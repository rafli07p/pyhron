"""Paper trading dashboard panel for the Pyhron terminal.

Displays session status, NAV summary, positions, today's fills,
and performance metrics in a Bloomberg-style layout.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


def _fmt_idr(value: int | float) -> str:
    """Format as IDR with period thousands separator."""
    s = f"{abs(int(value)):,}".replace(",", ".")
    return f"-{s}" if value < 0 else s


def _fmt_pct(value: float) -> str:
    """Format percentage with comma decimal."""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%".replace(".", ",")


def _fmt_pnl_color(value: float) -> str:
    """Return ANSI-style rich markup for P&L values."""
    if value > 0:
        return f"[#00c853]+{_fmt_idr(value)}[/]"
    if value < 0:
        return f"[#ff1744]-{_fmt_idr(abs(value))}[/]"
    return _fmt_idr(0)


_STATUS_COLORS: dict[str, str] = {
    "RUNNING": "#00c853",
    "PAUSED": "#f59e0b",
    "STOPPED": "#9e9e9e",
    "INITIALIZING": "#2196f3",
    "COMPLETED": "#9e9e9e",
}


class PaperTradingPanel(Static):
    """Bloomberg-style paper trading dashboard panel.

    Updates in real-time via WebSocket PAPER_NAV_UPDATE and
    POSITION_UPDATE messages.
    """

    session_data: reactive[dict[str, Any]] = reactive(dict, recompose=True)
    positions_data: reactive[list[dict[str, Any]]] = reactive(list, recompose=True)
    fills_data: reactive[list[dict[str, Any]]] = reactive(list, recompose=True)
    metrics_data: reactive[dict[str, Any]] = reactive(dict, recompose=True)

    def compose(self) -> ComposeResult:
        yield Static(self._render_panel(), id="paper-trading-content")

    def watch_session_data(self) -> None:
        """Refresh when session data changes."""
        with contextlib.suppress(Exception):
            content = self.query_one("#paper-trading-content", Static)
            content.update(self._render_panel())

    def watch_positions_data(self) -> None:
        with contextlib.suppress(Exception):
            content = self.query_one("#paper-trading-content", Static)
            content.update(self._render_panel())

    def watch_fills_data(self) -> None:
        with contextlib.suppress(Exception):
            content = self.query_one("#paper-trading-content", Static)
            content.update(self._render_panel())

    def on_nav_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Update NAV and drawdown display."""
        self.session_data = {
            **dict(self.session_data),
            "nav_idr": float(snapshot.get("nav_idr", 0)),
            "cash_idr": float(snapshot.get("cash_idr", 0)),
            "drawdown_pct": float(snapshot.get("drawdown_pct", 0)),
            "daily_pnl_idr": float(snapshot.get("daily_pnl_idr", 0)),
        }

    def on_position_update(self, update: dict[str, Any]) -> None:
        """Refresh positions table row for symbol."""
        symbol = update.get("symbol", "")
        new_positions = [p for p in self.positions_data if p.get("symbol") != symbol]
        new_positions.append(update)
        self.positions_data = new_positions

    def on_order_update(self, update: dict[str, Any]) -> None:
        """Add filled order to today's fills table."""
        if update.get("status") == "FILLED":
            self.fills_data = [*list(self.fills_data), update]

    def _render_panel(self) -> str:
        """Render the complete panel as text."""
        parts: list[str] = []

        # Session header
        session = self.session_data
        name = session.get("name", "No active session")
        status = session.get("status", "—")
        color = _STATUS_COLORS.get(status, "#9e9e9e")
        parts.append(f"SESSION: {name}  [{color}][{status}][/]")
        parts.append("─" * 50)

        # NAV summary
        nav = session.get("nav_idr", 0)
        cash = session.get("cash_idr", 0)
        peak = session.get("peak_nav_idr", 0)
        dd = session.get("drawdown_pct", 0)
        initial = session.get("initial_capital_idr", 0)
        total_return = ((nav - initial) / initial * 100) if initial > 0 else 0

        parts.append(f"NAV  IDR {_fmt_idr(nav)}  {_fmt_pct(total_return)} total")
        cash_pct = (cash / nav * 100) if nav > 0 else 0
        parts.append(f"Cash IDR {_fmt_idr(cash)}  {cash_pct:.1f}% of NAV")
        parts.append(f"Drawdown {_fmt_pct(-dd)}  Peak IDR {_fmt_idr(peak)}")
        parts.append("─" * 50)

        # Positions
        positions = self.positions_data
        parts.append(f"POSITIONS ({len(positions)} open)")
        parts.append(f"{'Symbol':<8} {'Lots':>6} {'Cost':>8} {'Last':>8} {'PnL%':>7} {'PnL IDR':>12}")
        for pos in positions:
            symbol = pos.get("symbol", "")
            lots = pos.get("quantity_lots", 0)
            cost = pos.get("avg_cost_idr", 0)
            last = pos.get("last_price", 0)
            pnl_pct = ((last - cost) / cost * 100) if cost > 0 else 0
            pnl_idr = pos.get("unrealized_pnl_idr", 0)
            parts.append(
                f"{symbol:<8} {lots:>6} {_fmt_idr(cost):>8} {_fmt_idr(last):>8} "
                f"{_fmt_pct(pnl_pct):>7} {_fmt_pnl_color(pnl_idr):>12}"
            )
        parts.append("─" * 50)

        # Today's fills
        fills = self.fills_data
        parts.append(f"TODAY'S FILLS ({len(fills)})")
        for fill in fills[-10:]:
            fill_time = fill.get("filled_at", "")[:5] if fill.get("filled_at") else ""
            side = fill.get("side", "").upper()
            symbol = fill.get("symbol", "")
            lots = fill.get("quantity_lots", 0)
            price = fill.get("avg_fill_price", 0)
            comm = fill.get("commission_idr", 0)
            parts.append(f"  {fill_time} {side:>4} {symbol:<6} {lots}L @ {_fmt_idr(price)}  " f"comm {_fmt_idr(comm)}")
        parts.append("─" * 50)

        # Metrics
        metrics = self.metrics_data
        sharpe = metrics.get("sharpe_ratio")
        sortino = metrics.get("sortino_ratio")
        win_rate = metrics.get("win_rate_pct", 0)
        parts.append("METRICS")
        sharpe_str = f"{sharpe:.2f}" if sharpe is not None else "—"
        sortino_str = f"{sortino:.2f}" if sortino is not None else "—"
        parts.append(f"Sharpe {sharpe_str}  Sortino {sortino_str}  Win Rate {win_rate:.1f}%")

        return "\n".join(parts)
