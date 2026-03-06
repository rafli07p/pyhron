# Enthropy Architecture Overview

## System Design

Enthropy is a Bloomberg-style quantitative research and trading terminal built as a Python monorepo with domain-driven design.

```
┌─────────────────────────────────────────────────────────┐
│                      Apps Layer                         │
│  ┌──────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ Terminal  │  │ Research Platform │  │ Admin Console│  │
│  └────┬─────┘  └────────┬─────────┘  └──────┬───────┘  │
│       │                 │                    │          │
├───────┴─────────────────┴────────────────────┴──────────┤
│                    API Gateway                          │
│  ┌────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │ REST (Fast │  │ WebSocket      │  │ Structured   │  │
│  │ API)       │  │ Gateway        │  │ Logging      │  │
│  └────┬───────┘  └────────┬───────┘  └──────────────┘  │
├───────┴────────────────────┴────────────────────────────┤
│                   Services Layer                        │
│  ┌───────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐  │
│  │Market Data│ │Execution │ │Portfolio│ │  Risk    │  │
│  │           │ │          │ │         │ │          │  │
│  └─────┬─────┘ └────┬─────┘ └────┬────┘ └────┬─────┘  │
│        │             │            │           │        │
│  ┌─────┴─────────────┴────────────┴───────────┴─────┐  │
│  │                Research Service                   │  │
│  │  Backtesting │ Factor Engine │ Simulation         │  │
│  └──────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────┤
│                  Data Platform                         │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐            │
│  │Tick Store│ │Historical  │ │Encryption│            │
│  │(Redis)   │ │(PostgreSQL)│ │(Fernet)  │            │
│  └──────────┘ └────────────┘ └──────────┘            │
├────────────────────────────────────────────────────────┤
│                  Shared Layer                          │
│  Schemas │ Contracts │ Utils │ Security (RBAC/Auth)   │
└────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Market Data Ingestion**: Massive/Polygon WebSocket → Normalization → Redis (tick cache) → PostgreSQL (historical)
2. **Order Execution**: Signal → Pre-trade checks → Order Router → Exchange Connector (Alpaca/CCXT) → Fill → Position Update → P&L
3. **Research Pipeline**: Dataset Builder (real API data) → Factor Engine → Backtest Engine → Results

## Key Design Decisions

- **Multi-tenancy**: All data models include `tenant_id` for client isolation
- **Real data only**: No mock data; all integrations use Massive, Alpaca, yfinance, CCXT
- **Encryption**: AES/Fernet for strategy IP protection and compliance exports
- **Circuit breakers**: pybreaker in execution and risk services for fault tolerance
- **Async-first**: asyncio throughout for non-blocking I/O

## External Integrations

| Service | Library | Purpose |
|---------|---------|---------|
| Massive/Polygon | `polygon` | Primary market data (US equities) |
| Alpaca | `alpaca-py` | Order execution (US equities) |
| yfinance | `yfinance` | Fallback data, IDX Indonesia (.JK) |
| CCXT | `ccxt` | Multi-exchange, crypto |

## Migration Path to Microservices

Each `services/` subdirectory is designed as a bounded context that can be extracted into an independent microservice:

1. Extract service into separate repository
2. Replace in-process calls with gRPC/HTTP clients
3. Deploy as independent container with own database
4. Use Kafka for event-driven communication between services

See `infra/kubernetes/` for container orchestration configs.
