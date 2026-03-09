"""Sample commodity price data for testing.

Provides 30 days of CPO (palm oil), coal (HBA), and nickel (LME) prices.
CPO in MYR/tonne, coal in USD/tonne, nickel in USD/tonne.
"""

from __future__ import annotations

from datetime import date, timedelta


def _generate_prices(
    base_date: date,
    days: int,
    start_price: float,
    daily_drift: float,
    volatility: float,
) -> list[dict]:
    """Generate synthetic price series with simple drift + zigzag pattern."""
    prices = []
    price = start_price
    for i in range(days):
        # Simple zigzag to simulate volatility
        direction = 1.0 if i % 3 != 2 else -1.0
        price = price + daily_drift + (volatility * direction)
        prices.append({
            "date": base_date + timedelta(days=i),
            "price": round(price, 2),
        })
    return prices


BASE_DATE = date(2025, 1, 1)

CPO_PRICES_MYR = [
    {"date": BASE_DATE + timedelta(days=i), "commodity": "CPO", "currency": "MYR", "unit": "tonne", "price": p}
    for i, p in enumerate([
        3850.0, 3870.0, 3890.0, 3860.0, 3880.0, 3920.0, 3900.0, 3940.0, 3960.0, 3930.0,
        3950.0, 3980.0, 3970.0, 4000.0, 4020.0, 3990.0, 4010.0, 4050.0, 4030.0, 4060.0,
        4080.0, 4050.0, 4070.0, 4100.0, 4090.0, 4120.0, 4140.0, 4110.0, 4130.0, 4160.0,
    ])
]

COAL_HBA_PRICES_USD = [
    {"date": BASE_DATE + timedelta(days=i), "commodity": "COAL_HBA", "currency": "USD", "unit": "tonne", "price": p}
    for i, p in enumerate([
        115.0, 115.5, 116.0, 115.2, 115.8, 116.5, 116.0, 116.8, 117.2, 116.5,
        117.0, 117.5, 117.0, 118.0, 118.5, 117.8, 118.2, 119.0, 118.5, 119.2,
        119.8, 119.0, 119.5, 120.0, 119.5, 120.2, 120.8, 120.0, 120.5, 121.0,
    ])
]

NICKEL_LME_PRICES_USD = [
    {"date": BASE_DATE + timedelta(days=i), "commodity": "NICKEL_LME", "currency": "USD", "unit": "tonne", "price": p}
    for i, p in enumerate([
        16200.0, 16250.0, 16320.0, 16180.0, 16280.0, 16400.0, 16350.0, 16450.0, 16520.0, 16380.0,
        16480.0, 16550.0, 16500.0, 16620.0, 16700.0, 16580.0, 16650.0, 16780.0, 16720.0, 16800.0,
        16880.0, 16750.0, 16830.0, 16920.0, 16860.0, 16950.0, 17050.0, 16980.0, 17020.0, 17100.0,
    ])
]

ALL_COMMODITY_PRICES = CPO_PRICES_MYR + COAL_HBA_PRICES_USD + NICKEL_LME_PRICES_USD
