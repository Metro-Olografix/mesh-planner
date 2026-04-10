"""Initial schema — hardware_profiles, nodes, coverage_cache, node_events

Revision ID: 0001
Revises:
Create Date: 2026-04-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

nodestatus = sa.Enum("planned", "deployed", name="nodestatus")


def upgrade() -> None:
    op.create_table(
        "hardware_profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("manufacturer", sa.String(), nullable=False),
        sa.Column("tx_power_dbm", sa.Float(), nullable=False),
        sa.Column(
            "frequency_mhz", sa.Float(), nullable=False, server_default="869.525"
        ),
        sa.Column(
            "rx_sensitivity_dbm", sa.Float(), nullable=False, server_default="-130"
        ),
        sa.Column(
            "default_antenna_gain_dbi", sa.Float(), nullable=False, server_default="2"
        ),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_custom", sa.Boolean(), server_default="false"),
    )

    nodestatus.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "nodes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("height_m", sa.Float(), nullable=False, server_default="2"),
        sa.Column("status", nodestatus, nullable=False, server_default="planned"),
        sa.Column(
            "hardware_id",
            sa.String(),
            sa.ForeignKey("hardware_profiles.id"),
            nullable=False,
        ),
        sa.Column("antenna_gain_dbi", sa.Float(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )

    op.create_table(
        "coverage_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "node_id",
            UUID(as_uuid=True),
            sa.ForeignKey("nodes.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("geotiff", sa.LargeBinary(), nullable=True),
        sa.Column("computed_at", sa.DateTime(), nullable=True),
        sa.Column("invalidated", sa.Boolean(), server_default="false"),
    )

    op.create_table(
        "node_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("node_id", sa.String(), nullable=True),
        sa.Column("node_name", sa.String(), nullable=False),
        sa.Column("by", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("node_events")
    op.drop_table("coverage_cache")
    op.drop_table("nodes")
    op.drop_table("hardware_profiles")
    nodestatus.drop(op.get_bind(), checkfirst=True)
