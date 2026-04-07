"""Add draft status and sim_radius_km, environment, lora_preset, high_resolution columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'draft' value to the nodestatus PG enum
    op.execute(
        "DO $$ BEGIN "
        "  ALTER TYPE nodestatus ADD VALUE IF NOT EXISTS 'draft'; "
        "EXCEPTION WHEN undefined_object THEN NULL; "
        "END $$"
    )

    op.add_column("nodes", sa.Column("sim_radius_km", sa.Float(), nullable=False, server_default="10"))
    op.add_column("nodes", sa.Column("environment", sa.String(), nullable=False, server_default="auto"))
    op.add_column("nodes", sa.Column("lora_preset", sa.String(), nullable=False, server_default="MEDIUM_FAST"))
    op.add_column("nodes", sa.Column("high_resolution", sa.Boolean(), nullable=False, server_default="true"))


def downgrade() -> None:
    op.drop_column("nodes", "high_resolution")
    op.drop_column("nodes", "lora_preset")
    op.drop_column("nodes", "environment")
    op.drop_column("nodes", "sim_radius_km")
    # Note: removing an enum value from PG requires recreating the type;
    # skipped here as it's rarely needed.
