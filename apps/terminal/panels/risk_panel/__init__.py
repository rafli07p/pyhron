"""Real-time portfolio risk dashboard panel for the Pyhron terminal.

Displays kill switch status, VaR metrics, exposure breakdown,
concentration analysis, daily loss and drawdown monitors with
color-coded progress bars in a Bloomberg-style layout.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


# Formatting Helpers
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


# Color Thresholds
_KILL_SWITCH_COLORS: dict[str, str] = {
    "ARMED": "#00c853",
    "TRIGGERED": "#ff1744",
    "DISARMED": "#9e9e9e",
}

_THRESHOLD_WARNING = 70.0
_THRESHOLD_DANGER = 90.0


def _threshold_color(pct: float) -> str:
    """Return rich markup color based on percentage thresholds.

    Green for normal (<70%), amber for warning (>=70%), red for danger (>=90%).
    """
    if pct >= _THRESHOLD_DANGER:
        return "#ff1744"
    if pct >= _THRESHOLD_WARNING:
        return "#f59e0b"
    return "#00c853"


def _render_progress_bar(pct: float, width: int = 20) -> str:
    """Render an ASCII progress bar with color coding.

    Args:
        pct: Percentage value (0-100+).
        width: Character width of the bar.

    Returns:
        Rich-markup string with colored progress bar.
    """
    clamped = max(0.0, min(100.0, pct))
    filled = int(round(clamped / 100 * width))
    empty = width - filled
    color = _threshold_color(pct)
    bar = "\u2588" * filled + "\u2591" * empty
    return f"[{color}]{bar}[/] {pct:.1f}%"


# Supported Commands
RISK_PANEL_COMMANDS: dict[str, str] = {
    "KILL ARM": "Arm the kill switch",
    "KILL TRIGGER": "Trigger the kill switch (emergency halt)",
    "KILL RESET": "Reset the kill switch after trigger",
    "PROMOTE": "Evaluate and promote a paper session to live",
    "ALLOC": "Show capital allocation across strategies",
    "VAR": "Show detailed VaR breakdown",
}


# Panel Widget
class RiskPanel(Static):
    """Bloomberg-style real-time portfolio risk dashboard.

    Updates via WebSocket RISK_SNAPSHOT messages.  Displays kill switch
    status, VaR metrics, exposure, concentration, and loss/drawdown
    monitors with color-coded progress bars.
    """

    kill_switch_data: reactive[dict[str, Any]] = reactive(dict, recompose=True)
    var_data: reactive[dict[str, Any]] = reactive(dict, recompose=True)
    exposure_data: reactive[dict[str, Any]] = reactive(dict, recompose=True)
    concentration_data: reactive[dict[str, Any]] = reactive(dict, recompose=True)
    loss_data: reactive[dict[str, Any]] = reactive(dict, recompose=True)
    drawdown_data: reactive[dict[str, Any]] = reactive(dict, recompose=True)
    allocation_data: reactive[list[dict[str, Any]]] = reactive(list, recompose=True)

    def compose(self) -> ComposeResult:
        yield Static(self._render_panel(), id="risk-panel-content")

    def watch_kill_switch_data(self) -> None:
        """Refresh panel when kill switch data changes."""
        self._try_refresh()

    def watch_var_data(self) -> None:
        self._try_refresh()

    def watch_exposure_data(self) -> None:
        self._try_refresh()

    def watch_concentration_data(self) -> None:
        self._try_refresh()

    def watch_loss_data(self) -> None:
        self._try_refresh()

    def watch_drawdown_data(self) -> None:
        self._try_refresh()

    def watch_allocation_data(self) -> None:
        self._try_refresh()

    def _try_refresh(self) -> None:
        """Attempt to update the inner content widget."""
        with contextlib.suppress(Exception):
            content = self.query_one("#risk-panel-content", Static)
            content.update(self._render_panel())

    # External update hooks

    def on_risk_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Ingest a full risk snapshot from the WebSocket feed."""
        self.kill_switch_data = {
            "state": snapshot.get("kill_switch_state", "ARMED"),
            "triggered_at": snapshot.get("triggered_at"),
            "triggered_by": snapshot.get("triggered_by"),
            "reason": snapshot.get("kill_switch_reason"),
        }
        self.var_data = {
            "var_1d_95_idr": snapshot.get("var_1d_95_idr", 0),
            "var_5d_95_idr": snapshot.get("var_5d_95_idr", 0),
            "var_1d_99_idr": snapshot.get("var_1d_99_idr", 0),
            "component_var": snapshot.get("component_var", {}),
        }
        exposure = snapshot.get("exposure", {})
        self.exposure_data = {
            "gross_idr": exposure.get("gross_exposure_idr", 0),
            "net_idr": exposure.get("net_exposure_idr", 0),
            "long_idr": exposure.get("long_exposure_idr", 0),
            "short_idr": exposure.get("short_exposure_idr", 0),
            "beta_vs_ihsg": exposure.get("beta_vs_ihsg", 0),
        }
        concentration = snapshot.get("concentration", {})
        self.concentration_data = {
            "sector_hhi": concentration.get("sector_hhi", 0),
            "top5_weight_pct": concentration.get("top5_weight_pct", 0),
            "largest_position_pct": concentration.get("largest_position_pct", 0),
            "largest_position_symbol": concentration.get("largest_position_symbol", ""),
            "num_positions": concentration.get("num_positions", 0),
        }
        nav = snapshot.get("nav_idr", 0)
        daily_loss_limit = snapshot.get("daily_loss_limit_idr", 0)
        daily_loss = snapshot.get("daily_loss_idr", 0)
        dd_limit = snapshot.get("drawdown_limit_pct", 0)
        dd_current = snapshot.get("drawdown_pct", 0)
        self.loss_data = {
            "daily_loss_idr": daily_loss,
            "daily_loss_limit_idr": daily_loss_limit,
            "daily_loss_pct": (daily_loss / nav * 100) if nav > 0 else 0,
            "utilization_pct": (daily_loss / daily_loss_limit * 100) if daily_loss_limit > 0 else 0,
        }
        self.drawdown_data = {
            "drawdown_pct": dd_current,
            "drawdown_limit_pct": dd_limit,
            "utilization_pct": (dd_current / dd_limit * 100) if dd_limit > 0 else 0,
        }

    def on_kill_switch_update(self, update: dict[str, Any]) -> None:
        """Handle a kill switch state change event."""
        self.kill_switch_data = {
            "state": update.get("state", "ARMED"),
            "triggered_at": update.get("triggered_at"),
            "triggered_by": update.get("triggered_by"),
            "reason": update.get("reason"),
        }

    def on_allocation_update(self, allocations: list[dict[str, Any]]) -> None:
        """Handle updated capital allocation data."""
        self.allocation_data = allocations

    # Command handling

    def handle_command(self, command: str) -> str | None:
        """Process a risk panel command and return a status message.

        Args:
            command: Uppercased command string (e.g. ``KILL ARM``).

        Returns:
            Human-readable status message, or ``None`` if unrecognised.
        """
        parts = command.strip().upper().split()
        if not parts:
            return None

        if len(parts) >= 2 and parts[0] == "KILL":
            sub = parts[1]
            if sub == "ARM":
                self.kill_switch_data = {**dict(self.kill_switch_data), "state": "ARMED"}
                return "Kill switch ARMED"
            if sub == "TRIGGER":
                self.kill_switch_data = {**dict(self.kill_switch_data), "state": "TRIGGERED"}
                return "Kill switch TRIGGERED -- all trading halted"
            if sub == "RESET":
                self.kill_switch_data = {**dict(self.kill_switch_data), "state": "ARMED"}
                return "Kill switch RESET and re-armed"

        if parts[0] == "PROMOTE":
            return "Promotion evaluation requested (see API for results)"

        if parts[0] == "ALLOC":
            return "Capital allocation refresh requested"

        if parts[0] == "VAR":
            return "VaR detail view requested"

        return None

    # Rendering

    def _render_panel(self) -> str:
        """Render the complete risk dashboard as a rich-markup string."""
        parts: list[str] = []

        # Kill switch status
        parts.append(self._render_kill_switch())
        parts.append("\u2500" * 60)

        # VaR metrics
        parts.append(self._render_var())
        parts.append("\u2500" * 60)

        # Exposure
        parts.append(self._render_exposure())
        parts.append("\u2500" * 60)

        # Concentration
        parts.append(self._render_concentration())
        parts.append("\u2500" * 60)

        # Daily loss monitor
        parts.append(self._render_daily_loss())
        parts.append("\u2500" * 60)

        # Drawdown monitor
        parts.append(self._render_drawdown())

        # Allocations (if present)
        alloc = self.allocation_data
        if alloc:
            parts.append("\u2500" * 60)
            parts.append(self._render_allocations())

        return "\n".join(parts)

    def _render_kill_switch(self) -> str:
        """Render the kill switch status section."""
        ks = self.kill_switch_data
        state = ks.get("state", "ARMED")
        color = _KILL_SWITCH_COLORS.get(state, "#9e9e9e")
        header = f"KILL SWITCH  [{color}][{state}][/]"

        lines = [header]
        triggered_at = ks.get("triggered_at")
        if triggered_at and state == "TRIGGERED":
            triggered_by = ks.get("triggered_by", "unknown")
            reason = ks.get("reason", "")
            lines.append(f"  Triggered by: {triggered_by}  at {triggered_at}")
            if reason:
                lines.append(f"  Reason: {reason}")
        return "\n".join(lines)

    def _render_var(self) -> str:
        """Render Value-at-Risk metrics section."""
        var = self.var_data
        var_1d_95 = var.get("var_1d_95_idr", 0)
        var_5d_95 = var.get("var_5d_95_idr", 0)
        var_1d_99 = var.get("var_1d_99_idr", 0)

        lines = [
            "VALUE AT RISK (95% confidence)",
            f"  1-day VaR  IDR {_fmt_idr(var_1d_95)}",
            f"  5-day VaR  IDR {_fmt_idr(var_5d_95)}",
            f"  1-day VaR (99%)  IDR {_fmt_idr(var_1d_99)}",
        ]

        component_var: dict[str, float] = var.get("component_var", {})
        if component_var:
            lines.append("  Component VaR:")
            for symbol, cvar in sorted(component_var.items(), key=lambda x: -abs(x[1])):
                lines.append(f"    {symbol:<8} IDR {_fmt_idr(cvar)}")

        return "\n".join(lines)

    def _render_exposure(self) -> str:
        """Render exposure breakdown section."""
        exp = self.exposure_data
        gross = exp.get("gross_idr", 0)
        net = exp.get("net_idr", 0)
        long_exp = exp.get("long_idr", 0)
        short_exp = exp.get("short_idr", 0)
        beta = exp.get("beta_vs_ihsg", 0)

        return "\n".join(
            [
                "EXPOSURE",
                f"  Gross    IDR {_fmt_idr(gross)}",
                f"  Net      IDR {_fmt_idr(net)}",
                f"  Long     IDR {_fmt_idr(long_exp)}",
                f"  Short    IDR {_fmt_idr(short_exp)}",
                f"  Beta vs IHSG  {_fmt_ratio(beta)}",
            ]
        )

    def _render_concentration(self) -> str:
        """Render concentration risk section."""
        conc = self.concentration_data
        hhi = conc.get("sector_hhi", 0)
        top5 = conc.get("top5_weight_pct", 0)
        largest_pct = conc.get("largest_position_pct", 0)
        largest_sym = conc.get("largest_position_symbol", "")
        num_pos = conc.get("num_positions", 0)

        return "\n".join(
            [
                "CONCENTRATION",
                f"  Sector HHI           {_fmt_ratio(hhi)}",
                f"  Top 5 positions      {top5:.1f}%",
                f"  Largest position     {largest_sym} ({largest_pct:.1f}%)",
                f"  Total positions      {num_pos}",
            ]
        )

    def _render_daily_loss(self) -> str:
        """Render daily loss monitor with progress bar."""
        loss = self.loss_data
        daily_loss = loss.get("daily_loss_idr", 0)
        limit_idr = loss.get("daily_loss_limit_idr", 0)
        utilization = loss.get("utilization_pct", 0)

        return "\n".join(
            [
                "DAILY LOSS MONITOR",
                f"  Loss     IDR {_fmt_idr(daily_loss)}  /  Limit IDR {_fmt_idr(limit_idr)}",
                f"  {_render_progress_bar(utilization)}",
            ]
        )

    def _render_drawdown(self) -> str:
        """Render drawdown monitor with progress bar."""
        dd = self.drawdown_data
        dd_pct = dd.get("drawdown_pct", 0)
        dd_limit = dd.get("drawdown_limit_pct", 0)
        utilization = dd.get("utilization_pct", 0)

        return "\n".join(
            [
                "DRAWDOWN MONITOR",
                f"  Current  {_fmt_pct(-dd_pct)}  /  Limit {_fmt_pct(-dd_limit)}",
                f"  {_render_progress_bar(utilization)}",
            ]
        )

    def _render_allocations(self) -> str:
        """Render capital allocation table."""
        alloc = self.allocation_data
        lines = [
            "CAPITAL ALLOCATION",
            f"{'Strategy':<22} {'Allocated':>14} {'Utilized':>14} {'Util%':>7} {'Sharpe':>7} {'Wt%':>6}",
        ]
        for entry in alloc:
            name = entry.get("strategy_name", entry.get("strategy_id", ""))[:20]
            allocated = entry.get("allocated_idr", 0)
            utilized = entry.get("utilized_idr", 0)
            util_pct = entry.get("utilization_pct", 0)
            sharpe = entry.get("sharpe_ratio", 0)
            weight = entry.get("weight_pct", 0)
            color = _threshold_color(util_pct)
            lines.append(
                f"{name:<22} {_fmt_idr(allocated):>14} {_fmt_idr(utilized):>14} "
                f"[{color}]{util_pct:>6.1f}%[/] {sharpe:>7.2f} {weight:>5.1f}%"
            )
        return "\n".join(lines)
