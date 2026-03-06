# Enthropy API Documentation

## Overview

The Enthropy REST API provides programmatic access to market data, order management, portfolio tracking, research tools, risk management, and administrative functions for the quantitative trading platform.

**Base URL:** `http://localhost:8000/api/v1`

Auto-generated OpenAPI/Swagger docs are available at `/docs` when the FastAPI server is running. ReDoc is at `/redoc`.

## Authentication

All endpoints require a Bearer JWT token in the `Authorization` header:

```
Authorization: Bearer <your-jwt-token>
```

Multi-tenancy is enforced via `tenant_id` extracted from the JWT claims. API keys for service-to-service communication can be configured via the `X-API-Key` header.

To obtain a token:

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "trader@enthropy.dev", "password": "your_password"}'
```

## Request/Response Format

All request and response bodies use JSON. Decimal values (prices, quantities) are sent as strings to avoid floating-point precision issues:

```json
{
  "symbol": "BBCA.JK",
  "quantity": "1000",
  "price": "9200.00"
}
```

Timestamps are in ISO 8601 format with UTC timezone: `2024-01-15T09:30:00Z`

## Endpoints

### Market Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/market-data/quotes/{symbol}` | Get latest quote for a symbol |
| POST | `/market-data/quotes/batch` | Get quotes for multiple symbols |
| GET | `/market-data/bars/{symbol}` | Get historical OHLCV bars |
| GET | `/market-data/orderbook/{symbol}` | Get order book (depth of market) |
| GET | `/market-data/trades/{symbol}` | Get recent trades |

**Example: Get Latest Quote**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/market-data/quotes/BBCA.JK
```

**Response:**
```json
{
  "symbol": "BBCA.JK",
  "price": "9250.00",
  "bid": "9245.00",
  "ask": "9255.00",
  "volume": 1500000,
  "timestamp": "2024-01-15T09:30:00Z",
  "exchange": "IDX"
}
```

### Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/orders` | Submit a new order |
| POST | `/orders/batch` | Submit multiple orders |
| GET | `/orders` | List orders (with filters) |
| GET | `/orders/{order_id}` | Get order status |
| DELETE | `/orders/{order_id}` | Cancel an order |

**Example: Submit Order**
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8000/api/v1/orders \
  -d '{
    "symbol": "BBCA.JK",
    "side": "buy",
    "order_type": "limit",
    "quantity": "1000",
    "price": "9200.00",
    "strategy_id": "momentum_v1"
  }'
```

**Response:**
```json
{
  "order_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "symbol": "BBCA.JK",
  "side": "buy",
  "order_type": "limit",
  "quantity": "1000",
  "price": "9200.00",
  "created_at": "2024-01-15T09:30:00Z"
}
```

**Order Status Values:** `pending`, `accepted`, `partially_filled`, `filled`, `cancelled`, `rejected`, `risk_rejected`, `expired`

### Portfolio

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/portfolio/positions` | Get open positions |
| GET | `/portfolio/pnl` | Get PnL breakdown (query: `period=today\|week\|month\|ytd`) |
| GET | `/portfolio/summary` | Get portfolio summary with NAV |
| GET | `/portfolio/history` | Get portfolio value history |

### Risk

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/risk/check` | Run pre-trade risk check |
| GET | `/risk/metrics` | Get current risk metrics (VaR, exposure, drawdown) |
| GET | `/risk/limits` | Get configured risk limits |
| GET | `/risk/violations` | Get recent risk violations |

### Backtest

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/backtest/run` | Run a backtest (async, returns job ID) |
| GET | `/backtest/{job_id}` | Get backtest status and results |
| GET | `/backtest/history` | List past backtest runs |

### Research

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/research/factors` | List available factors |
| GET | `/research/datasets` | List datasets |
| POST | `/research/analyze` | Run factor analysis |

### Admin (RBAC: ADMIN role required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/users` | List users |
| POST | `/admin/users` | Create user |
| PUT | `/admin/users/{id}` | Update user |
| DELETE | `/admin/users/{id}` | Deactivate user |
| GET | `/admin/audit-log` | Query audit log |
| POST | `/admin/compliance/export` | Export compliance report |

### Health & Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/ready` | Readiness probe (K8s) |
| GET | `/health/live` | Liveness probe (K8s) |
| GET | `/metrics` | Prometheus metrics endpoint |

## WebSocket

Connect to `ws://localhost:8000/ws/market-data` for real-time market data streaming.

**Subscription message:**
```json
{
  "action": "subscribe",
  "symbols": ["BBCA.JK", "TLKM.JK"],
  "channels": ["quotes", "trades"]
}
```

## Rate Limits

| Endpoint Group | Limit |
|---------------|-------|
| Market Data | 100 requests/minute |
| Order Submission | 50 requests/minute |
| Backtest Execution | 10 requests/minute |
| Admin Operations | 30 requests/minute |
| Health/Metrics | Unlimited |

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705312800
```

## Error Responses

All errors follow a consistent format:

```json
{
  "error": {
    "code": "RISK_LIMIT_EXCEEDED",
    "message": "Order exceeds maximum position size limit",
    "details": {
      "current_position": "8500000.00",
      "order_notional": "4600000.00",
      "limit": "10000000.00"
    }
  },
  "request_id": "req-abc123"
}
```

**Common Error Codes:**
- `VALIDATION_ERROR` (422) - Invalid request parameters
- `AUTHENTICATION_REQUIRED` (401) - Missing or invalid token
- `FORBIDDEN` (403) - Insufficient permissions
- `NOT_FOUND` (404) - Resource not found
- `RISK_LIMIT_EXCEEDED` (400) - Order blocked by risk checks
- `RATE_LIMITED` (429) - Too many requests
- `INTERNAL_ERROR` (500) - Server error

## Generating API Docs

API documentation is auto-generated from code using Sphinx:

```bash
cd docs/api
sphinx-build -b html . _build/html
```

See [`sphinx_conf.py`](sphinx_conf.py) for Sphinx configuration.
