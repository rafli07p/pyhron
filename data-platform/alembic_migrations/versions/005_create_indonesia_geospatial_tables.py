"""Create Indonesia geospatial tables: fire hotspots, weather rainfall.

Revision ID: 005
Create Date: 2024-01-01 00:04:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create fire hotspot event and weather rainfall tables."""
    # NASA FIRMS fire hotspot events
    op.create_table(
        "indonesia_fire_hotspot_event",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("brightness", sa.Float()),
        sa.Column("fire_radiative_power", sa.Float()),
        sa.Column("confidence", sa.String(10), nullable=False),
        sa.Column("satellite", sa.String(20)),
        sa.Column("acquisition_date", sa.Date(), nullable=False),
        sa.Column("acquisition_time", sa.String(10)),
        sa.Column("province", sa.String(100)),
        sa.Column("district", sa.String(100)),
        sa.Column("company_concession", sa.String(200)),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="alternative_data",
    )
    op.create_index(
        "ix_fire_hotspot_date",
        "indonesia_fire_hotspot_event",
        ["acquisition_date"],
        schema="alternative_data",
    )
    op.create_index(
        "ix_fire_hotspot_province",
        "indonesia_fire_hotspot_event",
        ["province"],
        schema="alternative_data",
    )
    op.create_index(
        "ix_fire_hotspot_concession",
        "indonesia_fire_hotspot_event",
        ["company_concession"],
        schema="alternative_data",
    )

    # BMKG daily rainfall
    op.create_table(
        "indonesia_weather_rainfall",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("province", sa.String(100), nullable=False),
        sa.Column("station_name", sa.String(200)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("rainfall_mm", sa.Numeric(8, 2)),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(50), server_default="BMKG"),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="alternative_data",
    )
    op.create_index(
        "ix_rainfall_province_date",
        "indonesia_weather_rainfall",
        ["province", "observation_date"],
        schema="alternative_data",
    )


def downgrade() -> None:
    """Drop geospatial tables."""
    op.drop_table("indonesia_weather_rainfall", schema="alternative_data")
    op.drop_table("indonesia_fire_hotspot_event", schema="alternative_data")
