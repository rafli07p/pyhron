"""Create TimescaleDB extension and core schemas.

Revision ID: 001
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create TimescaleDB extension and all required schemas."""
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("CREATE SCHEMA IF NOT EXISTS market_data")
    op.execute("CREATE SCHEMA IF NOT EXISTS trading")
    op.execute("CREATE SCHEMA IF NOT EXISTS risk")
    op.execute("CREATE SCHEMA IF NOT EXISTS macro")
    op.execute("CREATE SCHEMA IF NOT EXISTS commodity")
    op.execute("CREATE SCHEMA IF NOT EXISTS alternative_data")
    op.execute("CREATE SCHEMA IF NOT EXISTS fixed_income")
    op.execute("CREATE SCHEMA IF NOT EXISTS governance")
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")


def downgrade() -> None:
    """Drop schemas in reverse order."""
    op.execute("DROP SCHEMA IF EXISTS audit CASCADE")
    op.execute("DROP SCHEMA IF EXISTS governance CASCADE")
    op.execute("DROP SCHEMA IF EXISTS fixed_income CASCADE")
    op.execute("DROP SCHEMA IF EXISTS alternative_data CASCADE")
    op.execute("DROP SCHEMA IF EXISTS commodity CASCADE")
    op.execute("DROP SCHEMA IF EXISTS macro CASCADE")
    op.execute("DROP SCHEMA IF EXISTS risk CASCADE")
    op.execute("DROP SCHEMA IF EXISTS trading CASCADE")
    op.execute("DROP SCHEMA IF EXISTS market_data CASCADE")
