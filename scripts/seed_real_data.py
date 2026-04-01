"""Seed real IDX data via yfinance into PostgreSQL.

Usage:
    DATABASE_URL=... poetry run python scripts/seed_real_data.py

Steps:
    1. Update instrument metadata (sector, market_cap) from yfinance
    2. Backfill OHLCV data (2020-01-01 to today)
    3. Seed computed ratios from yfinance info
    4. Seed macro indicators (IHSG, USD/IDR, hardcoded BI rate etc.)
    5. Seed commodity prices
"""

import asyncio
import sys
from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import text

# Add project root to path
sys.path.insert(0, ".")

from data_platform.adapters.yfinance_adapter import YFinanceAdapter
from shared.async_database_session import get_session

CORE_SYMBOLS = [
    "BBCA",
    "BBRI",
    "BMRI",
    "TLKM",
    "ASII",
    "UNVR",
    "BBNI",
    "BRIS",
    "INDF",
    "ICBP",
    "KLBF",
    "HMSP",
    "GGRM",
    "ADRO",
    "ITMG",
    "PTBA",
    "ANTM",
    "INCO",
    "MDKA",
    "EXCL",
]

EXTRA_SYMBOLS = [
    "SIDO",
    "MAPI",
    "ACES",
    "CPIN",
    "JPFA",
    "MEDC",
    "PGAS",
    "ESSA",
    "TOWR",
    "TBIG",
    "SMGR",
    "INKP",
    "BRPT",
    "AMRT",
    "ERAA",
    "MNCN",
    "SCMA",
    "AKRA",
    "UNTR",
    "BBTN",
    "BSDE",
    "CTRA",
    "SMRA",
    "PWON",
    "JSMR",
    "WIKA",
    "WSKT",
    "PTPP",
    "TPIA",
    "EMTK",
]

ALL_SYMBOLS = CORE_SYMBOLS + EXTRA_SYMBOLS

LQ45_SYMBOLS = {
    "BBCA",
    "BBRI",
    "BMRI",
    "TLKM",
    "ASII",
    "UNVR",
    "BBNI",
    "INDF",
    "ICBP",
    "KLBF",
    "HMSP",
    "GGRM",
    "ADRO",
    "ITMG",
    "PTBA",
    "ANTM",
    "INCO",
    "MDKA",
    "EXCL",
    "CPIN",
    "PGAS",
    "TBIG",
    "SMGR",
    "INKP",
    "BRPT",
    "AMRT",
    "AKRA",
    "UNTR",
    "BBTN",
    "BSDE",
    "CTRA",
    "JSMR",
    "TPIA",
    "EMTK",
    "TOWR",
    "MEDC",
    "MAPI",
    "ACES",
    "SIDO",
    "JPFA",
    "ESSA",
    "ERAA",
    "PWON",
    "SMRA",
    "BRIS",
}


async def update_instrument_metadata():
    """Update sector, market_cap from yfinance for all instruments."""
    adapter = YFinanceAdapter()
    print("\n=== Updating Instrument Metadata ===")

    async with get_session() as session:
        for i, symbol in enumerate(ALL_SYMBOLS):
            try:
                info = await adapter.get_info(symbol)
                sector = info.get("sector", info.get("industry", ""))
                market_cap = info.get("marketCap", 0)
                name = info.get("longName", info.get("shortName", ""))

                if sector or market_cap:
                    await session.execute(
                        text("""
                            UPDATE instruments
                            SET sector = COALESCE(:sector, sector),
                                market_cap_idr = COALESCE(:mcap, market_cap_idr),
                                company_name = CASE WHEN :name != '' THEN :name ELSE company_name END,
                                updated_at = now()
                            WHERE symbol = :symbol
                        """),
                        {"sector": sector or None, "mcap": market_cap or None, "name": name, "symbol": symbol},
                    )
                    await session.commit()
                    print(f"  [{i+1}/{len(ALL_SYMBOLS)}] {symbol}: sector={sector}, mcap={market_cap}")
                else:
                    print(f"  [{i+1}/{len(ALL_SYMBOLS)}] {symbol}: no info available")
            except Exception as e:
                print(f"  [{i+1}/{len(ALL_SYMBOLS)}] {symbol}: ERROR - {e}")
                await session.rollback()

            # Rate limit: yfinance is lenient but don't hammer
            if (i + 1) % 5 == 0:
                await asyncio.sleep(1)


async def ensure_instruments_exist():
    """Make sure all symbols exist in the instruments table."""
    async with get_session() as session:
        result = await session.execute(text("SELECT symbol FROM instruments"))
        existing = {row[0] for row in result}

        for symbol in ALL_SYMBOLS:
            if symbol not in existing:
                await session.execute(
                    text("""
                        INSERT INTO instruments (id, symbol, company_name, is_active)
                        VALUES (:id, :symbol, :name, true)
                        ON CONFLICT (symbol) DO NOTHING
                    """),
                    {"id": str(uuid4()), "symbol": symbol, "name": f"{symbol} Tbk"},
                )
        await session.commit()
        print(f"Ensured {len(ALL_SYMBOLS)} instruments exist")


async def backfill_ohlcv(symbols: list[str], date_from: date, date_to: date, workers: int = 3):
    """Backfill OHLCV data for symbols using yfinance."""
    adapter = YFinanceAdapter()
    semaphore = asyncio.Semaphore(workers)
    print(f"\n=== Backfilling OHLCV: {len(symbols)} symbols, {date_from} to {date_to} ===")

    async def _backfill_one(symbol: str) -> tuple[str, int, str]:
        async with semaphore:
            try:
                records = await adapter.get_eod_data(symbol, date_from, date_to)
                if not records:
                    return symbol, 0, "no_data"

                async with get_session() as session:
                    batch_size = 500
                    for i in range(0, len(records), batch_size):
                        batch = records[i : i + batch_size]
                        for rec in batch:
                            await session.execute(
                                text("""
                                    INSERT INTO ohlcv (time, symbol, exchange, interval, open, high, low, close, volume, adjusted_close)
                                    VALUES (:time, :symbol, 'IDX', '1d', :open, :high, :low, :close, :volume, :adj_close)
                                    ON CONFLICT DO NOTHING
                                """),
                                {
                                    "time": datetime.combine(rec.date, datetime.min.time(), tzinfo=UTC),
                                    "symbol": rec.symbol,
                                    "open": float(rec.open),
                                    "high": float(rec.high),
                                    "low": float(rec.low),
                                    "close": float(rec.close),
                                    "volume": rec.volume,
                                    "adj_close": float(rec.adjusted_close),
                                },
                            )
                        await session.commit()

                return symbol, len(records), "ok"
            except Exception as e:
                return symbol, 0, str(e)[:60]

    tasks = [_backfill_one(s) for s in symbols]
    results = await asyncio.gather(*tasks)

    total = 0
    for symbol, count, status in sorted(results):
        total += count
        print(f"  {symbol:<8} {count:>6} bars  {status}")
    print(f"  Total: {total} bars inserted")
    return total


async def seed_computed_ratios():
    """Seed computed ratios (P/E, P/B, ROE, etc.) from yfinance info."""
    adapter = YFinanceAdapter()
    print("\n=== Seeding Computed Ratios ===")
    today = date.today()
    count = 0

    for i, symbol in enumerate(ALL_SYMBOLS):
        try:
            info = await adapter.get_info(symbol)
            pe = info.get("trailingPE") or info.get("forwardPE")
            pb = info.get("priceToBook")
            roe = info.get("returnOnEquity")
            eps = info.get("trailingEps")
            div_yield = info.get("dividendYield")
            mcap = info.get("marketCap")
            de = info.get("debtToEquity")

            async with get_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO computed_ratios (id, symbol, date, pe_ratio, pb_ratio, roe_pct, eps, dividend_yield_pct, market_cap_idr, debt_to_equity, computed_at)
                        VALUES (:id, :symbol, :date, :pe, :pb, :roe, :eps, :div, :mcap, :de, now())
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "id": str(uuid4()),
                        "symbol": symbol,
                        "date": today,
                        "pe": pe,
                        "pb": pb,
                        "roe": float(roe) * 100 if roe else None,
                        "eps": eps,
                        "div": float(div_yield) * 100 if div_yield else None,
                        "mcap": mcap,
                        "de": float(de) / 100 if de else None,
                    },
                )
                await session.commit()
                count += 1
                print(f"  [{i+1}/{len(ALL_SYMBOLS)}] {symbol}: PE={pe}, PB={pb}, ROE={roe}")
        except Exception as e:
            print(f"  [{i+1}/{len(ALL_SYMBOLS)}] {symbol}: ERROR - {e}")

        if (i + 1) % 5 == 0:
            await asyncio.sleep(1)

    print(f"  Seeded {count} ratio records")


async def seed_macro_indicators():
    """Seed macro indicators: IHSG, USD/IDR from yfinance + hardcoded BI rate, GDP, CPI."""
    print("\n=== Seeding Macro Indicators ===")

    indicators = [
        {
            "code": "BI_RATE",
            "name": "BI 7-Day Reverse Repo Rate",
            "value": 5.75,
            "unit": "%",
            "period": "2026-03",
            "source": "Bank Indonesia",
        },
        {
            "code": "GDP_GROWTH",
            "name": "GDP Growth YoY",
            "value": 5.05,
            "unit": "%",
            "period": "2025-Q4",
            "source": "BPS",
        },
        {
            "code": "CPI_YOY",
            "name": "CPI Year-on-Year",
            "value": 1.65,
            "unit": "%",
            "period": "2026-02",
            "source": "BPS",
        },
    ]

    # Fetch USD/IDR from yfinance
    try:
        import yfinance as yf

        ticker = yf.Ticker("USDIDR=X")
        hist = ticker.history(period="1d")
        if not hist.empty:
            idr_rate = float(hist["Close"].iloc[-1])
            indicators.append(
                {
                    "code": "USDIDR",
                    "name": "USD/IDR Exchange Rate",
                    "value": round(idr_rate, 2),
                    "unit": "IDR",
                    "period": date.today().isoformat()[:7],
                    "source": "yfinance",
                }
            )
    except Exception as e:
        print(f"  Could not fetch USD/IDR: {e}")
        indicators.append(
            {
                "code": "USDIDR",
                "name": "USD/IDR Exchange Rate",
                "value": 16250.0,
                "unit": "IDR",
                "period": "2026-03",
                "source": "manual",
            }
        )

    # Fetch IHSG
    try:
        import yfinance as yf

        ticker = yf.Ticker("^JKSE")
        hist = ticker.history(period="5d")
        if not hist.empty:
            last = hist.iloc[-1]
            indicators.append(
                {
                    "code": "IHSG",
                    "name": "Jakarta Composite Index",
                    "value": round(float(last["Close"]), 2),
                    "unit": "points",
                    "period": date.today().isoformat()[:7],
                    "source": "yfinance",
                }
            )
    except Exception as e:
        print(f"  Could not fetch IHSG: {e}")

    async with get_session() as session:
        for ind in indicators:
            await session.execute(
                text("""
                    INSERT INTO macro_indicators (id, indicator_code, indicator_name, value, unit, period, source, frequency, reference_date, created_at)
                    VALUES (:id, :code, :name, :value, :unit, :period, :source, 'monthly', :ref_date, now())
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": str(uuid4()),
                    "code": ind["code"],
                    "name": ind["name"],
                    "value": ind["value"],
                    "unit": ind["unit"],
                    "period": ind["period"],
                    "source": ind["source"],
                    "ref_date": date.today(),
                },
            )
            print(f"  {ind['code']}: {ind['value']} {ind['unit']}")
        await session.commit()
    print(f"  Seeded {len(indicators)} macro indicators")


async def seed_commodity_prices():
    """Seed commodity prices from yfinance where available, hardcoded otherwise."""
    print("\n=== Seeding Commodity Prices ===")

    commodities = [
        {"code": "CPO", "name": "Crude Palm Oil", "ticker": "FCPO=F", "currency": "MYR", "unit": "MT"},
        {"code": "COAL", "name": "Newcastle Coal", "ticker": None, "currency": "USD", "unit": "MT", "hardcoded": 130.0},
        {"code": "NICKEL", "name": "Nickel", "ticker": None, "currency": "USD", "unit": "MT", "hardcoded": 15800.0},
        {"code": "TIN", "name": "Tin", "ticker": None, "currency": "USD", "unit": "MT", "hardcoded": 30500.0},
        {"code": "GOLD", "name": "Gold", "ticker": "GC=F", "currency": "USD", "unit": "oz"},
        {"code": "RUBBER", "name": "Rubber", "ticker": None, "currency": "USD", "unit": "kg", "hardcoded": 1.65},
    ]

    for comm in commodities:
        price = comm.get("hardcoded")
        change_pct = 0.0

        if comm.get("ticker"):
            try:
                import yfinance as yf

                ticker = yf.Ticker(comm["ticker"])
                hist = ticker.history(period="5d")
                if not hist.empty:
                    price = round(float(hist["Close"].iloc[-1]), 2)
                    if len(hist) >= 2:
                        prev = float(hist["Close"].iloc[-2])
                        change_pct = round((price - prev) / prev * 100, 2) if prev else 0
            except Exception as e:
                print(f"  {comm['code']}: yfinance failed ({e}), using hardcoded")
                price = price or 0

        if price:
            async with get_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO commodity_prices (id, commodity_code, commodity_name, price, currency, unit, change_pct, price_date, source)
                        VALUES (:id, :code, :name, :price, :currency, :unit, :change_pct, :price_date, :source)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "id": str(uuid4()),
                        "code": comm["code"],
                        "name": comm["name"],
                        "price": price,
                        "currency": comm["currency"],
                        "unit": comm["unit"],
                        "change_pct": change_pct,
                        "price_date": date.today(),
                        "source": "yfinance" if comm.get("ticker") else "manual",
                    },
                )
                await session.commit()
            print(f"  {comm['code']}: {price} {comm['currency']}/{comm['unit']}")

    print("  Commodity prices seeded")


async def seed_index_constituents():
    """Seed LQ45 index constituents."""
    print("\n=== Seeding Index Constituents ===")

    async with get_session() as session:
        weight = round(100.0 / len(LQ45_SYMBOLS), 2)
        for symbol in LQ45_SYMBOLS:
            await session.execute(
                text("""
                    INSERT INTO index_constituents (id, index_name, symbol, effective_date, weight_pct, created_at)
                    VALUES (:id, 'LQ45', :symbol, '2025-01-01', :weight, now())
                    ON CONFLICT DO NOTHING
                """),
                {"id": str(uuid4()), "symbol": symbol, "weight": weight},
            )
        await session.commit()
    print(f"  Seeded {len(LQ45_SYMBOLS)} LQ45 constituents")


async def main():
    print("=" * 60)
    print("Pyhron Data Seeder \u2014 yfinance")
    print("=" * 60)

    # Step 0: Ensure all instruments exist
    await ensure_instruments_exist()

    # Step 1: Seed index constituents
    await seed_index_constituents()

    # Step 2: Update instrument metadata from yfinance
    await update_instrument_metadata()

    # Step 3: Backfill OHLCV \u2014 core symbols first (5 years)
    date_from = date(2020, 1, 1)
    date_to = date.today()
    total_core = await backfill_ohlcv(CORE_SYMBOLS, date_from, date_to, workers=3)

    # Step 4: Backfill OHLCV \u2014 extra symbols
    total_extra = await backfill_ohlcv(EXTRA_SYMBOLS, date_from, date_to, workers=3)

    # Step 5: Seed computed ratios
    await seed_computed_ratios()

    # Step 6: Seed macro indicators
    await seed_macro_indicators()

    # Step 7: Seed commodity prices
    await seed_commodity_prices()

    # Summary
    print("\n" + "=" * 60)
    print("SEED COMPLETE")
    print(f"  OHLCV: {total_core + total_extra} total bars")
    print(f"  Instruments: {len(ALL_SYMBOLS)}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
