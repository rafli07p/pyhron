"""
Locust load test for the Enthropy Trading Platform.

Tests concurrent trade submissions, market data requests, and mixed workloads
to validate system performance under heavy load.

Usage:
  locust -f tests/benchmarks/locustfile.py --host=http://localhost:8000
  locust -f tests/benchmarks/locustfile.py --host=http://localhost:8000 \
         --users 1000 --spawn-rate 50 --run-time 5m --headless
"""

from __future__ import annotations

import random
from uuid import uuid4

from locust import HttpUser, between, events, tag, task
from locust.runners import MasterRunner

# =============================================================================
# Configuration
# =============================================================================
IDX_SYMBOLS = [
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK",
    "UNVR.JK", "HMSP.JK", "GGRM.JK", "ICBP.JK", "KLBF.JK",
    "BBNI.JK", "INDF.JK", "PGAS.JK", "SMGR.JK", "JSMR.JK",
    "PTBA.JK", "ADRO.JK", "ANTM.JK", "INCO.JK", "EXCL.JK",
]

STRATEGIES = [
    "momentum_v1", "mean_reversion_v2", "pairs_trading_v1",
    "stat_arb_v3", "ml_alpha_v1", "value_factor_v1",
]

API_KEY = "load-test-api-key"


# =============================================================================
# Event Hooks
# =============================================================================
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test start."""
    if isinstance(environment.runner, MasterRunner):
        pass


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print summary statistics."""


# =============================================================================
# Helper Functions
# =============================================================================
def random_order_payload() -> dict:
    """Generate a random order payload."""
    symbol = random.choice(IDX_SYMBOLS)
    side = random.choice(["buy", "sell"])
    order_type = random.choice(["market", "limit"])
    quantity = random.choice([100, 200, 500, 1000, 2000, 5000]) * 100  # Lot sizes

    price = None
    if order_type == "limit":
        base_price = random.uniform(1000, 50000)
        # Round to IDX tick size
        if base_price < 200:
            price = round(base_price)
        elif base_price < 500:
            price = round(base_price / 2) * 2
        elif base_price < 2000:
            price = round(base_price / 5) * 5
        elif base_price < 5000:
            price = round(base_price / 10) * 10
        else:
            price = round(base_price / 25) * 25

    payload = {
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": str(quantity),
        "strategy_id": random.choice(STRATEGIES),
        "client_order_id": str(uuid4()),
    }
    if price:
        payload["price"] = str(price)

    return payload


def random_backtest_payload() -> dict:
    """Generate a random backtest request payload."""
    num_symbols = random.randint(1, 5)
    symbols = random.sample(IDX_SYMBOLS, num_symbols)

    return {
        "symbols": symbols,
        "strategy": random.choice(STRATEGIES),
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "initial_capital": str(random.choice([100000000, 500000000, 1000000000])),
        "commission_rate": "0.0015",
    }


# =============================================================================
# Trade Submission User
# =============================================================================
class TradeSubmissionUser(HttpUser):
    """Simulates a high-frequency trade submission client."""

    wait_time = between(0.1, 0.5)
    weight = 5  # 5x more common than other users

    def on_start(self):
        """Set authentication headers."""
        self.client.headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "X-Request-ID": str(uuid4()),
        }

    @tag("trades", "critical")
    @task(10)
    def submit_single_order(self):
        """Submit a single trade order."""
        payload = random_order_payload()
        with self.client.post(
            "/api/v1/orders",
            json=payload,
            name="/api/v1/orders [POST]",
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                response.success()
            elif response.status_code == 422:
                # Validation errors are expected for some random payloads
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @tag("trades", "critical")
    @task(3)
    def submit_batch_orders(self):
        """Submit a batch of orders."""
        batch_size = random.randint(5, 20)
        orders = [random_order_payload() for _ in range(batch_size)]

        with self.client.post(
            "/api/v1/orders/batch",
            json={"orders": orders},
            name="/api/v1/orders/batch [POST]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201, 207):
                response.success()
            else:
                response.failure(f"Batch failed: {response.status_code}")

    @tag("trades")
    @task(5)
    def get_order_status(self):
        """Check order status (simulates polling)."""
        order_id = str(uuid4())
        with self.client.get(
            f"/api/v1/orders/{order_id}",
            name="/api/v1/orders/{order_id} [GET]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            else:
                response.failure(f"Status check failed: {response.status_code}")

    @tag("trades")
    @task(2)
    def cancel_order(self):
        """Cancel an order."""
        order_id = str(uuid4())
        with self.client.delete(
            f"/api/v1/orders/{order_id}",
            name="/api/v1/orders/{order_id} [DELETE]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            else:
                response.failure(f"Cancel failed: {response.status_code}")


# =============================================================================
# Market Data User
# =============================================================================
class MarketDataUser(HttpUser):
    """Simulates a market data consumer requesting quotes and historical data."""

    wait_time = between(0.05, 0.3)
    weight = 3

    def on_start(self):
        self.client.headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }

    @tag("market-data", "critical")
    @task(10)
    def get_latest_quote(self):
        """Fetch the latest quote for a symbol."""
        symbol = random.choice(IDX_SYMBOLS)
        with self.client.get(
            f"/api/v1/market-data/quotes/{symbol}",
            name="/api/v1/market-data/quotes/{symbol} [GET]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "price" in data and float(data["price"]) > 0:
                    response.success()
                else:
                    response.failure("Invalid quote data")
            else:
                response.failure(f"Quote failed: {response.status_code}")

    @tag("market-data")
    @task(3)
    def get_batch_quotes(self):
        """Fetch quotes for multiple symbols."""
        num_symbols = random.randint(5, 15)
        symbols = random.sample(IDX_SYMBOLS, num_symbols)

        with self.client.post(
            "/api/v1/market-data/quotes/batch",
            json={"symbols": symbols},
            name="/api/v1/market-data/quotes/batch [POST]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Batch quotes failed: {response.status_code}")

    @tag("market-data")
    @task(2)
    def get_historical_bars(self):
        """Fetch historical OHLCV bars."""
        symbol = random.choice(IDX_SYMBOLS)
        with self.client.get(
            f"/api/v1/market-data/bars/{symbol}",
            params={
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "interval": "1d",
            },
            name="/api/v1/market-data/bars/{symbol} [GET]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Historical data failed: {response.status_code}")

    @tag("market-data")
    @task(1)
    def get_order_book(self):
        """Fetch order book (depth of market)."""
        symbol = random.choice(IDX_SYMBOLS)
        with self.client.get(
            f"/api/v1/market-data/orderbook/{symbol}",
            params={"depth": 10},
            name="/api/v1/market-data/orderbook/{symbol} [GET]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404):
                response.success()
            else:
                response.failure(f"Order book failed: {response.status_code}")


# =============================================================================
# Portfolio & Analytics User
# =============================================================================
class PortfolioUser(HttpUser):
    """Simulates portfolio management and analytics requests."""

    wait_time = between(1, 3)
    weight = 1

    def on_start(self):
        self.client.headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }

    @tag("portfolio")
    @task(5)
    def get_positions(self):
        """Fetch current positions."""
        with self.client.get(
            "/api/v1/portfolio/positions",
            name="/api/v1/portfolio/positions [GET]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Positions failed: {response.status_code}")

    @tag("portfolio")
    @task(3)
    def get_pnl_summary(self):
        """Fetch PnL summary."""
        with self.client.get(
            "/api/v1/portfolio/pnl",
            params={"period": random.choice(["today", "week", "month", "ytd"])},
            name="/api/v1/portfolio/pnl [GET]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"PnL failed: {response.status_code}")

    @tag("portfolio")
    @task(2)
    def get_risk_metrics(self):
        """Fetch current risk metrics."""
        with self.client.get(
            "/api/v1/risk/metrics",
            name="/api/v1/risk/metrics [GET]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Risk metrics failed: {response.status_code}")

    @tag("analytics")
    @task(1)
    def run_backtest(self):
        """Submit a backtest request (heavy operation)."""
        payload = random_backtest_payload()
        with self.client.post(
            "/api/v1/backtest/run",
            json=payload,
            name="/api/v1/backtest/run [POST]",
            timeout=120,
            catch_response=True,
        ) as response:
            if response.status_code in (200, 202):
                response.success()
            else:
                response.failure(f"Backtest failed: {response.status_code}")

    @tag("health")
    @task(2)
    def health_check(self):
        """Health check endpoint."""
        with self.client.get(
            "/health",
            name="/health [GET]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @tag("health")
    @task(1)
    def metrics_endpoint(self):
        """Prometheus metrics endpoint."""
        with self.client.get(
            "/metrics",
            name="/metrics [GET]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Metrics failed: {response.status_code}")
