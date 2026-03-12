"""Synthetic data provider for Pyhron Terminal demo mode.

Generates realistic IDX market data using geometric Brownian motion
with IDX ARA/ARB circuit breaker limits (35% from previous close).
Makes zero network calls.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")

_ARA_ARB_LIMIT = 0.35  # IDX circuit breaker: 35% max move per session

DEFAULT_SYMBOLS = [
    "BBCA",
    "BBRI",
    "BMRI",
    "TLKM",
    "ASII",
    "UNVR",
    "ICBP",
    "KLBF",
    "ADRO",
    "INDF",
]

DEFAULT_PRICES_IDR: dict[str, int] = {
    "BBCA": 9250,
    "BBRI": 5100,
    "BMRI": 7350,
    "TLKM": 3890,
    "ASII": 4720,
    "UNVR": 4280,
    "ICBP": 10500,
    "KLBF": 1680,
    "ADRO": 2840,
    "INDF": 7125,
}

DEFAULT_SECTORS: dict[str, str] = {
    "BBCA": "Banking",
    "BBRI": "Banking",
    "BMRI": "Banking",
    "TLKM": "Telecom",
    "ASII": "Auto",
    "UNVR": "Consumer",
    "ICBP": "Consumer",
    "KLBF": "Healthcare",
    "ADRO": "Mining",
    "INDF": "Consumer",
}


@dataclass
class QuoteData:
    """A single price quote."""

    symbol: str
    last: int
    change: int
    change_pct: float
    bid: int
    ask: int
    bid_size: int
    ask_size: int
    volume_lots: int
    value_billion: float
    timestamp: datetime


@dataclass
class PositionData:
    """A portfolio position."""

    symbol: str
    lots: int
    avg_cost: int
    last_price: int
    unrealized_pnl: int
    pnl_pct: float


@dataclass
class OrderData:
    """An order record."""

    order_id: str
    time: str
    symbol: str
    side: str
    lots: int
    order_type: str
    price: int | None
    status: str
    filled_lots: int


@dataclass
class OHLCVBar:
    """A single OHLCV bar."""

    timestamp: datetime
    open: int
    high: int
    low: int
    close: int
    volume: int


class DemoDataProvider:
    """Generates synthetic IDX market data for offline demonstration.

    Price model: geometric Brownian motion.
    Daily volatility: 0.018 (1.8%, typical IDX large cap).
    Daily drift: 0.0003.

    Simulates quote updates every 2 seconds, realistic bid/ask spread
    of 0.1%, volume clustering near session open and close, and a
    pre-seeded demo portfolio with positions and orders.
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)
        self._base_prices = dict(DEFAULT_PRICES_IDR)
        self._current_prices: dict[str, float] = {s: float(p) for s, p in self._base_prices.items()}
        self._session_open: dict[str, float] = dict(self._current_prices)
        self._prev_close: dict[str, float] = dict(self._current_prices)
        self._tick_count: dict[str, int] = {s: 0 for s in DEFAULT_SYMBOLS}
        self._volatility = 0.018
        self._drift = 0.0003

        # Pre-seed portfolio
        self._positions: list[PositionData] = [
            PositionData("BBCA", 50, 9100, 9250, 750000, 1.65),
            PositionData("TLKM", 100, 3900, 3890, -100000, -0.26),
            PositionData("ADRO", 30, 2780, 2840, 180000, 2.16),
        ]
        self._orders: list[OrderData] = [
            OrderData("ORD-001", "10:15", "BBCA", "BUY", 10, "LIMIT", 9150, "FILLED", 10),
            OrderData("ORD-002", "10:47", "BMRI", "SELL", 5, "LIMIT", 7400, "PENDING", 0),
            OrderData("ORD-003", "11:02", "TLKM", "BUY", 20, "MARKET", None, "PARTIALLY_FILLED", 12),
        ]

    def get_quote(self, symbol: str) -> QuoteData:
        """Generate next simulated quote with GBM step."""
        if symbol not in self._current_prices:
            price = 5000.0
            self._current_prices[symbol] = price
            self._prev_close[symbol] = price
            self._session_open[symbol] = price

        price = self._current_prices[symbol]

        # GBM step
        z = self._rng.gauss(0, 1)
        dt = 2.0 / (6.5 * 3600)  # 2-second tick as fraction of trading day
        new_price = price * math.exp(
            (self._drift - 0.5 * self._volatility**2) * dt + self._volatility * math.sqrt(dt) * z
        )

        # ARA/ARB clamp
        prev = self._prev_close[symbol]
        upper = prev * (1 + _ARA_ARB_LIMIT)
        lower = prev * (1 - _ARA_ARB_LIMIT)
        new_price = max(lower, min(upper, new_price))

        # IDX tick rounding (to nearest 5 for prices < 5000, 25 for >= 5000)
        if new_price < 200:
            new_price = round(new_price / 1) * 1
        elif new_price < 500:
            new_price = round(new_price / 2) * 2
        elif new_price < 2000:
            new_price = round(new_price / 5) * 5
        elif new_price < 5000:
            new_price = round(new_price / 10) * 10
        else:
            new_price = round(new_price / 25) * 25

        new_price = max(new_price, 50)  # min price
        self._current_prices[symbol] = new_price

        last = int(new_price)
        prev_int = int(prev)
        change = last - prev_int
        change_pct = (change / prev_int * 100) if prev_int else 0.0

        spread_bps = max(1, int(last * 0.001))
        bid = last - spread_bps
        ask = last + spread_bps

        self._tick_count[symbol] = self._tick_count.get(symbol, 0) + 1
        base_vol = self._rng.randint(5000, 50000)

        return QuoteData(
            symbol=symbol,
            last=last,
            change=change,
            change_pct=round(change_pct, 2),
            bid=bid,
            ask=ask,
            bid_size=self._rng.randint(100, 5000),
            ask_size=self._rng.randint(100, 5000),
            volume_lots=base_vol + self._tick_count[symbol] * 10,
            value_billion=round(base_vol * last / 1_000_000_000, 1),
            timestamp=datetime.now(tz=WIB),
        )

    def get_positions(self) -> list[PositionData]:
        """Return current demo positions with updated P&L."""
        result: list[PositionData] = []
        for pos in self._positions:
            last = int(self._current_prices.get(pos.symbol, pos.last_price))
            pnl = (last - pos.avg_cost) * pos.lots * 100
            pnl_pct = round((last - pos.avg_cost) / pos.avg_cost * 100, 2) if pos.avg_cost else 0.0
            result.append(
                PositionData(
                    symbol=pos.symbol,
                    lots=pos.lots,
                    avg_cost=pos.avg_cost,
                    last_price=last,
                    unrealized_pnl=pnl,
                    pnl_pct=pnl_pct,
                )
            )
        return result

    def get_orders(self) -> list[OrderData]:
        """Return demo orders."""
        return list(self._orders)

    def get_orderbook(self, symbol: str) -> dict[str, list[dict[str, Any]]]:
        """Generate synthetic order book for a symbol."""
        price = int(self._current_prices.get(symbol, 5000))
        tick = 25 if price >= 5000 else 10 if price >= 2000 else 5

        asks: list[dict[str, Any]] = []
        bids: list[dict[str, Any]] = []
        for i in range(5):
            asks.append(
                {
                    "price": price + (i + 1) * tick,
                    "lots": self._rng.randint(100, 5000),
                }
            )
            bids.append(
                {
                    "price": price - i * tick,
                    "lots": self._rng.randint(100, 5000),
                }
            )

        return {"asks": asks, "bids": bids}

    def get_ohlcv(self, symbol: str, n_bars: int = 60) -> list[OHLCVBar]:
        """Generate historical OHLCV bars using GBM."""
        base = self._base_prices.get(symbol, 5000)
        price = float(base)
        bars: list[OHLCVBar] = []
        now = datetime.now(tz=WIB)

        for i in range(n_bars, 0, -1):
            z = self._rng.gauss(0, 1)
            ret = (self._drift - 0.5 * self._volatility**2) + self._volatility * z
            price = price * math.exp(ret)
            price = max(price, 50)

            o = int(price)
            h = int(price * (1 + abs(self._rng.gauss(0, 0.01))))
            lo = int(price * (1 - abs(self._rng.gauss(0, 0.01))))
            c = int(price * (1 + self._rng.gauss(0, 0.005)))
            c = max(lo, min(h, c))
            vol = self._rng.randint(1_000_000, 50_000_000)

            bars.append(
                OHLCVBar(
                    timestamp=now - timedelta(days=i),
                    open=o,
                    high=h,
                    low=lo,
                    close=c,
                    volume=vol,
                )
            )

        return bars

    def get_momentum_signals(self) -> list[dict[str, Any]]:
        """Return synthetic momentum signals."""
        signals: list[dict[str, Any]] = []
        for i, symbol in enumerate(DEFAULT_SYMBOLS[:5]):
            score = round(0.85 - i * 0.07 + self._rng.gauss(0, 0.02), 3)
            signals.append(
                {
                    "rank": i + 1,
                    "symbol": symbol,
                    "sector": DEFAULT_SECTORS.get(symbol, ""),
                    "score": score,
                    "target_pct": round(3.2 - i * 0.3, 1),
                    "lots": self._rng.randint(10, 200),
                    "action": "ENTRY" if i % 3 == 0 else "HOLD",
                }
            )
        # Add exits
        for symbol in ["BBRI", "ASII"]:
            signals.append(
                {
                    "rank": 0,
                    "symbol": symbol,
                    "sector": DEFAULT_SECTORS.get(symbol, ""),
                    "score": round(-0.05 - self._rng.random() * 0.15, 3),
                    "target_pct": 0.0,
                    "lots": 0,
                    "action": "EXIT",
                }
            )
        return signals

    def get_ihsg(self) -> tuple[float, float]:
        """Return synthetic IHSG index value and change percent."""
        base = 7234.56
        change = self._rng.gauss(0, 30)
        return round(base + change, 2), round(change / base * 100, 2)

    def submit_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity_lots: int,
        limit_price: int | None,
    ) -> OrderData:
        """Simulate order submission."""
        oid = f"ORD-DEMO-{int(time.time())}"
        now = datetime.now(tz=WIB)
        order = OrderData(
            order_id=oid,
            time=now.strftime("%H:%M"),
            symbol=symbol,
            side=side,
            lots=quantity_lots,
            order_type=order_type,
            price=limit_price,
            status="FILLED" if order_type == "MARKET" else "PENDING",
            filled_lots=quantity_lots if order_type == "MARKET" else 0,
        )
        self._orders.insert(0, order)
        return order

    def get_instruments(self) -> list[dict[str, str]]:
        """Return instrument universe."""
        return [{"symbol": s, "sector": DEFAULT_SECTORS.get(s, ""), "lot_size": "100"} for s in DEFAULT_SYMBOLS]
