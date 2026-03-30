/**
 * MDX content for research articles.
 * In production, these would be .mdx files on disk or in a CMS.
 * For now, raw MDX strings keyed by slug.
 */
export const articleContent: Record<string, string> = {
  'fama-french-five-factor-ihsg': `
## Introduction

The Fama-French five-factor model decomposes equity returns into market risk (MKT), size (SMB), value (HML), profitability (RMW), and investment (CMA) factors. While extensively studied in developed markets, application to emerging markets like Indonesia's IDX remains limited.

This study applies the five-factor framework to 50+ IDX stocks from 2015-2025, constructing long-short factor portfolios using IDX-specific adjustments for T+2 settlement and 100-share lot sizes.

## Data & Methodology

We use daily return data for all LQ45 constituents plus additional liquid stocks, sourced from Bloomberg and IDX's official feed. Factor portfolio construction follows the standard 2x3 sort methodology:

- **SMB (Size):** Market cap median breakpoint, independent 30/70 sort on each value metric
- **HML (Value):** Book-to-market ratio, annual reconstitution in June
- **RMW (Profitability):** Operating profitability (revenue - COGS - SGA - interest) / book equity
- **CMA (Investment):** Total asset growth, lower investment = conservative
- **MKT:** Value-weighted market return minus 1-month SBI rate

| Factor | Ann. Return | Ann. Vol | Sharpe | Max DD |
|--------|------------|----------|--------|--------|
| MKT    | 8.2%       | 18.5%    | 0.44   | -33.2% |
| SMB    | 3.1%       | 12.3%    | 0.25   | -18.7% |
| HML    | 5.8%       | 11.7%    | 0.50   | -15.4% |
| RMW    | 4.2%       | 9.8%     | 0.43   | -12.1% |
| CMA    | 2.9%       | 8.4%     | 0.35   | -10.8% |

## Results

Our findings reveal several notable patterns in IDX factor returns:

1. **Value premium persists:** HML delivers the highest risk-adjusted return among non-market factors, with a Sharpe ratio of 0.50. This is consistent with the well-documented value effect in Asian emerging markets.

2. **Profitability matters:** RMW shows strong performance, suggesting that quality screening adds value in a market where corporate governance varies significantly.

3. **Size premium is modest:** SMB underperforms relative to developed market benchmarks, potentially due to liquidity constraints in small-cap IDX stocks.

> The momentum factor (not included in the original FF5 model) delivers the highest risk-adjusted returns with a Sharpe of 0.82, suggesting it should be considered alongside the standard five factors for IDX allocation.

## Factor Correlations

Cross-factor correlations are generally low, supporting multi-factor portfolio construction:

- HML-RMW correlation: -0.12 (value and quality are complementary)
- SMB-CMA correlation: 0.23 (mild positive relationship)
- MKT correlation with all factors: below 0.30

## Conclusion

Factor investing in IDX offers meaningful diversification benefits. The persistence of value and profitability premia, combined with low cross-factor correlations, supports systematic multi-factor strategies. Practitioners should account for IDX-specific constraints (T+2 settlement, 100-share lots, price tick bands) when implementing factor portfolios.
`,

  'pairs-trading-banking-cointegration': `
## Abstract

We examine cointegration relationships among the four largest Indonesian bank stocks (BBCA, BBRI, BMRI, BBNI) using the Johansen procedure. Statistically significant cointegrating vectors are identified for BBCA-BBRI and BMRI-BBNI pairs, yielding mean-reversion trading strategies with Sharpe ratios above 1.5.

## Methodology

### Johansen Cointegration Test

The Johansen procedure tests for cointegrating relationships in a VAR framework. For each pair, we estimate:

\`\`\`
Δyₜ = Πyₜ₋₁ + Σ Γᵢ Δyₜ₋ᵢ + εₜ
\`\`\`

where Π = αβ', with β being the cointegrating vector and α the adjustment speeds.

We use a rolling 252-day window to estimate cointegrating vectors and generate Z-scores for trading signals.

### Trading Rules

- **Entry:** Z-score crosses ±2.0 standard deviations
- **Exit:** Z-score crosses 0 (mean reversion)
- **Stop-loss:** Z-score reaches ±3.5 standard deviations
- **Position sizing:** Equal notional allocation, adjusted for lot sizes

## Results

### BBCA-BBRI Pair

| Metric | Value |
|--------|-------|
| Johansen Trace Stat | 24.7 (p < 0.01) |
| Half-life of mean reversion | 8.3 days |
| Annual return | 18.4% |
| Sharpe ratio | 1.72 |
| Win rate | 68.2% |
| Max drawdown | -6.8% |

### BMRI-BBNI Pair

| Metric | Value |
|--------|-------|
| Johansen Trace Stat | 19.2 (p < 0.05) |
| Half-life of mean reversion | 12.1 days |
| Annual return | 14.1% |
| Sharpe ratio | 1.53 |
| Win rate | 63.7% |
| Max drawdown | -8.2% |

## Risk Considerations

- **Regime changes:** BI rate decisions can temporarily break cointegration. We recommend pausing signals during rate announcement weeks.
- **Transaction costs:** IDX brokerage fees (0.15% buy, 0.25% sell) and lot-size rounding reduce realized returns by approximately 2.5% annually.
- **Liquidity:** Both pairs trade with sufficient depth for positions up to Rp 5B notional.

## Conclusion

Banking sector pairs trading on IDX offers attractive risk-adjusted returns. The strong fundamental linkages between these institutions (shared regulatory environment, correlated loan books, similar macro sensitivity) provide an economic rationale for the statistical cointegration observed.
`,

  'cpo-price-transmission-granger': `
## Introduction

Crude Palm Oil (CPO) is Indonesia's largest commodity export, and plantation stocks (AALI, LSIP, SIMP, SGRO) represent a significant portion of IDX market capitalization. We investigate the lead-lag relationship between CPO futures prices and plantation equity returns using Granger causality tests.

## Data

- **CPO Futures:** Malaysian Derivatives Exchange (MDEX) front-month CPO futures, daily close, 2018-2025
- **Plantation Stocks:** AALI, LSIP, SIMP, SGRO daily adjusted close prices
- **Control Variables:** USD/IDR exchange rate, IHSG returns

## Granger Causality Results

Using optimal lag selection (AIC criterion), we find:

| Direction | Lags | F-statistic | p-value |
|-----------|------|-------------|---------|
| CPO → AALI | 2 | 8.73 | 0.0002 |
| CPO → LSIP | 3 | 6.41 | 0.0008 |
| CPO → SIMP | 2 | 4.92 | 0.0074 |
| AALI → CPO | 2 | 1.23 | 0.2934 |

CPO prices Granger-cause plantation stock returns at the 1% significance level with a 2-3 day lag. The reverse causation is not significant, confirming a unidirectional information flow.

## Trading Implications

A simple strategy that buys (sells) plantation stocks following a 2% CPO price increase (decrease) generates:

- **Annual alpha:** 6.8% over buy-and-hold plantation basket
- **Information ratio:** 0.92
- **Signal frequency:** ~3.2 signals per month

## Conclusion

CPO futures provide a leading indicator for plantation stock returns with a 2-3 day lag. This price transmission channel can be exploited through systematic trading strategies, though practitioners should account for FX effects (CPO is MYR-denominated) and corporate-specific factors.
`,

  'momentum-factor-index-lq45': `
## Overview

We construct a momentum factor index for IDX LQ45 constituents using a 12-1 month formation period (12 months of returns excluding the most recent month to avoid short-term reversal). The index is rebalanced monthly, holding the top decile (long) and bottom decile (short) of LQ45 by trailing momentum.

## Construction Methodology

1. **Universe:** LQ45 constituents as of each rebalance date
2. **Signal:** 12-month cumulative return, skipping the most recent month
3. **Portfolio:** Long top 5 / Short bottom 5, equal-weighted
4. **Rebalance:** Monthly, on the first trading day
5. **Transaction costs:** 0.15% buy + 0.25% sell (IDX standard)

## Performance Summary

| Metric | Momentum Index | LQ45 Equal-Weight |
|--------|---------------|-------------------|
| Ann. Return | 14.8% | 10.6% |
| Ann. Volatility | 16.2% | 17.8% |
| Sharpe Ratio | 0.91 | 0.60 |
| Max Drawdown | -18.3% | -28.7% |
| Annual Alpha | +4.2% | — |

## Momentum Crashes

Momentum strategies are vulnerable to sharp reversals ("momentum crashes"). In our sample, the worst month was March 2020 (-14.2%), coinciding with the COVID-19 selloff. Incorporating a volatility-scaling overlay (reducing position size when trailing 1-month realized vol exceeds 2x its 12-month average) reduces max drawdown to -12.1% with minimal impact on returns.

## Conclusion

A 12-1 month momentum strategy on LQ45 delivers significant alpha after transaction costs. The strategy benefits from IDX's relatively low institutional participation, which slows information incorporation. Volatility-scaling provides effective crash protection.
`,

  'bi-rate-sector-rotation': `
## Introduction

Bank Indonesia (BI) rate decisions are among the most impactful macro events for IDX. This event study analyzes sector-level returns around BI rate announcements from 2018-2025, encompassing 48 rate decisions (18 cuts, 12 hikes, 18 holds).

## Methodology

We compute cumulative abnormal returns (CARs) for IDX sector indices over event windows of [-5, +10] trading days around each BI announcement. Abnormal returns are calculated relative to a market model estimated over [-60, -6] days.

## Key Findings

### Rate Cuts (18 events)

| Sector | CAR [-1,+5] | t-statistic |
|--------|------------|-------------|
| Property | +3.2% | 3.41** |
| Consumer | +2.1% | 2.87** |
| Infrastructure | +1.8% | 2.14* |
| Banking | -1.8% | -2.53* |
| Mining | +0.3% | 0.42 |

### Rate Hikes (12 events)

| Sector | CAR [-1,+5] | t-statistic |
|--------|------------|-------------|
| Banking | +2.4% | 2.78** |
| Mining | +1.1% | 1.34 |
| Property | -2.7% | -3.12** |
| Consumer | -1.5% | -1.98* |

## Trading Strategy

A sector rotation strategy that overweights rate-sensitive sectors based on BI rate expectations generates an information ratio of 0.74. Pre-positioning 3 days before announcements (when forward rate agreements signal the likely decision) improves performance.

## Conclusion

BI rate decisions create predictable sector rotation patterns. Rate cuts shift capital from banking to property and consumer sectors within 5 trading days. These patterns are economically intuitive and statistically significant, supporting systematic sector allocation around policy events.
`,

  'algorithmic-trading-idx-microstructure': `
## Introduction

Algorithmic trading on the Indonesia Stock Exchange (IDX) presents unique challenges compared to developed markets. This guide covers the essential microstructure details that every algo trader must understand before deploying strategies on IDX.

## Settlement: T+2

IDX operates on a T+2 settlement cycle. This means:

- **Cash settlement** occurs 2 business days after trade execution
- **Short selling** is restricted (no direct short selling for retail investors)
- **Buying power** is affected by unsettled trades
- **Margin requirements** vary by broker (typically 50-80% for regular accounts)

## Lot Sizes

All IDX equities trade in lots of 100 shares. This has significant implications:

- **Minimum position size:** 100 shares × stock price
- **Position sizing:** Must round to nearest 100 shares
- **Odd lots:** Can only be sold (not bought) in the odd-lot market with limited liquidity
- **Rebalancing precision:** Factor strategies may have significant rounding error for smaller portfolios

\`\`\`python
def round_to_lot(shares: float, lot_size: int = 100) -> int:
    """Round share count to nearest lot."""
    return max(lot_size, round(shares / lot_size) * lot_size)
\`\`\`

## Price Tick Sizes

IDX uses variable tick sizes based on price bands:

| Price Range | Tick Size |
|------------|-----------|
| < Rp 200 | Rp 1 |
| Rp 200 - 500 | Rp 2 |
| Rp 500 - 2,000 | Rp 5 |
| Rp 2,000 - 5,000 | Rp 10 |
| > Rp 5,000 | Rp 25 |

## Trading Sessions

- **Pre-opening:** 08:45 - 09:00 WIB (call auction)
- **Session 1:** 09:00 - 11:30 WIB
- **Session 2:** 13:30 - 14:50 WIB (15:00 on Fridays)
- **Pre-closing:** 14:50 - 15:00 WIB (call auction)

## Auto Rejection Limits

IDX enforces daily price limits (auto rejection):

- **Stocks < Rp 200:** ±35%
- **Stocks Rp 200 - 5,000:** ±25%
- **Stocks > Rp 5,000:** ±20%

## Conclusion

Successful algorithmic trading on IDX requires careful handling of lot sizes, tick sizes, settlement cycles, and session timing. The Pyhron platform handles all these constraints natively, allowing strategy developers to focus on signal generation rather than execution mechanics.
`,

  'idx-commentary-march-2026': `
## Market Overview

IHSG gained 2.8% in March 2026, closing at 7,842.15. The rally was driven by strong banking sector performance (+4.1%) and mining sector gains (+3.5%) on the back of elevated commodity prices.

## Sector Performance

| Sector | Monthly Return | YTD Return |
|--------|---------------|------------|
| Banking | +4.1% | +8.3% |
| Mining | +3.5% | +12.1% |
| Consumer | +1.8% | +3.2% |
| Property | +2.2% | +5.7% |
| Telecom | +0.9% | +1.4% |
| Infrastructure | +1.5% | +4.8% |

## Key Highlights

- **Foreign flows:** Net buying of Rp 8.2 trillion, the highest monthly inflow since October 2025. Banking stocks accounted for 62% of foreign purchases.
- **BI Rate:** Held steady at 5.75%, in line with consensus. Forward guidance remains neutral.
- **Commodity tailwinds:** Coal prices averaged USD 142/ton (+8% MoM), supporting ADRO, PTBA, and ITMG. CPO held above MYR 4,100/ton.
- **Rupiah:** Appreciated 0.5% to Rp 15,380/USD, supported by trade surplus and foreign equity inflows.

## Factor Performance (March 2026)

| Factor | Return |
|--------|--------|
| Market (IHSG) | +2.8% |
| Value (HML) | +1.2% |
| Momentum | +3.1% |
| Quality (RMW) | +0.8% |
| Size (SMB) | -0.3% |

Momentum continued to outperform, driven by the persistence of banking and mining trends. Small-cap stocks lagged as foreign flows concentrated in large-cap names.

## Outlook

We maintain a constructive outlook for Q2 2026. Key catalysts include potential BI rate cut in May (if Fed signals are dovish), continued commodity strength, and upcoming Q1 earnings season. Key risks: global recession fears, CNY depreciation pressure, and potential CPO export levy adjustments.
`,
};
