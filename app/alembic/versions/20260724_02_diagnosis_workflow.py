"""adapt OS Service to the diagnosis-first workflow

Revision ID: 20260724_02
Revises: 20260723_01
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260724_02"
down_revision = "20260723_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE serviceorderstatus RENAME VALUE 'CREATED' TO 'OPEN'")
    op.execute("ALTER TYPE serviceorderstatus RENAME VALUE 'BUDGET_PENDING' TO 'WAITING_DIAGNOSIS'")
    op.execute("ALTER TYPE serviceorderstatus RENAME VALUE 'BUDGET_READY' TO 'WAITING_APPROVAL'")
    op.execute("ALTER TYPE serviceorderstatus RENAME VALUE 'REFUNDED' TO 'CANCELLED'")

    op.add_column(
        "service_orders",
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
    )
    op.alter_column("service_orders", "description", server_default=None)
    op.create_table(
        "processed_events",
        sa.Column("event_id", sa.String(length=100), primary_key=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("processed_events")
    op.drop_column("service_orders", "description")
    op.execute("ALTER TYPE serviceorderstatus RENAME VALUE 'OPEN' TO 'CREATED'")
    op.execute("ALTER TYPE serviceorderstatus RENAME VALUE 'WAITING_DIAGNOSIS' TO 'BUDGET_PENDING'")
    op.execute("ALTER TYPE serviceorderstatus RENAME VALUE 'WAITING_APPROVAL' TO 'BUDGET_READY'")
    op.execute("ALTER TYPE serviceorderstatus RENAME VALUE 'CANCELLED' TO 'REFUNDED'")
