"""Reusable Textual widgets for the Pyhron terminal."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

# IDR formatting helpers
def fmt_idr(value: int | float) -> str:
    """Format number as IDR with period thousands separator."""
    n = int(value)
    s = f"{abs(n):,}".replace(",", ".")
    return f"-{s}" if n < 0 else s


def fmt_pct(value: float, sign: bool = True) -> str:
    """Format percentage with comma decimal separator."""
    prefix = "+" if sign and value > 0 else ""
    return f"{prefix}{value:.2f}%".replace(".", ",")


def fmt_change(value: int) -> str:
    prefix = "+" if value > 0 else ""
    return f"{prefix}{fmt_idr(value)}"


# Chart panel widget
class ChartWidget(Static):
    """Unicode candlestick chart for OHLCV data."""

    def render_chart(self, bars: list[Any], symbol: str = "", timeframe: str = "D1") -> None:
        if not bars:
            self.update(f"  {symbol} {timeframe} — No data")
            return

        # Extract prices
        highs = [getattr(b, "high", b.get("high", 0) if isinstance(b, dict) else 0) for b in bars]
        lows = [getattr(b, "low", b.get("low", 0) if isinstance(b, dict) else 0) for b in bars]
        opens = [getattr(b, "open", b.get("open", 0) if isinstance(b, dict) else 0) for b in bars]
        closes = [getattr(b, "close", b.get("close", 0) if isinstance(b, dict) else 0) for b in bars]

        if not highs:
            self.update(f"  {symbol} {timeframe} — No data")
            return

        max_p = max(highs)
        min_p = min(lows)
        price_range = max_p - min_p or 1

        chart_height = 12
        chart_width = min(len(bars), 50)
        use_highs = highs[-chart_width:]
        use_lows = lows[-chart_width:]
        use_opens = opens[-chart_width:]
        use_closes = closes[-chart_width:]

        grid: list[list[str]] = [[" " for _ in range(chart_width)] for _ in range(chart_height)]

        for col in range(chart_width):
            h = use_highs[col]
            lo = use_lows[col]
            o = use_opens[col]
            c = use_closes[col]

            h_row = chart_height - 1 - int((h - min_p) / price_range * (chart_height - 1))
            l_row = chart_height - 1 - int((lo - min_p) / price_range * (chart_height - 1))
            o_row = chart_height - 1 - int((o - min_p) / price_range * (chart_height - 1))
            c_row = chart_height - 1 - int((c - min_p) / price_range * (chart_height - 1))

            body_top = min(o_row, c_row)
            body_bot = max(o_row, c_row)

            for row in range(h_row, l_row + 1):
                if 0 <= row < chart_height:
                    if body_top <= row <= body_bot:
                        grid[row][col] = "\u2588" if c >= o else "\u2591"
                    else:
                        grid[row][col] = "\u2502"

        lines = [f"  {symbol} {timeframe}  Last: {fmt_idr(use_closes[-1])}"]
        for row_idx in range(chart_height):
            price_at_row = max_p - (row_idx / (chart_height - 1)) * price_range
            label = f"{int(price_at_row):>8} "
            lines.append(label + "".join(grid[row_idx]))

        self.update("\n".join(lines))


# Orderbook widget
class OrderbookWidget(Static):
    """Displays a live order book with depth bars."""

    def render_book(self, book: dict[str, list[dict[str, Any]]], symbol: str = "") -> None:
        asks = book.get("asks", [])
        bids = book.get("bids", [])

        lines = [f"  ORDER BOOK  {symbol}"]

        max_lots = 1
        for level in asks + bids:
            max_lots = max(max_lots, level.get("lots", level.get("size", 0)))

        lines.append("  ASK")
        for level in reversed(asks[:5]):
            price = level.get("price", 0)
            lots = level.get("lots", level.get("size", 0))
            bar_len = int(lots / max_lots * 20) if max_lots else 0
            bar = "\u2502" * bar_len
            lines.append(f"  {fmt_idr(price):>10}  {bar:<20} {fmt_idr(lots)}L")

        if asks and bids:
            best_ask = asks[0].get("price", 0)
            best_bid = bids[0].get("price", 0)
            spread = best_ask - best_bid
            spread_pct = spread / best_bid * 100 if best_bid else 0
            lines.append(f"  --- SPREAD: IDR {fmt_idr(spread)} ({fmt_pct(spread_pct, sign=False)}) ---")

        lines.append("  BID")
        for level in bids[:5]:
            price = level.get("price", 0)
            lots = level.get("lots", level.get("size", 0))
            bar_len = int(lots / max_lots * 20) if max_lots else 0
            bar = "\u2502" * bar_len
            lines.append(f"  {fmt_idr(price):>10}  {bar:<20} {fmt_idr(lots)}L")

        self.update("\n".join(lines))


# Positions widget
class PositionsWidget(Static):
    """Displays portfolio positions with P&L."""

    def render_positions(self, positions: list[Any]) -> None:
        header = f"  {'SYMBOL':<6} {'LOTS':>5} {'AVG':>8} {'LAST':>8} {'UNREALIZED PNL':>16} {'PCT':>7}"
        lines = [header, "  " + "-" * 58]
        total_pnl = 0

        for pos in positions:
            sym = getattr(pos, "symbol", "") if hasattr(pos, "symbol") else pos.get("symbol", "")
            lots = getattr(pos, "lots", 0) if hasattr(pos, "lots") else pos.get("lots", 0)
            avg = getattr(pos, "avg_cost", 0) if hasattr(pos, "avg_cost") else pos.get("avg_cost", 0)
            last = getattr(pos, "last_price", 0) if hasattr(pos, "last_price") else pos.get("last_price", 0)
            pnl = getattr(pos, "unrealized_pnl", 0) if hasattr(pos, "unrealized_pnl") else pos.get("unrealized_pnl", 0)
            pct = getattr(pos, "pnl_pct", 0.0) if hasattr(pos, "pnl_pct") else pos.get("pnl_pct", 0.0)
            total_pnl += pnl

            pnl_str = fmt_change(pnl)
            pct_str = fmt_pct(pct)
            lines.append(f"  {sym:<6} {lots:>4}L {fmt_idr(avg):>8} {fmt_idr(last):>8} {pnl_str:>16} {pct_str:>7}")

        lines.append("  " + "-" * 58)
        total_str = fmt_change(total_pnl)
        lines.append(f"  {'TOTAL':<6} {'':>5} {'':>8} {'':>8} {total_str:>16}")

        self.update("\n".join(lines))


# Orders widget
class OrdersWidget(Static):
    """Displays today's orders."""

    def render_orders(self, orders: list[Any]) -> None:
        header = (
            f"  {'TIME':<6} {'SYMBOL':<6} {'SIDE':<5} {'LOTS':>5} {'TYPE':<7} {'PRICE':>8} {'STATUS':<18} {'FILLED':>6}"
        )
        lines = [header, "  " + "-" * 68]

        for o in orders:
            t = getattr(o, "time", "") if hasattr(o, "time") else o.get("time", "")
            sym = getattr(o, "symbol", "") if hasattr(o, "symbol") else o.get("symbol", "")
            side = getattr(o, "side", "") if hasattr(o, "side") else o.get("side", "")
            lots = getattr(o, "lots", 0) if hasattr(o, "lots") else o.get("lots", 0)
            otype = getattr(o, "order_type", "") if hasattr(o, "order_type") else o.get("order_type", "")
            price = getattr(o, "price", None) if hasattr(o, "price") else o.get("price")
            status = getattr(o, "status", "") if hasattr(o, "status") else o.get("status", "")
            filled = getattr(o, "filled_lots", 0) if hasattr(o, "filled_lots") else o.get("filled_lots", 0)

            price_str = fmt_idr(price) if price else "-"
            lines.append(f"  {t:<6} {sym:<6} {side:<5} {lots:>4}L {otype:<7} {price_str:>8} {status:<18} {filled:>5}L")

        self.update("\n".join(lines))


# Momentum signals widget
class MomentumWidget(Static):
    """Displays momentum strategy signals."""

    def render_signals(self, signals: list[dict[str, Any]]) -> None:
        longs = [s for s in signals if s.get("action") != "EXIT"]
        exits = [s for s in signals if s.get("action") == "EXIT"]

        lines = [
            "  MOMENTUM SIGNALS",
            f"  Universe: {len(signals)} entries",
            "",
            f"  LONG PORTFOLIO ({len(longs)} stocks)",
            f"  {'RANK':>4} {'SYMBOL':<6} {'SECTOR':<12} {'SCORE':>7} {'TARGET%':>8} {'LOTS':>5} {'ACTION':<6}",
            "  " + "-" * 52,
        ]

        for s in longs:
            lines.append(
                f"  {s.get('rank', 0):>4} {s.get('symbol', ''):<6} "
                f"{s.get('sector', ''):<12} {s.get('score', 0):>+7.3f} "
                f"{s.get('target_pct', 0):>7.1f}% {s.get('lots', 0):>5} "
                f"{s.get('action', ''):<6}"
            )

        if exits:
            lines.append("")
            lines.append(f"  EXIT ({len(exits)} stocks)")
            for s in exits:
                lines.append(
                    f"       {s.get('symbol', ''):<6} {s.get('sector', ''):<12} {s.get('score', 0):>+7.3f}  EXIT"
                )

        self.update("\n".join(lines))


# Order confirmation dialog
class OrderConfirmDialog(ModalScreen[bool]):
    """Modal confirmation dialog before order submission."""

    def __init__(
        self,
        symbol: str,
        side: str,
        lots: int,
        order_type: str,
        estimated_value: int = 0,
        estimated_cost: int = 0,
        current_lots: int = 0,
    ) -> None:
        super().__init__()
        self._symbol = symbol
        self._side = side
        self._lots = lots
        self._order_type = order_type
        self._estimated_value = estimated_value
        self._estimated_cost = estimated_cost
        self._current_lots = current_lots

    def compose(self) -> ComposeResult:
        after = self._current_lots + self._lots if self._side == "BUY" else self._current_lots - self._lots

        with Vertical(classes="dialog-content"):
            yield Label("ORDER CONFIRMATION", classes="dialog-title")
            yield Static("")
            yield Static(f"  {self._side} {self._symbol} {self._lots} LOTS {self._order_type}")
            yield Static("")
            yield Static(f"  Estimated value: IDR {fmt_idr(self._estimated_value)}")
            yield Static(f"  Estimated cost:  IDR {fmt_idr(self._estimated_cost)}")
            yield Static(f"  Current position: {self._current_lots} lots")
            yield Static(f"  After order:      {after} lots")
            yield Static("")
            if self._order_type == "LIMIT":
                yield Input(placeholder="Enter limit price", id="limit-price-input")
            yield Static("  CONFIRM: Enter    CANCEL: Esc")

    def key_enter(self) -> None:
        self.dismiss(True)

    def key_escape(self) -> None:
        self.dismiss(False)
