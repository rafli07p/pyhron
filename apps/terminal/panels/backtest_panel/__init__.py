"""Backtest results panel for the Pyhron terminal.

Displays strategy backtest results including capital summary,
risk-adjusted metrics, trading statistics, and an ASCII equity curve.
Triggered by ``BT <strategy> <date_from> <date_to>`` commands.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


# ── Formatting Helpers ───────────────────────────────────────────────────────


def _fmt_idr(value: int | float) -> str:
    """Format as IDR with period thousands separator."""
    s = f"{abs(int(value)):,}".replace(",", ".")
    return f"-{s}" if value < 0 else s


def _fmt_pct(value: float) -> str:
    """Format percentage with comma decimal separator."""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%".replace(".", ",")


def _fmt_ratio(value: float | None) -> str:
    """Format a numeric ratio, returning a dash for None."""
    if value is None:
        return "---"
    return f"{value:.2f}"


def _fmt_pnl_color(value: float) -> str:
    """Return rich markup for P&L values (green positive, red negative)."""
    if value > 0:
        return f"[#00c853]+{_fmt_idr(value)}[/]"
    if value < 0:
        return f"[#ff1744]-{_fmt_idr(abs(value))}[/]"
    return _fmt_idr(0)


def _fmt_return_color(value: float) -> str:
    """Return rich markup for percentage returns."""
    if value > 0:
        return f"[#00c853]{_fmt_pct(value)}[/]"
    if value < 0:
        return f"[#ff1744]{_fmt_pct(value)}[/]"
    return _fmt_pct(0)


# ── ASCII Equity Curve ───────────────────────────────────────────────────────


def render_equity_curve(
    nav_series: list[float],
    width: int = 60,
    height: int = 12,
) -> str:
    """Render an ASCII equity curve using min-max normalization.

    Args:
        nav_series: Time series of NAV values.
        width: Character width of the chart area.
        height: Character height of the chart area.

    Returns:
        Multi-line string containing the ASCII chart with axis labels.

    Handles edge cases:
        - Empty series: returns a placeholder message.
        - Single point: renders a single dot at mid-height.
        - Flat series (all same value): renders a horizontal line.
    """
    if not nav_series:
        return "  (no equity data available)"

    if len(nav_series) == 1:
        mid = height // 2
        lines: list[str] = []
        label = _fmt_idr(nav_series[0])
        for row in range(height):
            if row == mid:
                lines.append(f"  {label:>14} \u2502 \u2022")
            else:
                lines.append(f"  {'':>14} \u2502")
        lines.append(f"  {'':>14} \u2514" + "\u2500" * (width + 1))
        return "\n".join(lines)

    # Resample to fit width if series is longer
    if len(nav_series) > width:
        step = len(nav_series) / width
        sampled = [nav_series[int(i * step)] for i in range(width)]
    else:
        sampled = list(nav_series)

    min_val = min(sampled)
    max_val = max(sampled)
    val_range = max_val - min_val

    # Build character grid
    grid: list[list[str]] = [[" "] * len(sampled) for _ in range(height)]

    for col, val in enumerate(sampled):
        if val_range > 0:
            normalized = (val - min_val) / val_range
        else:
            normalized = 0.5  # flat series
        row = height - 1 - int(round(normalized * (height - 1)))
        row = max(0, min(height - 1, row))
        grid[row][col] = "\u2588"

    # Render with Y-axis labels
    lines = []
    for row_idx in range(height):
        if row_idx == 0:
            label = _fmt_idr(max_val)
        elif row_idx == height - 1:
            label = _fmt_idr(min_val)
        elif row_idx == height // 2:
            mid_val = (max_val + min_val) / 2
            label = _fmt_idr(mid_val)
        else:
            label = ""
        row_str = "".join(grid[row_idx])
        lines.append(f"  {label:>14} \u2502 {row_str}")

    # X-axis
    lines.append(f"  {'':>14} \u2514" + "\u2500" * (len(sampled) + 1))

    return "\n".join(lines)


# ── Panel Widget ─────────────────────────────────────────────────────────────


class BacktestPanel(Static):
    """Backtest results display panel.

    Shows capital summary, risk metrics, trading statistics, and
    an ASCII equity curve.  Populated by running
    ``BT <strategy> <date_from> <date_to>`` in the terminal.
    """

    result_data: reactive[dict[str, Any]] = reactive(dict, recompose=True)
    nav_series: reactive[list[float]] = reactive(list, recompose=True)

    DEFAULT_CSS = """
    BacktestPanel {
        height: auto;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(self._render_panel(), id="backtest-panel-content")

    def watch_result_data(self) -> None:
        """Refresh when backtest results change."""
        self._try_refresh()

    def watch_nav_series(self) -> None:
        self._try_refresh()

    def _try_refresh(self) -> None:
        """Attempt to update the inner content widget."""
        with contextlib.suppress(Exception):
            content = self.query_one("#backtest-panel-content", Static)
            content.update(self._render_panel())

    # ── External update hook ─────────────────────────────────────────

    def on_backtest_result(self, result: dict[str, Any]) -> None:
        """Ingest a completed backtest result payload.

        Expected keys in *result*:
            strategy_id, date_from, date_to, initial_capital_idr,
            final_nav_idr, total_return_pct, cagr_pct, sharpe_ratio,
            sortino_ratio, calmar_ratio, max_drawdown_pct,
            max_drawdown_duration_days, total_trades, win_rate_pct,
            avg_win_idr, avg_loss_idr, profit_factor,
            total_commission_idr, nav_series (list[float]).
        """
        self.result_data = result
        self.nav_series = result.get("nav_series", [])

    # ── Rendering ────────────────────────────────────────────────────

    def _render_panel(self) -> str:
        """Render the complete backtest results panel."""
        data = self.result_data
        if not data:
            return "No backtest results. Run: BT <strategy> <date_from> <date_to>"

        parts: list[str] = []

        # Header
        strategy = data.get("strategy_id", "unknown")
        date_from = data.get("date_from", "?")
        date_to = data.get("date_to", "?")
        parts.append(f"BACKTEST RESULTS: {strategy}")
        parts.append(f"Period: {date_from} to {date_to}")
        parts.append("\u2500" * 60)

        # Capital summary
        parts.append(self._render_capital_summary(data))
        parts.append("\u2500" * 60)

        # Risk metrics
        parts.append(self._render_risk_metrics(data))
        parts.append("\u2500" * 60)

        # Trading statistics
        parts.append(self._render_trading_stats(data))
        parts.append("\u2500" * 60)

        # Equity curve
        parts.append("EQUITY CURVE")
        parts.append(render_equity_curve(list(self.nav_series)))

        return "\n".join(parts)

    def _render_capital_summary(self, data: dict[str, Any]) -> str:
        """Render the capital and return summary section."""
        initial = data.get("initial_capital_idr", 0)
        final_nav = data.get("final_nav_idr", 0)
        total_return = data.get("total_return_pct", 0)
        cagr = data.get("cagr_pct", 0)

        pnl = final_nav - initial

        return "\n".join(
            [
                "CAPITAL SUMMARY",
                f"  Initial Capital  IDR {_fmt_idr(initial)}",
                f"  Final NAV        IDR {_fmt_idr(final_nav)}",
                f"  P&L              {_fmt_pnl_color(pnl)}",
                f"  Total Return     {_fmt_return_color(total_return)}",
                f"  CAGR             {_fmt_return_color(cagr)}",
            ]
        )

    def _render_risk_metrics(self, data: dict[str, Any]) -> str:
        """Render risk-adjusted performance metrics."""
        sharpe = data.get("sharpe_ratio")
        sortino = data.get("sortino_ratio")
        calmar = data.get("calmar_ratio")
        max_dd = data.get("max_drawdown_pct", 0)
        max_dd_days = data.get("max_drawdown_duration_days", 0)

        # Color-code Sharpe
        sharpe_str = _fmt_ratio(sharpe)
        if sharpe is not None:
            if sharpe >= 1.5:
                sharpe_str = f"[#00c853]{sharpe_str}[/]"
            elif sharpe >= 1.0:
                sharpe_str = f"[#f59e0b]{sharpe_str}[/]"
            else:
                sharpe_str = f"[#ff1744]{sharpe_str}[/]"

        # Color-code max drawdown
        dd_str = _fmt_pct(-max_dd)
        if max_dd >= 20:
            dd_str = f"[#ff1744]{dd_str}[/]"
        elif max_dd >= 10:
            dd_str = f"[#f59e0b]{dd_str}[/]"
        else:
            dd_str = f"[#00c853]{dd_str}[/]"

        return "\n".join(
            [
                "RISK METRICS",
                f"  Sharpe Ratio     {sharpe_str}",
                f"  Sortino Ratio    {_fmt_ratio(sortino)}",
                f"  Calmar Ratio     {_fmt_ratio(calmar)}",
                f"  Max Drawdown     {dd_str}",
                f"  Max DD Duration  {max_dd_days} days",
            ]
        )

    def _render_trading_stats(self, data: dict[str, Any]) -> str:
        """Render trading activity statistics."""
        total_trades = data.get("total_trades", 0)
        win_rate = data.get("win_rate_pct", 0)
        avg_win = data.get("avg_win_idr", 0)
        avg_loss = data.get("avg_loss_idr", 0)
        profit_factor = data.get("profit_factor")
        total_commission = data.get("total_commission_idr", 0)

        # Win rate color
        wr_str = f"{win_rate:.1f}%"
        if win_rate >= 55:
            wr_str = f"[#00c853]{wr_str}[/]"
        elif win_rate >= 45:
            wr_str = f"[#f59e0b]{wr_str}[/]"
        else:
            wr_str = f"[#ff1744]{wr_str}[/]"

        # Profit factor color
        pf_str = _fmt_ratio(profit_factor)
        if profit_factor is not None:
            if profit_factor >= 1.5:
                pf_str = f"[#00c853]{pf_str}[/]"
            elif profit_factor >= 1.0:
                pf_str = f"[#f59e0b]{pf_str}[/]"
            else:
                pf_str = f"[#ff1744]{pf_str}[/]"

        # Avg win/loss ratio
        if avg_loss != 0:
            wl_ratio = abs(avg_win / avg_loss)
            wl_str = f"{wl_ratio:.2f}x"
        else:
            wl_str = "---"

        return "\n".join(
            [
                "TRADING STATISTICS",
                f"  Total Trades     {total_trades}",
                f"  Win Rate         {wr_str}",
                f"  Avg Win          IDR {_fmt_idr(avg_win)}",
                f"  Avg Loss         IDR {_fmt_idr(avg_loss)}",
                f"  Win/Loss Ratio   {wl_str}",
                f"  Profit Factor    {pf_str}",
                f"  Total Commission IDR {_fmt_idr(total_commission)}",
            ]
        )
