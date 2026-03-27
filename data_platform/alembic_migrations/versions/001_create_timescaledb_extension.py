"""Create TimescaleDB extension and core schemas.

Revision ID: 001
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op
from sqlalchemy import text

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def _try_execute(sql: str) -> None:
    """Execute SQL, ignoring failures (e.g. missing extensions in plain postgres).

    Uses a savepoint so that a failure only rolls back this statement,
    not the entire Alembic migration transaction (which would drop the
    alembic_version table).
    """
    conn = op.get_bind()
    try:
        nested = conn.begin_nested()
        conn.execute(text(sql))
        nested.commit()
    except Exception:
        nested.rollback()


def upgrade() -> None:
    """Create TimescaleDB extension and all required schemas."""
    _try_execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
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
