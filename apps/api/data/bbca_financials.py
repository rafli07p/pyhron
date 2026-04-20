"""BBCA 5-year financial data seeded from Annual Report 2025.

Source: PT Bank Central Asia Tbk — Annual Report 2025 (Audited, Consolidated).
All monetary values in Billion IDR unless otherwise stated.
"""

from __future__ import annotations

BBCA_FINANCIAL_POSITION = [
    {
        "year": 2025, "period": "FY2025",
        "total_assets": 1_586_829, "total_earning_assets": 1_479_307,
        "total_loans": 992_901, "total_liabilities": 1_305_141,
        "third_party_funds": 1_249_044, "casa": 1_045_239,
        "time_deposits": 203_805, "total_equity": 281_688,
    },
    {
        "year": 2024, "period": "FY2024",
        "total_assets": 1_449_301, "total_earning_assets": 1_354_435,
        "total_loans": 921_878, "total_liabilities": 1_186_467,
        "third_party_funds": 1_133_612, "casa": 923_977,
        "time_deposits": 209_635, "total_equity": 262_835,
    },
    {
        "year": 2023, "period": "FY2023",
        "total_assets": 1_408_107, "total_earning_assets": 1_266_223,
        "total_loans": 810_392, "total_liabilities": 1_165_570,
        "third_party_funds": 1_101_673, "casa": 884_641,
        "time_deposits": 217_032, "total_equity": 242_538,
    },
    {
        "year": 2022, "period": "FY2022",
        "total_assets": 1_314_732, "total_earning_assets": 1_173_144,
        "total_loans": 711_262, "total_liabilities": 1_093_550,
        "third_party_funds": 1_039_718, "casa": 847_938,
        "time_deposits": 191_780, "total_equity": 221_182,
    },
    {
        "year": 2021, "period": "FY2021",
        "total_assets": 1_228_345, "total_earning_assets": 1_125_418,
        "total_loans": 636_987, "total_liabilities": 1_025_496,
        "third_party_funds": 975_949, "casa": 767_012,
        "time_deposits": 208_937, "total_equity": 202_849,
    },
]

BBCA_INCOME = [
    {
        "year": 2025, "period": "FY2025",
        "operating_income": 112_006, "net_interest_income": 85_548,
        "operating_expenses": 36_734, "impairment_losses": 4_011,
        "income_before_tax": 71_261, "net_income": 57_563,
        "total_comprehensive_income": 58_909, "eps": 467,
    },
    {
        "year": 2024, "period": "FY2024",
        "operating_income": 106_552, "net_interest_income": 82_264,
        "operating_expenses": 36_300, "impairment_losses": 2_034,
        "income_before_tax": 68_218, "net_income": 54_851,
        "total_comprehensive_income": 54_506, "eps": 445,
    },
    {
        "year": 2023, "period": "FY2023",
        "operating_income": 96_728, "net_interest_income": 74_938,
        "operating_expenses": 35_492, "impairment_losses": 1_056,
        "income_before_tax": 60_180, "net_income": 48_458,
        "total_comprehensive_income": 47_552, "eps": 395,
    },
    {
        "year": 2022, "period": "FY2022",
        "operating_income": 83_981, "net_interest_income": 63_863,
        "operating_expenses": 30_200, "impairment_losses": 3_314,
        "income_before_tax": 50_467, "net_income": 40_756,
        "total_comprehensive_income": 37_433, "eps": 330,
    },
    {
        "year": 2021, "period": "FY2021",
        "operating_income": 75_430, "net_interest_income": 55_987,
        "operating_expenses": 28_346, "impairment_losses": 8_243,
        "income_before_tax": 38_841, "net_income": 31_440,
        "total_comprehensive_income": 31_867, "eps": 255,
    },
]

BBCA_RATIOS = [
    {
        "year": 2025, "period": "FY2025",
        "car": 29.8, "car_tier1": 28.6, "car_tier2": 1.1,
        "npl_gross": 1.7, "npl_net": 0.7, "lar": 4.8,
        "roa": 3.9, "roe": 23.3, "nim": 5.7,
        "cir": 30.7, "bopo": 41.6,
        "ldr": 76.8, "lcr": 310.8, "nsfr": 159.9,
        "casa_ratio": 83.7,
    },
    {
        "year": 2024, "period": "FY2024",
        "car": 29.4, "car_tier1": 28.2, "car_tier2": 1.1,
        "npl_gross": 1.8, "npl_net": 0.6, "lar": 5.3,
        "roa": 3.9, "roe": 24.6, "nim": 5.8,
        "cir": 31.3, "bopo": 41.7,
        "ldr": 78.4, "lcr": 323.0, "nsfr": 157.3,
        "casa_ratio": 81.5,
    },
    {
        "year": 2023, "period": "FY2023",
        "car": 29.4, "car_tier1": 28.3, "car_tier2": 1.1,
        "npl_gross": 1.9, "npl_net": 0.6, "lar": 6.9,
        "roa": 3.6, "roe": 23.5, "nim": 5.5,
        "cir": 33.9, "bopo": 43.7,
        "ldr": 70.2, "lcr": 357.8, "nsfr": 168.6,
        "casa_ratio": 80.3,
    },
    {
        "year": 2022, "period": "FY2022",
        "car": 25.8, "car_tier1": 24.8, "car_tier2": 1.0,
        "npl_gross": 1.8, "npl_net": 0.6, "lar": 10.4,
        "roa": 3.2, "roe": 21.7, "nim": 5.3,
        "cir": 34.9, "bopo": 46.1,
        "ldr": 65.2, "lcr": 393.5, "nsfr": 171.1,
        "casa_ratio": 81.6,
    },
    {
        "year": 2021, "period": "FY2021",
        "car": 25.7, "car_tier1": 24.7, "car_tier2": 1.0,
        "npl_gross": 2.2, "npl_net": 0.8, "lar": 15.2,
        "roa": 2.8, "roe": 18.3, "nim": 5.1,
        "cir": 34.8, "bopo": 54.2,
        "ldr": 62.0, "lcr": 396.3, "nsfr": 180.7,
        "casa_ratio": 78.6,
    },
]

BBCA_STOCK_HIGHLIGHTS = [
    {
        "year": 2025,
        "highest": 9_925, "lowest": 7_225, "closing": 8_075,
        "market_cap_trillion": 995, "eps": 467, "bvps": 2_288,
        "pe": 17.3, "pbv": 3.8,
    },
    {
        "year": 2024,
        "highest": 10_950, "lowest": 8_775, "closing": 9_675,
        "market_cap_trillion": 1_193, "eps": 445, "bvps": 2_131,
        "pe": 21.7, "pbv": 4.5,
    },
    {
        "year": 2023,
        "highest": 9_450, "lowest": 8_000, "closing": 9_400,
        "market_cap_trillion": 1_159, "eps": 395, "bvps": 1_966,
        "pe": 23.8, "pbv": 4.8,
    },
    {
        "year": 2022,
        "highest": 9_400, "lowest": 7_000, "closing": 8_550,
        "market_cap_trillion": 1_054, "eps": 330, "bvps": 1_794,
        "pe": 25.9, "pbv": 4.8,
    },
    {
        "year": 2021,
        "highest": 8_250, "lowest": 5_905, "closing": 7_300,
        "market_cap_trillion": 900, "eps": 255, "bvps": 1_645,
        "pe": 28.6, "pbv": 4.4,
    },
]
