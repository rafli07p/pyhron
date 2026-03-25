# Pyhron API Documentation

## Overview

The Pyhron REST API provides programmatic access to market data, order management, portfolio tracking, backtesting, paper trading, and administrative functions for the IDX quantitative trading platform.

**Base URL:** `http://localhost:8000`

Auto-generated OpenAPI/Swagger docs are available at `/docs` when the FastAPI server is running. ReDoc is at `/redoc`.

## Authentication

All endpoints (except health checks) require a Bearer JWT token:

```
Authorization: Bearer <your-jwt-token>
```

To obtain a token:
```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "trader@pyhron.dev", "password": "your_password"}'
```

Roles: `admin`, `trader`, `analyst`, `readonly`

## Request/Response Format

- All bodies use JSON
- Decimal values (prices, quantities) are strings to avoid floating-point issues
- Timestamps are ISO 8601 with UTC timezone: `2024-01-15T09:30:00Z`

## Endpoints

### Market Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/market-data/quotes/{symbol}` | Latest quote for a symbol |
| POST | `/v1/market-data/quotes/batch` | Quotes for multiple symbols |
| GET | `/v1/market-data/bars/{symbol}` | Historical OHLCV bars |

**Example:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/market-data/quotes/BBCA
```

```json
{
  "symbol": "BBCA",
  "price": "9250.00",
  "bid": "9245.00",
  "ask": "9255.00",
  "volume": 15000000,
  "timestamp": "2024-01-15T09:30:00Z",
  "exchange": "IDX"
}
```

### Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/orders` | Submit a new order |
| GET | `/v1/orders` | List orders (with filters) |
| GET | `/v1/orders/{order_id}` | Get order status |
| DELETE | `/v1/orders/{order_id}` | Cancel an order |

**Order status values:** `pending_risk`, `risk_approved`, `submitted`, `acknowledged`, `partial_fill`, `filled`, `cancelled`, `rejected`

### Backtest

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/backtest/run` | Submit async backtest job (202) |
| GET | `/v1/backtest/{task_id}` | Get backtest status/result |
| GET | `/v1/backtest/{task_id}/metrics` | Detailed performance metrics |
| GET | `/v1/backtest/history` | Browse past backtests |

**Submit backtest:**
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8000/v1/backtest/run \
  -d '{
    "strategy_type": "momentum",
    "symbols": ["BBCA", "BBRI", "TLKM", "ASII"],
    "start_date": "2023-01-01",
    "end_date": "2024-12-31",
    "initial_capital": "1000000000",
    "slippage_bps": 5.0
  }'
```

**Response (202):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "submitted",
  "submitted_at": "2024-01-15T09:30:00Z"
}
```

**Get metrics:**
```json
{
  "task_id": "550e8400-...",
  "total_return_pct": 15.42,
  "cagr_pct": 7.8,
  "sharpe_ratio": 1.23,
  "sortino_ratio": 1.67,
  "calmar_ratio": 0.89,
  "max_drawdown_pct": -8.75,
  "win_rate_pct": 55.3,
  "profit_factor": 1.45,
  "total_trades": 142
}
```

### Paper Trading

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/paper-trading/sessions` | Create paper trading session |
| POST | `/v1/paper-trading/sessions/{id}/start` | Start session |
| POST | `/v1/paper-trading/sessions/{id}/pause` | Pause session |
| POST | `/v1/paper-trading/sessions/{id}/resume` | Resume session |
| POST | `/v1/paper-trading/sessions/{id}/stop` | Stop and get summary |
| GET | `/v1/paper-trading/sessions/{id}/nav` | Get NAV snapshot |

### Portfolio

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/portfolio/positions` | Get open positions |
| GET | `/v1/portfolio/pnl` | P&L breakdown |
| GET | `/v1/portfolio/summary` | Portfolio summary with NAV |

### Risk

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/risk/check` | Pre-trade risk check |
| GET | `/v1/risk/metrics` | Current risk metrics |

### Admin (requires ADMIN role)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/admin/users` | List users |
| POST | `/v1/admin/users` | Create user |
| GET | `/v1/admin/audit-log` | Query audit log |

### Health & Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/ready` | Readiness probe |
| GET | `/health/live` | Liveness probe |
| GET | `/metrics` | Prometheus metrics |

## WebSocket

Connect to `ws://localhost:8000/ws` for real-time data streaming.

**Subscribe to market data:**
```json
{
  "action": "subscribe",
  "channels": ["quotes"],
  "symbols": ["BBCA", "TLKM"]
}
```

**Message types received:**
- `QUOTE_UPDATE` — EOD price updates
- `TRADE_UPDATE` — Intraday trades
- `BAR_UPDATE` — Intraday minute bars
- `ORDER_UPDATE` — Order status changes
- `POSITION_UPDATE` — Position changes
- `SIGNAL_UPDATE` — Strategy signals
- `PAPER_NAV_UPDATE` — Paper trading NAV
- `PAPER_REBALANCE_UPDATE` — Paper rebalance results

## Rate Limits

| Endpoint Group | Limit |
|---------------|-------|
| Market Data | 100 req/min |
| Order Submission | 50 req/min |
| Backtest Execution | 10 req/min |
| Health/Metrics | Unlimited |

## Error Responses

```json
{
  "error": {
    "code": "RISK_LIMIT_EXCEEDED",
    "message": "Order exceeds maximum position size limit",
    "details": {
      "current_position": "8500000.00",
      "limit": "10000000.00"
    }
  },
  "request_id": "req-abc123"
}
```

Common codes: `VALIDATION_ERROR` (422), `AUTHENTICATION_REQUIRED` (401), `FORBIDDEN` (403), `NOT_FOUND` (404), `RISK_LIMIT_EXCEEDED` (400), `RATE_LIMITED` (429), `INTERNAL_ERROR` (500).
