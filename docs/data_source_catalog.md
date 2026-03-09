# Pyhron Data Source Catalog

All external data sources ingested by the Pyhron platform, organized by domain.

---

## Equity Market Data

| Source | URL | Frequency | Auth Method | Data Type |
|--------|-----|-----------|-------------|-----------|
| EODHD | https://eodhd.com/api | Daily EOD, intraday 5m/1h | API key (header `api_token`) | OHLCV, adjusted prices, splits, dividends for IDX and global equities |

---

## Indonesian Macroeconomic — Bank Indonesia (BI)

| Source | URL | Frequency | Auth Method | Data Type |
|--------|-----|-----------|-------------|-----------|
| BI 7-Day Reverse Repo Rate | https://www.bi.go.id/en/statistik/indikator/bi-rate.aspx | Policy meeting (~monthly) | Public (scrape / SEKI API) | BI reference interest rate (%) |
| JISDOR (Jakarta Interbank Spot Dollar Rate) | https://www.bi.go.id/en/statistik/informasi-kurs/jisdor/default.aspx | Daily (business days) | Public (scrape / SEKI API) | USD/IDR reference exchange rate |
| Money Supply (M2) | https://www.bi.go.id/en/statistik/ekonomi-keuangan/sekda/default.aspx | Monthly | Public (SEKI API) | Broad money supply (IDR trillion) |
| Foreign Exchange Reserves | https://www.bi.go.id/en/statistik/ekonomi-keuangan/sekda/default.aspx | Monthly | Public (SEKI API) | FX reserves (USD billion) |

---

## Indonesian Macroeconomic — BPS Statistics

| Source | URL | Frequency | Auth Method | Data Type |
|--------|-----|-----------|-------------|-----------|
| Consumer Price Index (CPI) | https://www.bps.go.id/en/statistics/table?subject=523 | Monthly | Public API / scrape | CPI index, YoY inflation (%) |
| Gross Domestic Product (GDP) | https://www.bps.go.id/en/statistics/table?subject=526 | Quarterly | Public API / scrape | GDP at current & constant prices, YoY growth (%) |
| Trade Balance | https://www.bps.go.id/en/statistics/table?subject=528 | Monthly | Public API / scrape | Exports, imports, trade balance (USD million) |

---

## Indonesian Fiscal — Kemenkeu (Ministry of Finance)

| Source | URL | Frequency | Auth Method | Data Type |
|--------|-----|-----------|-------------|-----------|
| APBN Realization | https://djpb.kemenkeu.go.id/ | Monthly | Public (scrape) | Budget revenue & expenditure realization (IDR trillion) |

---

## Indonesian Energy — ESDM (Ministry of Energy & Mineral Resources)

| Source | URL | Frequency | Auth Method | Data Type |
|--------|-----|-----------|-------------|-----------|
| HBA (Harga Batubara Acuan) | https://www.minerba.esdm.go.id/harga_acuan | Monthly | Public (scrape) | Coal reference price (USD/ton) |
| ICP (Indonesian Crude Price) | https://migas.esdm.go.id/post/read/harga-minyak-mentah-indonesia-icp | Monthly | Public (scrape) | Crude oil reference price (USD/barrel) |
| Oil & Gas Lifting | https://migas.esdm.go.id/ | Monthly | Public (scrape) | Production volumes (barrels/day, MSCF/day) |

---

## Weather & Climate — BMKG

| Source | URL | Frequency | Auth Method | Data Type |
|--------|-----|-----------|-------------|-----------|
| Rainfall Data | https://dataonline.bmkg.go.id/ | Daily / Monthly | Public (API / scrape) | Rainfall measurements (mm) by station, relevant for plantation and agriculture sectors |

---

## Climate — NOAA

| Source | URL | Frequency | Auth Method | Data Type |
|--------|-----|-----------|-------------|-----------|
| ENSO ONI (Oceanic Nino Index) | https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt | Monthly (3-month running mean) | Public (HTTP GET) | ONI values for El Nino / La Nina classification, impacts CPO yields and coal logistics |

---

## Satellite — NASA FIRMS

| Source | URL | Frequency | Auth Method | Data Type |
|--------|-----|-----------|-------------|-----------|
| Fire Hotspots (VIIRS/MODIS) | https://firms.modaps.eosdis.nasa.gov/api/ | Near real-time (~3hr lag) | API key (free registration) | Active fire detections — lat/lon, confidence, FRP; used for plantation burn monitoring |

---

## Commodities — MPOB (Malaysia Palm Oil Board)

| Source | URL | Frequency | Auth Method | Data Type |
|--------|-----|-----------|-------------|-----------|
| CPO Prices (Bursa Malaysia) | https://bepi.mpob.gov.my/ | Daily | Public (scrape) | Crude Palm Oil spot and futures prices (MYR/ton) |

---

## Commodities — LME (London Metal Exchange)

| Source | URL | Frequency | Auth Method | Data Type |
|--------|-----|-----------|-------------|-----------|
| Nickel | https://www.lme.com/en/metals/non-ferrous/lme-nickel | Daily | Public (scrape) / data vendor | LME nickel cash and 3-month prices (USD/ton) |

---

## Fixed Income — DJPPR (Direktorat Jenderal Pengelolaan Pembiayaan dan Risiko)

| Source | URL | Frequency | Auth Method | Data Type |
|--------|-----|-----------|-------------|-----------|
| SBN Yields (Government Bond Yields) | https://www.djppr.kemenkeu.go.id/sbn/yield-curve | Daily (business days) | Public (scrape) | Yield curve for Indonesian government bonds (SUN/SBSN) across tenors 1M-30Y |

---

## Credit Ratings — PEFINDO

| Source | URL | Frequency | Auth Method | Data Type |
|--------|-----|-----------|-------------|-----------|
| Corporate Credit Ratings | https://www.pefindo.com/index.php/fileman/file?file=710 | Event-driven (on rating action) | Public (scrape / PDF) | Issuer and instrument credit ratings (idAAA to idD), outlook, rating rationale |

---

## Corporate Governance & Bonds — IDX (Indonesia Stock Exchange)

| Source | URL | Frequency | Auth Method | Data Type |
|--------|-----|-----------|-------------|-----------|
| Corporate Bond Listings | https://www.idx.co.id/en/market-data/bonds-sukuk/ | Daily | Public (scrape) | Bond/sukuk instrument details, coupon rates, maturity dates, outstanding amounts |
| Governance Filings | https://www.idx.co.id/en/listed-companies/company-profiles/ | Event-driven | Public (scrape) | Annual reports, GCG assessments, material transactions, related-party disclosures |

---

## Ingestion Architecture Notes

- All ingestion jobs are implemented as async Python workers in `services/data_platform/ingestion/`.
- Ingested data is written to the appropriate TimescaleDB schema and published to the corresponding Kafka topic.
- Each source has a dedicated rate limiter key in Redis (`pyhron:ingestion:rate_limit:{source}`).
- Ingestion status events are published to `pyhron.data.ingestion-status` for monitoring.
- Data quality alerts are published to `pyhron.data.quality-alerts` when validation rules fail.
