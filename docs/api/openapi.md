# Enthropy API Documentation

## Overview

The Enthropy REST API provides programmatic access to market data, order management, portfolio tracking, research tools, and administrative functions.

**Base URL:** `http://localhost:8000/api/v1`

Auto-generated OpenAPI/Swagger docs are available at `/docs` when the FastAPI server is running.

## Authentication

All endpoints require a Bearer JWT token in the `Authorization` header:

```
Authorization: Bearer <your-jwt-token>
```

Multi-tenancy is enforced via `tenant_id` extracted from the JWT claims.

## Endpoints

### Market Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/market-data/{symbol}` | Get OHLCV bars for a symbol |
| GET | `/market-data/{symbol}/quotes` | Get latest quotes |
| GET | `/market-data/{symbol}/trades` | Get recent trades |

### Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/orders` | Submit a new order |
| GET | `/orders` | List orders |
| GET | `/orders/{order_id}` | Get order status |
| DELETE | `/orders/{order_id}` | Cancel an order |

### Portfolio

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/portfolio` | Get portfolio summary |
| GET | `/portfolio/positions` | Get open positions |
| GET | `/portfolio/pnl` | Get P&L breakdown |

### Research

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/research/backtest` | Run a backtest |
| GET | `/research/factors` | List available factors |
| GET | `/research/datasets` | List datasets |

### Risk

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/risk/check` | Run pre-trade risk check |
| GET | `/risk/summary` | Get risk summary |

### Admin (RBAC: ADMIN role required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/users` | List users |
| POST | `/admin/users` | Create user |
| PUT | `/admin/users/{id}` | Update user |
| DELETE | `/admin/users/{id}` | Deactivate user |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/ready` | Readiness probe |

## WebSocket

Connect to `ws://localhost:8000/ws/market-data` for real-time market data streaming.

## Rate Limits

- 100 requests/minute for market data
- 50 requests/minute for order submission
- 10 requests/minute for backtest execution
