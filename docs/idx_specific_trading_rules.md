# IDX (Indonesia Stock Exchange) Trading Rules

Rules and constraints enforced by the Pyhron platform for trading on the Indonesia Stock Exchange. These parameters are configured in `services/risk/idx_constraints.py` and enforced by the pre-trade risk engine.

---

## Trading Hours (WIB, UTC+7)

| Session | Start | End | Notes |
|---------|-------|-----|-------|
| Pre-Opening | 08:45 | 09:00 | Order entry only, no matching. Orders are accumulated and matched at a single equilibrium price at 09:00. |
| Session 1 | 09:00 | 12:00 | Continuous auction. Regular trading. |
| Lunch Break | 12:00 | 13:30 | No trading. Orders may be entered/cancelled. |
| Session 2 | 13:30 | 16:15 | Continuous auction. Regular trading. |
| Pre-Closing | 16:15 | 16:25 | Order entry for closing auction. |
| Post-Trading | 16:25 | 16:30 | Closing price determined. Trade reporting. |

**Friday schedule:** Session 1 ends at 11:30, Session 2 starts at 14:00 (Jumat prayer break).

---

## Lot Size

- **Standard lot size:** 100 shares
- All orders must be in multiples of 100 shares.
- The risk engine validates `quantity % 100 == 0` before submitting any order.
- Odd-lot trading (< 100 shares) is available via the Negotiated Market but is not supported by Pyhron automated strategies.

---

## Settlement Cycle

- **T+2 settlement:** Trades executed on day T are settled on T+2 (two business days later).
- The risk engine tracks unsettled cash via the `RISK_LIMIT_T2_BUYING_POWER` constraint.
- Buying power = Cash balance + (settled receivables on T+1) + (settled receivables on T+2) - outstanding buy commitments.

---

## Auto-Rejection Limits (ARA / ARB)

Price movement limits per session. Orders outside these bands are automatically rejected by the exchange.

| Price Tier (IDR) | Auto-Rejection Limit |
|-------------------|---------------------|
| < 200 | +/- 35% from previous close |
| 200 - 5,000 | +/- 25% from previous close |
| > 5,000 | +/- 20% from previous close |

**Notes:**
- Limits apply to each trading session independently.
- IPO stocks on listing day: +/- 2x the normal limit.
- The risk engine enforces these limits as a pre-trade check to avoid rejected orders.

---

## Tick Sizes

| Price Range (IDR) | Tick Size (IDR) |
|-------------------|----------------|
| < 200 | 1 |
| 200 - 500 | 2 |
| 500 - 2,000 | 5 |
| 2,000 - 5,000 | 10 |
| > 5,000 | 25 |

Limit order prices must be multiples of the applicable tick size. The risk engine rounds prices to valid ticks.

---

## Transaction Costs

| Fee Component | Buy | Sell | Notes |
|---------------|-----|------|-------|
| Broker Commission | 0.15% | 0.15% | Negotiable; 0.15% is the standard rate used in backtesting |
| Transaction Tax | - | 0.10% | Final income tax on equity sales (PPh 4(2)) |
| Exchange Levy | 0.01% | 0.01% | IDX levy, included in broker commission |
| KPEI Clearing Fee | 0.01% | 0.01% | Included in broker commission |
| **Total** | **~0.15%** | **~0.25%** | Sell side includes 0.10% tax |

**Backtesting default parameters:**
```python
IDX_BUY_COST_BPS = 15    # 0.15%
IDX_SELL_COST_BPS = 25   # 0.25% (0.15% commission + 0.10% tax)
IDX_SELL_TAX_BPS = 10    # 0.10% final tax
```

---

## Circuit Breakers (IHSG-based)

Market-wide circuit breakers triggered when the Jakarta Composite Index (IHSG) falls from its previous close:

| Decline Threshold | Action | Duration |
|-------------------|--------|----------|
| -5% | Trading halt | 30 minutes |
| -8% | Trading halt | 1 hour |
| -15% | Market close | Remainder of trading day |

**Pyhron implementation:**
- The risk engine monitors IHSG level via the real-time market data feed.
- When a circuit breaker triggers, `CircuitBreakerState` is published to `pyhron.risk.circuit-breaker`.
- All strategy order generation is paused until the halt period ends or the market closes.
- The `auto_resume_at` field in the protobuf message indicates when trading may resume (for -5% and -8% halts).

---

## Additional Constraints Enforced by Pyhron

| Constraint | Value | Config Key |
|------------|-------|------------|
| Max position size (% of portfolio) | 20% | `RISK_LIMIT_MAX_POSITION_SIZE_PCT` |
| Max sector concentration | 40% | `RISK_LIMIT_MAX_SECTOR_CONCENTRATION` |
| Daily loss limit (% of NAV) | 3% | `RISK_LIMIT_DAILY_LOSS_LIMIT` |
| Max orders per minute | 10 | `RISK_LIMIT_MAX_ORDERS_PER_MINUTE` |
| Max gross exposure | 100% | `RISK_LIMIT_MAX_GROSS_EXPOSURE` |
| Portfolio VaR ceiling (1-day 95%) | 5% of NAV | `RISK_LIMIT_MAX_VAR` |

---

## References

- IDX Rulebook: https://www.idx.co.id/en/regulation/trading-rules/
- OJK Regulation on Securities Trading: POJK 22/2023
- PPh 4(2) Final Tax on Securities: PP 41/1994, amended PP 14/1997
