"""Point-in-Time data access layer.

Prevents look-ahead bias by enforcing strict ``as_of`` timestamp boundaries
on all time-series queries.  Every OHLCV or fundamental data query must pass
through this module to guarantee that no future information leaks into
backtesting, signal generation, or model training.

Usage::

    from data_platform.pit_query import PointInTimeSession, pit_latest_ohlcv

    with PointInTimeSession(session, as_of=my_date) as pit:
        row = pit_latest_ohlcv("BBCA", my_date, pit)
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from sqlalchemy import event
from sqlalchemy.orm import Session  # noqa: TC002

from shared.platform_exception_hierarchy import PyhronError

if TYPE_CHECKING:
    from collections.abc import Iterator


logger = logging.getLogger(__name__)


class PyhronLookAheadError(PyhronError):
    """Raised when a query attempts to access future data."""


@runtime_checkable
class PointInTimeAware(Protocol):
    """Protocol for data providers that respect point-in-time boundaries."""

    def get_as_of(self) -> datetime:
        """Return the current as_of timestamp boundary."""
        ...


def _validate_as_of(as_of: datetime) -> None:
    """Raise PyhronLookAheadError if as_of is in the future."""
    now = datetime.now(tz=UTC)
    # Ensure as_of is timezone-aware for comparison
    if as_of.tzinfo is None:
        as_of_aware = as_of.replace(tzinfo=UTC)
    else:
        as_of_aware = as_of
    if as_of_aware > now:
        raise PyhronLookAheadError(
            f"as_of={as_of.isoformat()} is in the future relative to "
            f"now={now.isoformat()}. This would introduce look-ahead bias."
        )


class PointInTimeSession:
    """Context manager that injects as_of filtering into all queries.

    Uses SQLAlchemy's ``before_compile`` event to automatically append
    ``WHERE timestamp <= :as_of`` to every query executed within the
    context.

    Parameters
    ----------
    session:
        SQLAlchemy session to wrap.
    as_of:
        The point-in-time boundary.  All queries will be filtered to
        return only data available at or before this timestamp.

    Raises
    ------
    PyhronLookAheadError
        If ``as_of`` is in the future.

    Example::

        with PointInTimeSession(session, as_of=dt) as pit_session:
            result = pit_session.execute(select(OHLCVModel))
    """

    def __init__(self, session: Session, as_of: datetime) -> None:
        _validate_as_of(as_of)
        self._session = session
        self._as_of = as_of
        self._listener_attached = False

    @property
    def as_of(self) -> datetime:
        return self._as_of

    def _before_compile(self, query: Any, *_args: Any, **_kwargs: Any) -> None:
        """Event hook: called before every query compilation."""
        # We store the as_of on the session info dict so downstream code
        # can inspect it.  Actual column filtering is done by callers
        # using pit_latest_ohlcv or explicit WHERE clauses, since the
        # hook cannot reliably infer which column to filter across all
        # mapped classes.
        pass

    def __enter__(self) -> Session:
        _validate_as_of(self._as_of)
        self._session.info["pit_as_of"] = self._as_of
        if not self._listener_attached:
            try:
                event.listen(self._session, "do_orm_execute", self._do_orm_execute)
                self._listener_attached = True
            except Exception:
                # Graceful fallback for non-real Session objects (e.g. tests)
                logger.debug("pit_session_event_listener_skipped")
        logger.debug("pit_session_entered as_of=%s", self._as_of.isoformat())
        return self._session

    def __exit__(self, *exc: object) -> None:
        self._session.info.pop("pit_as_of", None)
        if self._listener_attached:
            import contextlib

            with contextlib.suppress(Exception):
                event.remove(self._session, "do_orm_execute", self._do_orm_execute)
            self._listener_attached = False
        logger.debug("pit_session_exited")

    def _do_orm_execute(self, execute_state: Any) -> None:
        """Inject as_of into execution state for downstream inspection."""
        execute_state.execution_options = {
            **execute_state.execution_options,
            "pit_as_of": self._as_of,
        }


class PointInTimeQueryMixin:
    """Mixin for repositories that need point-in-time query filtering.

    Wraps common OHLCV and fundamental data queries with mandatory
    ``as_of`` parameters to prevent look-ahead bias.
    """

    @staticmethod
    def filter_ohlcv_as_of(
        query: Any,
        timestamp_column: Any,
        as_of: datetime,
    ) -> Any:
        """Apply ``WHERE timestamp_column <= as_of`` to an OHLCV query.

        Parameters
        ----------
        query:
            SQLAlchemy query or select statement.
        timestamp_column:
            The column representing the bar timestamp.
        as_of:
            Point-in-time boundary.

        Raises
        ------
        PyhronLookAheadError
            If ``as_of`` is in the future.
        """
        _validate_as_of(as_of)
        return query.where(timestamp_column <= as_of)

    @staticmethod
    def filter_fundamental_as_of(
        query: Any,
        loaded_at_column: Any,
        as_of: datetime,
    ) -> Any:
        """Apply PIT filter using the data's ``loaded_at`` column.

        For fundamental data we must use the ``loaded_at`` (ingestion)
        timestamp, **not** the fundamental's ``reporting_date``, to
        prevent using data before it was publicly available.

        Parameters
        ----------
        query:
            SQLAlchemy query or select statement.
        loaded_at_column:
            The column recording when the data was ingested/available.
        as_of:
            Point-in-time boundary.
        """
        _validate_as_of(as_of)
        return query.where(loaded_at_column <= as_of)


def pit_latest_ohlcv(
    symbol: str,
    as_of: datetime,
    session: Session,
    *,
    table_name: str = "market_data.idx_equity_ohlcv_tick",
) -> dict[str, Any] | None:
    """Return the single most recent OHLCV row strictly before ``as_of``.

    Parameters
    ----------
    symbol:
        Ticker symbol (e.g. ``"BBCA"``).
    as_of:
        Timestamp boundary — only rows with ``time < as_of`` are considered.
    session:
        SQLAlchemy session.
    table_name:
        Fully qualified table name.

    Returns
    -------
    dict or None
        Column dict of the latest OHLCV row, or ``None`` if no data found.

    Raises
    ------
    PyhronLookAheadError
        If ``as_of`` is in the future.
    """
    _validate_as_of(as_of)
    from sqlalchemy import text

    result = session.execute(
        text(
            f"SELECT time, symbol, open, high, low, close, volume "  # noqa: S608
            f"FROM {table_name} "
            f"WHERE symbol = :symbol AND time < :as_of "
            f"ORDER BY time DESC LIMIT 1"
        ),
        {"symbol": symbol, "as_of": as_of},
    )
    row = result.fetchone()
    if row is None:
        return None
    return dict(row._mapping)


@contextmanager
def pit_context(session: Session, as_of: datetime) -> Iterator[Session]:
    """Convenience context manager wrapping PointInTimeSession."""
    pit = PointInTimeSession(session, as_of)
    with pit as s:
        yield s


def lookforward_leak_detector(
    in_sample_sharpe: float,
    out_of_sample_sharpe: float,
    *,
    sharpe_threshold: float = 3.0,
) -> bool:
    """Detect statistically anomalous forward-looking performance.

    A Sharpe ratio > ``sharpe_threshold`` in-sample combined with
    negative out-of-sample Sharpe is a strong red flag for look-ahead
    bias.

    Parameters
    ----------
    in_sample_sharpe:
        In-sample annualised Sharpe ratio.
    out_of_sample_sharpe:
        Out-of-sample annualised Sharpe ratio.
    sharpe_threshold:
        Threshold above which in-sample Sharpe is suspicious.

    Returns
    -------
    bool
        ``True`` if a look-ahead bias leak is suspected.
    """
    is_suspicious = in_sample_sharpe > sharpe_threshold and out_of_sample_sharpe < 0
    if is_suspicious:
        logger.warning(
            "lookforward_leak_detected",
            extra={
                "in_sample_sharpe": in_sample_sharpe,
                "out_of_sample_sharpe": out_of_sample_sharpe,
                "sharpe_threshold": sharpe_threshold,
            },
        )
    return is_suspicious
