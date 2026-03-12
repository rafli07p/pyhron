"""Watchlist panel — real-time price table for tracked IDX symbols."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


def _fmt_idr(value: int) -> str:
    """Format integer as IDR with period separators."""
    s = f"{abs(value):,}".replace(",", ".")
    return f"-{s}" if value < 0 else s


def _fmt_pct(value: float) -> str:
    """Format percentage with sign and comma decimal."""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%".replace(".", ",")


def _fmt_change(value: int) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{_fmt_idr(value)}"


def _fmt_vol(value: int) -> str:
    """Format volume in lots with period separator."""
    return f"{value:,}".replace(",", ".")


def _fmt_val_b(value: float) -> str:
    """Format value in billions."""
    return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


class WatchlistPanel(Static):
    """Displays a live watchlist table of IDX symbols.

    Updates are driven by the parent app calling ``update_quotes()``.
    """

    quotes: reactive[list[dict[str, Any]]] = reactive(list, recompose=True)

    def compose(self) -> ComposeResult:
        yield Static(self._render_table(), id="watchlist-content")

    def update_quotes(self, data: list[dict[str, Any]]) -> None:
        self.quotes = list(data)

    def watch_quotes(self) -> None:
        try:
            content = self.query_one("#watchlist-content", Static)
            content.update(self._render_table())
        except Exception:
            pass

    def _render_table(self) -> str:
        header = f"{'SYMBOL':<6} {'LAST':>8} {'CHG':>7} {'CHG%':>7} {'VOL(L)':>8} {'VAL(B)':>7}"
        lines = [header, "-" * 50]

        for q in self.quotes:
            sym = str(q.get("symbol", ""))[:6]
            last = _fmt_idr(q.get("last", 0))
            chg = _fmt_change(q.get("change", 0))
            pct = _fmt_pct(q.get("change_pct", 0.0))
            vol = _fmt_vol(q.get("volume_lots", 0))
            val = _fmt_val_b(q.get("value_billion", 0.0))

            lines.append(f"{sym:<6} {last:>8} {chg:>7} {pct:>7} {vol:>8} {val:>7}")

        return "\n".join(lines) if lines else "No data"
