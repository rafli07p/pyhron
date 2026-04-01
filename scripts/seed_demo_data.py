"""Seed realistic demo IDX data directly into PostgreSQL.

Since yfinance is unavailable (network restrictions), this script generates
realistic synthetic data based on actual IDX market characteristics.
"""

import asyncio
import random
import sys
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from sqlalchemy import text

sys.path.insert(0, ".")
from shared.async_database_session import get_session

# IDX instrument data with realistic metadata
INSTRUMENTS = [
    ("BBCA", "Bank Central Asia Tbk", "Financials", 1200000000000000, True),
    ("BBRI", "Bank Rakyat Indonesia Tbk", "Financials", 850000000000000, True),
    ("BMRI", "Bank Mandiri (Persero) Tbk", "Financials", 560000000000000, True),
    ("TLKM", "Telkom Indonesia Tbk", "Communication Services", 450000000000000, True),
    ("ASII", "Astra International Tbk", "Consumer Discretionary", 280000000000000, True),
    ("UNVR", "Unilever Indonesia Tbk", "Consumer Staples", 220000000000000, True),
    ("BBNI", "Bank Negara Indonesia Tbk", "Financials", 180000000000000, True),
    ("BRIS", "Bank Syariah Indonesia Tbk", "Financials", 85000000000000, True),
    ("INDF", "Indofood Sukses Makmur Tbk", "Consumer Staples", 95000000000000, True),
    ("ICBP", "Indofood CBP Sukses Makmur Tbk", "Consumer Staples", 120000000000000, True),
    ("KLBF", "Kalbe Farma Tbk", "Health Care", 88000000000000, True),
    ("HMSP", "H.M. Sampoerna Tbk", "Consumer Staples", 55000000000000, True),
    ("GGRM", "Gudang Garam Tbk", "Consumer Staples", 45000000000000, True),
    ("ADRO", "Adaro Energy Indonesia Tbk", "Energy", 110000000000000, True),
    ("ITMG", "Indo Tambangraya Megah Tbk", "Energy", 52000000000000, True),
    ("PTBA", "Bukit Asam Tbk", "Energy", 48000000000000, True),
    ("ANTM", "Aneka Tambang Tbk", "Materials", 62000000000000, True),
    ("INCO", "Vale Indonesia Tbk", "Materials", 55000000000000, True),
    ("MDKA", "Merdeka Copper Gold Tbk", "Materials", 42000000000000, True),
    ("EXCL", "XL Axiata Tbk", "Communication Services", 38000000000000, True),
    ("SIDO", "Industri Jamu Dan Farmasi Sido Tbk", "Health Care", 28000000000000, False),
    ("MAPI", "Mitra Adiperkasa Tbk", "Consumer Discretionary", 22000000000000, False),
    ("ACES", "Ace Hardware Indonesia Tbk", "Consumer Discretionary", 18000000000000, True),
    ("CPIN", "Charoen Pokphand Indonesia Tbk", "Consumer Staples", 72000000000000, True),
    ("JPFA", "Japfa Comfeed Indonesia Tbk", "Consumer Staples", 15000000000000, True),
    ("MEDC", "Medco Energi Internasional Tbk", "Energy", 35000000000000, True),
    ("PGAS", "Perusahaan Gas Negara Tbk", "Utilities", 42000000000000, True),
    ("ESSA", "Surya Esa Perkasa Tbk", "Energy", 18000000000000, True),
    ("TOWR", "Sarana Menara Nusantara Tbk", "Communication Services", 68000000000000, True),
    ("TBIG", "Tower Bersama Infrastructure Tbk", "Communication Services", 55000000000000, True),
    ("SMGR", "Semen Indonesia (Persero) Tbk", "Materials", 45000000000000, True),
    ("INKP", "Indah Kiat Pulp & Paper Tbk", "Materials", 58000000000000, True),
    ("BRPT", "Barito Pacific Tbk", "Basic Materials", 38000000000000, True),
    ("AMRT", "Sumber Alfaria Trijaya Tbk", "Consumer Staples", 75000000000000, True),
    ("ERAA", "Erajaya Swasembada Tbk", "Consumer Discretionary", 12000000000000, False),
    ("MNCN", "Media Nusantara Citra Tbk", "Communication Services", 8000000000000, False),
    ("SCMA", "Surya Citra Media Tbk", "Communication Services", 6000000000000, False),
    ("AKRA", "AKR Corporindo Tbk", "Energy", 25000000000000, True),
    ("UNTR", "United Tractors Tbk", "Industrials", 95000000000000, True),
    ("BBTN", "Bank Tabungan Negara Tbk", "Financials", 28000000000000, True),
    ("BSDE", "Bumi Serpong Damai Tbk", "Real Estate", 22000000000000, True),
    ("CTRA", "Ciputra Development Tbk", "Real Estate", 18000000000000, True),
    ("SMRA", "Summarecon Agung Tbk", "Real Estate", 12000000000000, True),
    ("PWON", "Pakuwon Jati Tbk", "Real Estate", 15000000000000, True),
    ("JSMR", "Jasa Marga (Persero) Tbk", "Industrials", 38000000000000, True),
    ("WIKA", "Wijaya Karya (Persero) Tbk", "Industrials", 8000000000000, True),
    ("WSKT", "Waskita Karya (Persero) Tbk", "Industrials", 5000000000000, False),
    ("PTPP", "PP (Persero) Tbk", "Industrials", 6000000000000, False),
    ("TPIA", "Chandra Asri Pacific Tbk", "Materials", 45000000000000, True),
    ("EMTK", "Elang Mahkota Teknologi Tbk", "Communication Services", 32000000000000, True),
]

# Base prices per symbol (approximate real IDX prices in IDR)
BASE_PRICES = {
    "BBCA": 9800,
    "BBRI": 5100,
    "BMRI": 6800,
    "TLKM": 3800,
    "ASII": 5200,
    "UNVR": 4200,
    "BBNI": 5500,
    "BRIS": 2700,
    "INDF": 6800,
    "ICBP": 11500,
    "KLBF": 1650,
    "HMSP": 880,
    "GGRM": 28000,
    "ADRO": 3200,
    "ITMG": 27000,
    "PTBA": 2800,
    "ANTM": 1800,
    "INCO": 4500,
    "MDKA": 2400,
    "EXCL": 2200,
    "SIDO": 750,
    "MAPI": 1850,
    "ACES": 780,
    "CPIN": 5200,
    "JPFA": 1450,
    "MEDC": 1350,
    "PGAS": 1550,
    "ESSA": 850,
    "TOWR": 1100,
    "TBIG": 2150,
    "SMGR": 4200,
    "INKP": 8500,
    "BRPT": 1150,
    "AMRT": 2800,
    "ERAA": 560,
    "MNCN": 780,
    "SCMA": 192,
    "AKRA": 1500,
    "UNTR": 28000,
    "BBTN": 1350,
    "BSDE": 1100,
    "CTRA": 1200,
    "SMRA": 620,
    "PWON": 440,
    "JSMR": 4500,
    "WIKA": 410,
    "WSKT": 350,
    "PTPP": 520,
    "TPIA": 5800,
    "EMTK": 550,
}

# Fundamental ratios (P/E, P/B, ROE%, dividend yield%, debt/equity)
FUNDAMENTALS = {
    "BBCA": (25.3, 5.2, 21.5, 1.8, 0.0),
    "BBRI": (12.8, 2.5, 19.8, 3.2, 0.0),
    "BMRI": (10.5, 1.8, 18.2, 4.5, 0.0),
    "TLKM": (14.2, 3.1, 22.5, 4.8, 0.85),
    "ASII": (8.5, 1.4, 16.8, 5.2, 0.62),
    "UNVR": (35.2, 42.5, 125.3, 2.8, 2.85),
    "BBNI": (7.8, 1.2, 15.5, 5.8, 0.0),
    "BRIS": (18.5, 3.8, 15.2, 1.2, 0.0),
    "INDF": (7.2, 1.3, 18.5, 4.2, 0.95),
    "ICBP": (18.5, 3.8, 21.2, 2.5, 0.45),
    "KLBF": (22.5, 3.2, 14.8, 2.2, 0.18),
    "HMSP": (12.8, 5.8, 45.2, 8.5, 0.12),
    "GGRM": (14.2, 1.8, 12.5, 3.8, 0.22),
    "ADRO": (5.8, 1.2, 22.8, 8.5, 0.35),
    "ITMG": (4.2, 1.5, 35.8, 12.5, 0.28),
    "PTBA": (6.5, 1.8, 28.5, 9.2, 0.15),
    "ANTM": (8.5, 1.2, 14.2, 3.5, 0.35),
    "INCO": (12.5, 1.8, 14.5, 2.8, 0.08),
    "MDKA": (35.2, 3.5, 10.2, 0.0, 0.65),
    "EXCL": (18.5, 2.2, 12.5, 0.8, 1.25),
    "SIDO": (22.5, 5.8, 25.8, 3.2, 0.05),
    "MAPI": (15.2, 3.2, 22.5, 1.5, 0.85),
    "ACES": (18.5, 3.5, 19.2, 2.8, 0.02),
    "CPIN": (14.5, 3.8, 26.5, 2.2, 0.42),
    "JPFA": (8.5, 1.5, 18.2, 3.5, 0.85),
    "MEDC": (5.2, 1.2, 24.5, 2.5, 0.95),
    "PGAS": (8.8, 1.1, 12.8, 5.5, 0.65),
    "ESSA": (12.5, 2.2, 18.5, 0.0, 0.45),
    "TOWR": (28.5, 5.5, 19.5, 1.8, 2.85),
    "TBIG": (32.5, 6.8, 21.2, 1.2, 3.15),
    "SMGR": (15.2, 1.5, 10.2, 3.5, 0.55),
    "INKP": (5.8, 0.8, 14.5, 2.2, 0.45),
    "BRPT": (18.5, 1.2, 6.5, 0.0, 0.85),
    "AMRT": (42.5, 12.5, 28.5, 0.8, 0.65),
    "ERAA": (8.5, 2.2, 26.5, 2.5, 0.35),
    "MNCN": (6.5, 0.8, 12.5, 5.8, 0.25),
    "SCMA": (8.2, 1.5, 18.5, 6.2, 0.12),
    "AKRA": (12.5, 2.5, 20.2, 3.2, 0.75),
    "UNTR": (8.2, 1.5, 18.8, 5.5, 0.55),
    "BBTN": (6.5, 0.8, 12.5, 3.8, 0.0),
    "BSDE": (12.5, 0.8, 6.5, 2.2, 0.45),
    "CTRA": (15.2, 1.2, 8.2, 1.5, 0.35),
    "SMRA": (18.5, 1.5, 8.5, 1.2, 0.65),
    "PWON": (8.5, 0.9, 10.5, 2.5, 0.25),
    "JSMR": (22.5, 2.2, 9.8, 1.2, 1.85),
    "WIKA": (12.5, 0.5, 4.2, 2.8, 1.45),
    "WSKT": (None, 0.3, 2.5, 0.0, 2.85),
    "PTPP": (8.5, 0.4, 4.8, 1.5, 1.65),
    "TPIA": (15.8, 1.8, 11.5, 0.5, 0.55),
    "EMTK": (25.5, 1.2, 4.8, 0.0, 0.15),
}


def generate_ohlcv(symbol: str, base_price: float, start: date, end: date) -> list[dict]:
    """Generate realistic OHLCV data with random walk and mean reversion."""
    random.seed(hash(symbol))
    records = []
    price = base_price * random.uniform(0.6, 0.9)  # Start lower in 2020
    volatility = 0.018 + random.uniform(-0.005, 0.01)

    current = start
    while current <= end:
        # Skip weekends
        if current.weekday() >= 5:
            current += timedelta(days=1)
            continue

        # Random walk with slight upward drift (IDX ~10% annual)
        daily_return = random.gauss(0.0004, volatility)

        # Mean reversion toward base price
        reversion = (base_price - price) / base_price * 0.002
        daily_return += reversion

        price *= 1 + daily_return
        price = max(price, 50)  # Floor at 50 IDR

        if price < 200:
            price = round(price)
        elif price < 500:
            price = round(price / 2) * 2
        elif price < 2000:
            price = round(price / 5) * 5
        elif price < 5000:
            price = round(price / 10) * 10
        else:
            price = round(price / 25) * 25

        intraday_vol = random.uniform(0.005, 0.025)
        high = price * (1 + random.uniform(0, intraday_vol))
        low = price * (1 - random.uniform(0, intraday_vol))
        open_price = price * (1 + random.uniform(-intraday_vol / 2, intraday_vol / 2))

        volume = int(random.gauss(15_000_000, 8_000_000))
        volume = max(volume, 500_000)

        records.append(
            {
                "time": datetime.combine(current, datetime.min.time(), tzinfo=UTC),
                "symbol": symbol,
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(price, 2),
                "volume": volume,
                "adj_close": round(price, 2),
            }
        )
        current += timedelta(days=1)

    return records


async def seed_instruments():
    """Seed/update all instruments."""
    print("=== Seeding Instruments ===")
    async with get_session() as session:
        for symbol, name, sector, mcap, is_lq45 in INSTRUMENTS:
            await session.execute(
                text("""
                    INSERT INTO instruments (id, symbol, company_name, sector, market_cap_idr, is_active)
                    VALUES (:id, :symbol, :name, :sector, :mcap, true)
                    ON CONFLICT (symbol) DO UPDATE SET
                        company_name = :name, sector = :sector, market_cap_idr = :mcap, updated_at = now()
                """),
                {"id": str(uuid4()), "symbol": symbol, "name": name, "sector": sector, "mcap": mcap},
            )
        await session.commit()
    print(f"  {len(INSTRUMENTS)} instruments seeded")


async def seed_index_constituents():
    """Seed LQ45 index constituents."""
    print("\n=== Seeding Index Constituents ===")
    lq45 = [s for s, _, _, _, is_lq45 in INSTRUMENTS if is_lq45]
    async with get_session() as session:
        await session.execute(text("DELETE FROM index_constituents WHERE index_name = 'LQ45'"))
        weight = round(100.0 / len(lq45), 2)
        for symbol in lq45:
            await session.execute(
                text("""
                    INSERT INTO index_constituents (id, index_name, symbol, effective_date, weight_pct)
                    VALUES (:id, 'LQ45', :symbol, '2025-01-01', :weight)
                """),
                {"id": str(uuid4()), "symbol": symbol, "weight": weight},
            )
        await session.commit()
    print(f"  {len(lq45)} LQ45 constituents seeded")


async def seed_ohlcv():
    """Seed OHLCV data for all instruments."""
    start = date(2020, 1, 1)
    end = date(2026, 3, 28)
    print(f"\n=== Seeding OHLCV Data ({start} to {end}) ===")

    total_bars = 0
    async with get_session() as session:
        for i, (symbol, _, _, _, _) in enumerate(INSTRUMENTS):
            base = BASE_PRICES.get(symbol, 1000)
            records = generate_ohlcv(symbol, base, start, end)

            for j in range(0, len(records), 200):
                batch = records[j : j + 200]
                for rec in batch:
                    await session.execute(
                        text("""
                            INSERT INTO ohlcv (time, symbol, exchange, interval, open, high, low, close, volume, adjusted_close)
                            VALUES (:time, :symbol, 'IDX', '1d', :open, :high, :low, :close, :volume, :adj_close)
                            ON CONFLICT DO NOTHING
                        """),
                        rec,
                    )
                await session.commit()

            total_bars += len(records)
            print(f"  [{i+1}/{len(INSTRUMENTS)}] {symbol}: {len(records)} bars")

    print(f"  Total: {total_bars} bars seeded")
    return total_bars


async def seed_computed_ratios():
    """Seed computed ratios for all instruments."""
    print("\n=== Seeding Computed Ratios ===")
    today = date.today()

    async with get_session() as session:
        for symbol, (pe, pb, roe, div_yield, de) in FUNDAMENTALS.items():
            mcap = next((m for s, _, _, m, _ in INSTRUMENTS if s == symbol), 0)
            await session.execute(
                text("""
                    INSERT INTO computed_ratios (id, symbol, date, pe_ratio, pb_ratio, roe_pct, dividend_yield_pct, market_cap_idr, debt_to_equity, computed_at)
                    VALUES (:id, :symbol, :date, :pe, :pb, :roe, :div, :mcap, :de, now())
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": str(uuid4()),
                    "symbol": symbol,
                    "date": today,
                    "pe": pe,
                    "pb": pb,
                    "roe": roe,
                    "div": div_yield,
                    "mcap": mcap,
                    "de": de,
                },
            )
        await session.commit()
    print(f"  {len(FUNDAMENTALS)} ratio records seeded")


async def seed_macro_indicators():
    """Seed macro indicators."""
    print("\n=== Seeding Macro Indicators ===")
    indicators = [
        ("BI_RATE", "BI 7-Day Reverse Repo Rate", 5.75, "%", "2026-03", "Bank Indonesia"),
        ("GDP_GROWTH", "GDP Growth YoY", 5.05, "%", "2025-Q4", "BPS"),
        ("CPI_YOY", "CPI Year-on-Year", 1.65, "%", "2026-02", "BPS"),
        ("USDIDR", "USD/IDR Exchange Rate", 16250.00, "IDR", "2026-03", "Market"),
        ("IHSG", "Jakarta Composite Index", 7245.32, "points", "2026-03", "IDX"),
        ("UNEMPLOYMENT", "Unemployment Rate", 5.32, "%", "2025-Q4", "BPS"),
        ("TRADE_BALANCE", "Trade Balance", 3.56, "USD Bn", "2026-02", "BPS"),
        ("FDI", "Foreign Direct Investment", 12.4, "USD Bn", "2025", "BKPM"),
    ]

    async with get_session() as session:
        for code, name, value, unit, period, source in indicators:
            await session.execute(
                text("""
                    INSERT INTO macro_indicators (id, indicator_code, indicator_name, value, unit, period, source, frequency, reference_date)
                    VALUES (:id, :code, :name, :value, :unit, :period, :source, 'monthly', :ref_date)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": str(uuid4()),
                    "code": code,
                    "name": name,
                    "value": value,
                    "unit": unit,
                    "period": period,
                    "source": source,
                    "ref_date": date.today(),
                },
            )
        await session.commit()
    print(f"  {len(indicators)} macro indicators seeded")


async def seed_commodity_prices():
    """Seed commodity prices."""
    print("\n=== Seeding Commodity Prices ===")
    commodities = [
        ("CPO", "Crude Palm Oil", 4125.00, "MYR", "MT"),
        ("COAL", "Newcastle Coal", 130.50, "USD", "MT"),
        ("NICKEL", "Nickel", 15800.00, "USD", "MT"),
        ("TIN", "Tin", 30500.00, "USD", "MT"),
        ("GOLD", "Gold", 3085.50, "USD", "oz"),
        ("RUBBER", "Rubber RSS3", 1.65, "USD", "kg"),
    ]

    async with get_session() as session:
        for code, name, price, currency, unit in commodities:
            change = round(random.uniform(-2.5, 3.5), 2)
            await session.execute(
                text("""
                    INSERT INTO commodity_prices (id, commodity_code, commodity_name, price, currency, unit, change_pct, price_date, source)
                    VALUES (:id, :code, :name, :price, :currency, :unit, :change, :pdate, 'demo')
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": str(uuid4()),
                    "code": code,
                    "name": name,
                    "price": price,
                    "currency": currency,
                    "unit": unit,
                    "change": change,
                    "pdate": date.today(),
                },
            )
        await session.commit()
    print(f"  {len(commodities)} commodity prices seeded")


async def main():
    print("=" * 60)
    print("Pyhron Demo Data Seeder")
    print("=" * 60)

    await seed_instruments()
    await seed_index_constituents()
    total = await seed_ohlcv()
    await seed_computed_ratios()
    await seed_macro_indicators()
    await seed_commodity_prices()

    print("\n" + "=" * 60)
    print("SEED COMPLETE")
    print(f"  Instruments: {len(INSTRUMENTS)}")
    print(f"  OHLCV bars: {total}")
    print(f"  Ratios: {len(FUNDAMENTALS)}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
