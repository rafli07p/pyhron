"""Seed IDX LQ45 constituent instruments and IHSG index.

Populates the instrument master table with the most liquid IDX equities.

Revision ID: 012
Create Date: 2026-03-10 00:03:00.000000
"""

from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None

# LQ45 constituents + IHSG index
LQ45_SYMBOLS = [
    ("ACES", "Ace Hardware Indonesia Tbk"),
    ("ADRO", "Adaro Energy Indonesia Tbk"),
    ("AKRA", "AKR Corporindo Tbk"),
    ("AMRT", "Sumber Alfaria Trijaya Tbk"),
    ("ANTM", "Aneka Tambang Tbk"),
    ("ARTO", "Bank Jago Tbk"),
    ("ASII", "Astra International Tbk"),
    ("BBCA", "Bank Central Asia Tbk"),
    ("BBNI", "Bank Negara Indonesia Tbk"),
    ("BBRI", "Bank Rakyat Indonesia Tbk"),
    ("BBTN", "Bank Tabungan Negara Tbk"),
    ("BFIN", "BFI Finance Indonesia Tbk"),
    ("BJBR", "Bank Pembangunan Daerah Jawa Barat Tbk"),
    ("BMRI", "Bank Mandiri Tbk"),
    ("BNGA", "Bank CIMB Niaga Tbk"),
    ("BRPT", "Barito Pacific Tbk"),
    ("BTPS", "Bank BTPN Syariah Tbk"),
    ("BUKA", "Bukalapak.com Tbk"),
    ("CPIN", "Charoen Pokphand Indonesia Tbk"),
    ("ERAA", "Erajaya Swasembada Tbk"),
    ("EXCL", "XL Axiata Tbk"),
    ("GOTO", "GoTo Gojek Tokopedia Tbk"),
    ("HEAL", "Medikaloka Hermina Tbk"),
    ("HMSP", "H.M. Sampoerna Tbk"),
    ("HRUM", "Harum Energy Tbk"),
    ("ICBP", "Indofood CBP Sukses Makmur Tbk"),
    ("INCO", "Vale Indonesia Tbk"),
    ("INDF", "Indofood Sukses Makmur Tbk"),
    ("INTP", "Indocement Tunggal Prakarsa Tbk"),
    ("ITMG", "Indo Tambangraya Megah Tbk"),
    ("JPFA", "Japfa Comfeed Indonesia Tbk"),
    ("JSMR", "Jasa Marga Tbk"),
    ("KLBF", "Kalbe Farma Tbk"),
    ("MEDC", "Medco Energi Internasional Tbk"),
    ("MIKA", "Mitra Keluarga Karyasehat Tbk"),
    ("MNCN", "Media Nusantara Citra Tbk"),
    ("PGAS", "Perusahaan Gas Negara Tbk"),
    ("PTBA", "Bukit Asam Tbk"),
    ("SIDO", "Industri Jamu dan Farmasi Sido Muncul Tbk"),
    ("SMGR", "Semen Indonesia Tbk"),
    ("TAPG", "Triputra Agro Persada Tbk"),
    ("TBIG", "Tower Bersama Infrastructure Tbk"),
    ("TLKM", "Telkom Indonesia Tbk"),
    ("TOWR", "Sarana Menara Nusantara Tbk"),
    ("TPIA", "Chandra Asri Petrochemical Tbk"),
    ("UNTR", "United Tractors Tbk"),
    ("UNVR", "Unilever Indonesia Tbk"),
    ("VALE", "Vale Indonesia Tbk"),
    ("WIFI", "Solusi Sinergi Digital Tbk"),
]


def upgrade() -> None:
    """Seed LQ45 constituents and IHSG index into instruments table."""
    for symbol, name in LQ45_SYMBOLS:
        escaped_name = name.replace("'", "''")
        op.execute(
            f"INSERT INTO market_data.idx_equity_instrument "
            f"(symbol, company_name, board, is_active) "
            f"VALUES ('{symbol}', '{escaped_name}', 'IDX', true) "
            f"ON CONFLICT (symbol) DO NOTHING"
        )

    # IHSG index
    op.execute(
        "INSERT INTO market_data.idx_equity_instrument "
        "(symbol, company_name, board, is_active) "
        "VALUES ('^JKSE', 'Jakarta Composite Index (IHSG)', 'IDX', true) "
        "ON CONFLICT (symbol) DO NOTHING"
    )


def downgrade() -> None:
    """Remove seeded LQ45 instruments."""
    symbols = ", ".join(f"'{s}'" for s, _ in LQ45_SYMBOLS)
    op.execute(f"DELETE FROM market_data.idx_equity_instrument WHERE symbol IN ({symbols}, '^JKSE')")
