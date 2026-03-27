"""Cross-sectional momentum strategy for IDX equities.

Implements Jegadeesh-Titman (1993) 12-1 month momentum adapted for the
Indonesia Stock Exchange:
  - IDX lot size constraints (100 shares/lot)
  - IDX transaction costs (BEI levy + broker commission + VAT)
  - IDX liquidity profile (avg daily value filter)
  - Monthly rebalancing aligned to IDX trading calendar
  - No short selling (OJK regulation)

Signal construction:
    momentum_score(i, t) = P(i, t-1) / P(i, t-13) - 1
    Where P is adjusted close, t is in months, and the most recent month
    (t to t-1) is skipped to avoid short-term reversal.

Usage::

    strategy = IDXMomentumCrossSectionStrategy()
    signals = strategy.generate_signals(
        prices, volumes, trading_values, instrument_metadata,
        rebalance_dates, portfolio_nav,
    )
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from shared.structured_json_logger import get_logger
from strategy_engine.base_strategy_interface import (
    BarData,
    BaseStrategyInterface,
    SignalDirection,
    StrategyParameters,
    StrategySignal,
    TickData,
)

if TYPE_CHECKING:
    from datetime import date, datetime

logger = get_logger(__name__)

# Default universe (LQ45 subset)
_DEFAULT_UNIVERSE: list[str] = [
    "BBCA",
    "BBRI",
    "BMRI",
    "BBNI",
    "TLKM",
    "ASII",
    "UNVR",
    "HMSP",
    "GGRM",
    "KLBF",
    "ICBP",
    "INDF",
    "SMGR",
    "PTBA",
    "ADRO",
    "ITMG",
    "UNTR",
    "PGAS",
    "JSMR",
    "MNCN",
    "CPIN",
    "INKP",
    "INTP",
    "SMRA",
    "BSDE",
    "WIKA",
    "WSKT",
    "ANTM",
    "TINS",
    "INCO",
    "EXCL",
    "ISAT",
    "TOWR",
    "TBIG",
    "MDKA",
    "EMTK",
    "ESSA",
    "ACES",
    "ERAA",
    "MAPI",
]

# Constants
_TRADING_DAYS_PER_MONTH = 21
_IDX_LOT_SIZE = 100
_MIN_LOTS_PER_POSITION = 1


def calculate_lot_size(
    target_weight: Decimal,
    portfolio_nav: Decimal,
    price: Decimal,
    lot_size: int = _IDX_LOT_SIZE,
) -> int:
    """Round DOWN to nearest lot to avoid cash shortfall.

    IDX does not allow fractional lots.

    Parameters
    ----------
    target_weight:
        Target portfolio weight as a fraction (e.g. ``Decimal("0.05")``).
    portfolio_nav:
        Total portfolio net asset value in IDR.
    price:
        Current share price in IDR.
    lot_size:
        Shares per lot (default 100).

    Returns
    -------
    int
        Number of lots (≥ 0).
    """
    if price <= 0:
        return 0
    target_value = target_weight * portfolio_nav
    target_shares = int(target_value / price)
    target_lots = target_shares // lot_size
    return max(0, target_lots)


class IDXMomentumCrossSectionStrategy(BaseStrategyInterface):
    """Cross-sectional momentum strategy for IDX equities.

    Based on Jegadeesh-Titman (1993) adapted for:
    - IDX lot size constraints (100 shares/lot)
    - IDX transaction costs (BEI levy + broker commission + VAT)
    - IDX liquidity profile (avg daily value filter)
    - Monthly rebalancing aligned to IDX trading calendar
    - No short selling (OJK regulation)

    Parameters
    ----------
    formation_months : int
        Lookback period for momentum calculation, default 12
    skip_months : int
        Months to skip before formation period end, default 1
    holding_months : int
        Rebalancing frequency in months, default 1
    top_pct : float
        Top fraction to include in long portfolio, default 0.20
    max_position_pct : float
        Maximum single position as fraction of NAV, default 0.10
    min_avg_daily_value_idr : Decimal
        Minimum average daily trading value for liquidity filter
    max_sector_concentration : float
        Maximum sector weight in portfolio, default 0.40
    """

    def __init__(
        self,
        universe: list[str] | None = None,
        formation_months: int = 12,
        skip_months: int = 1,
        holding_months: int = 1,
        top_pct: float = 0.20,
        max_position_pct: float = 0.10,
        min_avg_daily_value_idr: Decimal = Decimal("10_000_000_000"),
        max_sector_concentration: float = 0.40,
        strategy_id: str = "idx_momentum_12_1",
    ) -> None:
        self._universe = universe or list(_DEFAULT_UNIVERSE)
        self._formation_months = formation_months
        self._skip_months = skip_months
        self._holding_months = holding_months
        self._top_pct = top_pct
        self._max_position_pct = max_position_pct
        self._min_avg_daily_value_idr = min_avg_daily_value_idr
        self._max_sector_concentration = max_sector_concentration
        self._strategy_id = strategy_id
        self._bar_buffer: dict[str, list[BarData]] = {s: [] for s in self._universe}

        logger.info(
            "momentum_strategy_initialised",
            strategy_id=self._strategy_id,
            universe_size=len(self._universe),
            formation_months=self._formation_months,
            skip_months=self._skip_months,
            top_pct=self._top_pct,
        )

    # BaseStrategyInterface implementation

    def get_parameters(self) -> StrategyParameters:
        return StrategyParameters(
            name="IDX 12-1 Cross-Section Momentum",
            version="2.0.0",
            universe=list(self._universe),
            lookback_days=self._formation_months * _TRADING_DAYS_PER_MONTH,
            rebalance_frequency="monthly",
            custom={
                "formation_months": self._formation_months,
                "skip_months": self._skip_months,
                "holding_months": self._holding_months,
                "top_pct": self._top_pct,
                "max_position_pct": self._max_position_pct,
                "max_sector_concentration": self._max_sector_concentration,
            },
        )

    async def generate_signals(
        self,
        market_data: pd.DataFrame,
        as_of_date: datetime,
    ) -> list[StrategySignal]:
        """Generate momentum signals (BaseStrategyInterface compat).

        For the full production API with IDX-specific features, use
        :meth:`generate_signals_full` instead.
        """
        logger.info("momentum_signal_generation_start", as_of_date=as_of_date.isoformat())
        try:
            signals = self._compute_momentum_signals(market_data, as_of_date)
            logger.info(
                "momentum_signal_generation_complete",
                as_of_date=as_of_date.isoformat(),
                signal_count=len(signals),
            )
            return signals
        except (KeyError, ValueError) as exc:
            logger.error("momentum_signal_generation_failed", error=str(exc))
            return []

    async def on_bar(self, bar: BarData) -> list[StrategySignal]:
        if bar.symbol in self._bar_buffer:
            self._bar_buffer[bar.symbol].append(bar)
        return []

    async def on_tick(self, tick: TickData) -> list[StrategySignal]:
        return []

    # Full production API

    def generate_signals_full(
        self,
        prices: pd.DataFrame,
        volumes: pd.DataFrame,
        trading_values: pd.DataFrame,
        instrument_metadata: pd.DataFrame,
        rebalance_dates: list[date],
        portfolio_nav: Decimal,
    ) -> pd.DataFrame:
        """Generate signal DataFrame across multiple rebalance dates.

        Parameters
        ----------
        prices:
            Shape ``(dates, symbols)``, adjusted close prices.
            Index must be ``pd.DatetimeIndex`` (UTC).
        volumes:
            Shape ``(dates, symbols)``, volume in shares.
        trading_values:
            Shape ``(dates, symbols)``, daily trading value in IDR.
        instrument_metadata:
            Columns: ``symbol``, ``sector``, ``lot_size``, ``is_active``.
        rebalance_dates:
            List of rebalance dates.
        portfolio_nav:
            Total portfolio NAV in IDR.

        Returns
        -------
        pd.DataFrame
            Columns: symbol, date, signal_type, target_weight, target_lots,
            momentum_score, rank, universe_size, sector
        """
        all_signals: list[pd.DataFrame] = []

        for reb_date in rebalance_dates:
            filtered = self.filter_universe(
                prices,
                trading_values,
                instrument_metadata,
                as_of_date=reb_date,
                min_history_days=self._formation_months * _TRADING_DAYS_PER_MONTH,
                min_avg_daily_value_idr=self._min_avg_daily_value_idr,
            )
            if not filtered:
                continue

            scores = self.compute_momentum_scores(
                prices,
                as_of_date=reb_date,
                formation_months=self._formation_months,
                skip_months=self._skip_months,
            )
            # Keep only filtered symbols
            scores = scores.reindex(filtered).dropna()
            if scores.empty:
                continue

            prices_today = self._get_prices_as_of(prices, reb_date).iloc[-1]

            portfolio = self.construct_portfolio(
                momentum_scores=scores,
                filtered_universe=filtered,
                instrument_metadata=instrument_metadata,
                portfolio_nav=portfolio_nav,
                prices_today=prices_today,
                top_pct=self._top_pct,
                max_position_pct=self._max_position_pct,
                max_sector_concentration=self._max_sector_concentration,
            )
            if portfolio.empty:
                continue

            portfolio["date"] = reb_date
            portfolio["universe_size"] = len(filtered)
            portfolio["signal_type"] = "ENTRY_LONG"
            all_signals.append(portfolio)

        if not all_signals:
            return pd.DataFrame(
                columns=[
                    "symbol",
                    "date",
                    "signal_type",
                    "target_weight",
                    "target_lots",
                    "momentum_score",
                    "rank",
                    "universe_size",
                    "sector",
                ]
            )
        return pd.concat(all_signals, ignore_index=True)

    # Core computations

    def compute_momentum_scores(
        self,
        prices: pd.DataFrame,
        as_of_date: date,
        formation_months: int,
        skip_months: int,
    ) -> pd.Series:
        """Compute 12-1 momentum scores for all symbols as of a given date.

        Uses only data available STRICTLY BEFORE ``as_of_date``.
        No look-ahead bias — enforced via strict date filtering.

        Returns
        -------
        pd.Series
            Indexed by symbol, sorted descending by momentum score.
        """
        available = self._get_prices_as_of(prices, as_of_date)

        formation_days = formation_months * _TRADING_DAYS_PER_MONTH
        skip_days = skip_months * _TRADING_DAYS_PER_MONTH

        total_required = formation_days + skip_days
        if len(available) < total_required:
            return pd.Series(dtype=float)

        # P(t-1): most recent available price (end of skip period)
        price_end = available.iloc[-skip_days] if skip_days > 0 else available.iloc[-1]

        # P(t-13): price at start of formation period
        price_start = available.iloc[-(formation_days + skip_days)]

        # momentum_score = P(t-1) / P(t-13) - 1
        momentum: pd.Series = (price_end / price_start) - 1.0
        momentum = momentum.dropna()
        return momentum.sort_values(ascending=False)

    def filter_universe(
        self,
        prices: pd.DataFrame,
        trading_values: pd.DataFrame,
        instrument_metadata: pd.DataFrame,
        as_of_date: date,
        min_history_days: int = 252,
        min_avg_daily_value_idr: Decimal = Decimal("10_000_000_000"),
        min_price_idr: Decimal = Decimal("100"),
    ) -> list[str]:
        """Apply all IDX-specific universe filters.

        Filters (all applied using data strictly before ``as_of_date``):
          1. Liquidity: trailing 63-day avg daily value ≥ threshold
          2. Price: closing price ≥ min_price_idr
          3. Suspension: exclude stocks where ``is_active`` is False
          4. Data completeness: require ≥ min_history_days of price data
          5. Survivorship: exclude stocks not yet listed or already delisted
        """
        available_prices = self._get_prices_as_of(prices, as_of_date)
        tv_ts = pd.Timestamp(as_of_date)
        if trading_values.index.tz is not None and tv_ts.tz is None:
            tv_ts = tv_ts.tz_localize(trading_values.index.tz)
        available_values = trading_values[trading_values.index < tv_ts]

        # Build metadata lookup
        meta_lookup = instrument_metadata.set_index("symbol")

        passed: list[str] = []
        for symbol in available_prices.columns:
            # 4. Data completeness
            sym_prices = available_prices[symbol].dropna()
            if len(sym_prices) < min_history_days:
                continue

            # 3. Suspension filter + survivorship bias prevention
            if symbol in meta_lookup.index:
                row = meta_lookup.loc[symbol]
                if not row.get("is_active", True):
                    continue
                # Survivorship: skip if not yet listed or already delisted
                listing = row.get("listing_date")
                delisting = row.get("delisting_date")
                if listing is not None and as_of_date < listing:
                    continue
                if delisting is not None and as_of_date > delisting:
                    continue

            # 2. Price filter — last available close
            last_price = sym_prices.iloc[-1]
            if Decimal(str(last_price)) < min_price_idr:
                continue

            # 1. Liquidity filter — trailing 63 trading day avg daily value
            if symbol in available_values.columns:
                trailing_values = available_values[symbol].dropna().iloc[-63:]
                if len(trailing_values) > 0:
                    avg_daily_value = Decimal(str(trailing_values.mean()))
                    if avg_daily_value < min_avg_daily_value_idr:
                        continue
                else:
                    continue
            else:
                continue

            passed.append(symbol)

        return passed

    def construct_portfolio(
        self,
        momentum_scores: pd.Series,
        filtered_universe: list[str],
        instrument_metadata: pd.DataFrame,
        portfolio_nav: Decimal,
        prices_today: pd.Series,
        top_pct: float = 0.20,
        max_position_pct: float = 0.10,
        max_sector_concentration: float = 0.40,
    ) -> pd.DataFrame:
        """Construct target portfolio from ranked universe.

        Steps:
          1. Select top quintile by momentum score
          2. Assign equal weight (capped at max_position_pct)
          3. Enforce sector concentration cap
          4. Round to lot sizes

        Returns
        -------
        pd.DataFrame
            Columns: symbol, target_weight, target_lots, target_value_idr,
            momentum_score, rank, sector
        """
        scores = momentum_scores.reindex(filtered_universe).dropna()
        scores = scores.sort_values(ascending=False)

        n_select = max(1, int(np.ceil(len(scores) * top_pct)))
        top = scores.head(n_select)

        meta_lookup = instrument_metadata.set_index("symbol")

        # Initial equal weight
        raw_weight = Decimal("1") / Decimal(str(len(top)))
        capped_weight = min(raw_weight, Decimal(str(max_position_pct)))

        rows: list[dict[str, object]] = []
        for rank_idx, (symbol, score) in enumerate(top.items(), start=1):
            sector = ""
            lot_size = _IDX_LOT_SIZE
            if symbol in meta_lookup.index:
                sector = str(meta_lookup.loc[symbol, "sector"] or "")
                lot_size = int(meta_lookup.loc[symbol, "lot_size"])

            price = Decimal(str(prices_today.get(symbol, 0)))
            if price <= 0:
                continue

            lots = calculate_lot_size(capped_weight, portfolio_nav, price, lot_size)
            if lots < _MIN_LOTS_PER_POSITION:
                continue

            actual_shares = lots * lot_size
            actual_value = price * Decimal(str(actual_shares))
            actual_weight = actual_value / portfolio_nav if portfolio_nav > 0 else Decimal("0")

            rows.append(
                {
                    "symbol": symbol,
                    "target_weight": float(actual_weight),
                    "target_lots": lots,
                    "target_value_idr": float(actual_value),
                    "momentum_score": float(score),
                    "rank": rank_idx,
                    "sector": sector,
                }
            )

        if not rows:
            return pd.DataFrame(
                columns=[
                    "symbol",
                    "target_weight",
                    "target_lots",
                    "target_value_idr",
                    "momentum_score",
                    "rank",
                    "sector",
                ]
            )

        portfolio = pd.DataFrame(rows)

        # Enforce sector concentration cap
        return self._apply_sector_cap(portfolio, max_sector_concentration)

    def compute_rebalance_trades(
        self,
        target_portfolio: pd.DataFrame,
        current_positions: dict[str, int],
        prices_today: pd.Series,
    ) -> pd.DataFrame:
        """Compute trades needed to move from current to target portfolio.

        Rules:
        - Only trade if |lots_delta| >= 1
        - Sells sorted before buys (free capital first)
        - Buys sorted by momentum_score descending (highest conviction first)

        Returns
        -------
        pd.DataFrame
            Columns: symbol, action, lots_delta, estimated_value_idr
        """
        target_lots_map: dict[str, int] = {}
        score_map: dict[str, float] = {}
        if not target_portfolio.empty:
            target_lots_map = dict(zip(target_portfolio["symbol"], target_portfolio["target_lots"], strict=False))
            score_map = dict(zip(target_portfolio["symbol"], target_portfolio["momentum_score"], strict=False))

        all_symbols = set(current_positions.keys()) | set(target_lots_map.keys())

        trades: list[dict[str, object]] = []
        for symbol in all_symbols:
            current = current_positions.get(symbol, 0)
            target = target_lots_map.get(symbol, 0)
            delta = target - current

            if abs(delta) < 1:
                continue

            price = float(prices_today.get(symbol, 0))
            value = abs(delta) * _IDX_LOT_SIZE * price

            action = "BUY" if delta > 0 else "SELL"
            trades.append(
                {
                    "symbol": symbol,
                    "action": action,
                    "lots_delta": delta,
                    "estimated_value_idr": value,
                    "momentum_score": score_map.get(symbol, 0.0),
                }
            )

        if not trades:
            return pd.DataFrame(columns=["symbol", "action", "lots_delta", "estimated_value_idr"])

        df = pd.DataFrame(trades)

        # Sells first, then buys sorted by momentum_score descending
        sells = df[df["action"] == "SELL"].copy()
        buys = df[df["action"] == "BUY"].sort_values("momentum_score", ascending=False).copy()
        result = pd.concat([sells, buys], ignore_index=True)
        return result[["symbol", "action", "lots_delta", "estimated_value_idr"]]

    # Private helpers

    def _get_prices_as_of(
        self,
        prices: pd.DataFrame,
        as_of_date: date,
    ) -> pd.DataFrame:
        """Return prices STRICTLY BEFORE ``as_of_date``.

        Signal generated using close[t-1], executed at open[t].
        Using ``<`` prevents look-ahead bias — today's close is not known
        at market open when orders are placed.
        """
        ts = pd.Timestamp(as_of_date)
        if prices.index.tz is not None and ts.tz is None:
            ts = ts.tz_localize(prices.index.tz)
        return prices[prices.index < ts]

    def _compute_momentum_signals(
        self,
        market_data: pd.DataFrame,
        as_of_date: datetime,
    ) -> list[StrategySignal]:
        """Backward-compatible signal generation for BaseStrategyInterface."""
        if isinstance(market_data.index, pd.MultiIndex):
            close_prices = market_data["close"].unstack(level="symbol")
        else:
            close_prices = market_data.pivot(columns="symbol", values="close")

        # Strict < for look-ahead prevention
        close_prices = close_prices.loc[close_prices.index < as_of_date]
        close_prices = close_prices.sort_index()

        td_per_month = _TRADING_DAYS_PER_MONTH
        formation_days = self._formation_months * td_per_month
        skip_days = self._skip_months * td_per_month

        if len(close_prices) < formation_days + skip_days:
            logger.warning(
                "momentum_insufficient_data",
                required=formation_days + skip_days,
                available=len(close_prices),
            )
            return []

        # P(t-1): end of skip window
        price_end = close_prices.iloc[-skip_days] if skip_days > 0 else close_prices.iloc[-1]
        # P(t-13): start of formation window
        price_start = close_prices.iloc[-(formation_days + skip_days)]

        momentum_score: pd.Series = (price_end / price_start) - 1.0
        momentum_score = momentum_score.dropna()
        momentum_score = momentum_score.reindex(self._universe).dropna()

        if momentum_score.empty:
            return []

        n_select = max(1, int(np.ceil(len(momentum_score) * self._top_pct)))
        top_stocks = momentum_score.nlargest(n_select)
        weight = 1.0 / n_select

        signals: list[StrategySignal] = []
        for symbol in top_stocks.index:
            score = float(momentum_score[symbol])
            rank_pct = float(momentum_score.rank(ascending=True)[symbol] / len(momentum_score))
            signals.append(
                StrategySignal(
                    symbol=symbol,
                    direction=SignalDirection.LONG,
                    target_weight=weight,
                    confidence=round(rank_pct, 4),
                    strategy_id=self._strategy_id,
                    generated_at=as_of_date,
                    metadata={
                        "momentum_score": round(score, 6),
                    },
                )
            )
        return signals

    @staticmethod
    def _apply_sector_cap(
        portfolio: pd.DataFrame,
        max_sector_concentration: float,
    ) -> pd.DataFrame:
        """Redistribute weight from over-concentrated sectors.

        Iteratively trims positions in the heaviest sector until no sector
        exceeds the cap, redistributing weight to under-weight sectors.
        """
        if portfolio.empty or "sector" not in portfolio.columns:
            return portfolio

        df = portfolio.copy()
        for _ in range(10):  # max iterations to converge
            sector_weights = df.groupby("sector")["target_weight"].sum()
            over = sector_weights[sector_weights > max_sector_concentration]
            if over.empty:
                break
            for sector_name in over.index:
                mask = df["sector"] == sector_name
                sector_total = df.loc[mask, "target_weight"].sum()
                if sector_total > max_sector_concentration:
                    scale = max_sector_concentration / sector_total
                    df.loc[mask, "target_weight"] *= scale

        # Renormalize so total weight sums to original total
        total = df["target_weight"].sum()
        if total > 0:
            original_total = portfolio["target_weight"].sum()
            df["target_weight"] *= original_total / total

        return df
