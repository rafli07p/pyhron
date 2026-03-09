"""Sample macroeconomic indicator data for testing.

Provides BI rate decisions, CPI data, and GDP growth figures
representative of Indonesian macro conditions.
"""

from __future__ import annotations

from datetime import date

BI_RATE_DECISIONS = [
    {"date": date(2024, 1, 17), "indicator": "bi_7day_reverse_repo_rate", "value": 6.00, "unit": "percent"},
    {"date": date(2024, 2, 21), "indicator": "bi_7day_reverse_repo_rate", "value": 6.00, "unit": "percent"},
    {"date": date(2024, 3, 20), "indicator": "bi_7day_reverse_repo_rate", "value": 6.00, "unit": "percent"},
    {"date": date(2024, 4, 24), "indicator": "bi_7day_reverse_repo_rate", "value": 6.25, "unit": "percent"},
    {"date": date(2024, 5, 22), "indicator": "bi_7day_reverse_repo_rate", "value": 6.25, "unit": "percent"},
    {"date": date(2024, 6, 19), "indicator": "bi_7day_reverse_repo_rate", "value": 6.25, "unit": "percent"},
    {"date": date(2024, 7, 17), "indicator": "bi_7day_reverse_repo_rate", "value": 6.25, "unit": "percent"},
    {"date": date(2024, 8, 21), "indicator": "bi_7day_reverse_repo_rate", "value": 6.25, "unit": "percent"},
    {"date": date(2024, 9, 18), "indicator": "bi_7day_reverse_repo_rate", "value": 6.00, "unit": "percent"},
    {"date": date(2024, 10, 16), "indicator": "bi_7day_reverse_repo_rate", "value": 6.00, "unit": "percent"},
    {"date": date(2024, 11, 20), "indicator": "bi_7day_reverse_repo_rate", "value": 6.00, "unit": "percent"},
    {"date": date(2024, 12, 18), "indicator": "bi_7day_reverse_repo_rate", "value": 6.00, "unit": "percent"},
]

CPI_DATA = [
    {"date": date(2024, 1, 1), "indicator": "cpi_yoy", "value": 2.57, "unit": "percent"},
    {"date": date(2024, 2, 1), "indicator": "cpi_yoy", "value": 2.75, "unit": "percent"},
    {"date": date(2024, 3, 1), "indicator": "cpi_yoy", "value": 3.05, "unit": "percent"},
    {"date": date(2024, 4, 1), "indicator": "cpi_yoy", "value": 3.00, "unit": "percent"},
    {"date": date(2024, 5, 1), "indicator": "cpi_yoy", "value": 2.84, "unit": "percent"},
    {"date": date(2024, 6, 1), "indicator": "cpi_yoy", "value": 2.51, "unit": "percent"},
    {"date": date(2024, 7, 1), "indicator": "cpi_yoy", "value": 2.13, "unit": "percent"},
    {"date": date(2024, 8, 1), "indicator": "cpi_yoy", "value": 2.12, "unit": "percent"},
    {"date": date(2024, 9, 1), "indicator": "cpi_yoy", "value": 1.84, "unit": "percent"},
    {"date": date(2024, 10, 1), "indicator": "cpi_yoy", "value": 1.71, "unit": "percent"},
    {"date": date(2024, 11, 1), "indicator": "cpi_yoy", "value": 1.55, "unit": "percent"},
    {"date": date(2024, 12, 1), "indicator": "cpi_yoy", "value": 1.57, "unit": "percent"},
]

GDP_GROWTH = [
    {"date": date(2024, 3, 31), "indicator": "gdp_growth_yoy", "value": 5.11, "unit": "percent", "quarter": 1},
    {"date": date(2024, 6, 30), "indicator": "gdp_growth_yoy", "value": 5.05, "unit": "percent", "quarter": 2},
    {"date": date(2024, 9, 30), "indicator": "gdp_growth_yoy", "value": 4.95, "unit": "percent", "quarter": 3},
    {"date": date(2024, 12, 31), "indicator": "gdp_growth_yoy", "value": 5.02, "unit": "percent", "quarter": 4},
]

ALL_MACRO_INDICATORS = BI_RATE_DECISIONS + CPI_DATA + GDP_GROWTH
