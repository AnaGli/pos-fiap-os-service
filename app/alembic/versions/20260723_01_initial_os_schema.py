"""create initial OS Service schema

Revision ID: 20260723_01
Revises:
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260723_01"
down_revision = None
branch_labels = None
depends_on = None

status_enum = postgresql.ENUM(
    "CREATED", "BUDGET_PENDING", "BUDGET_READY", "PAYMENT_PENDING", "PAID",
    "IN_EXECUTION", "COMPLETED", "EXECUTION_FAILED", "REFUNDED",
    name="serviceorderstatus",
    create_type=False,
)


def upgrade() -> None:
    status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("cpf", sa.String(length=11), nullable=False, unique=True),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plate", sa.String(length=10), nullable=False, unique=True),
        sa.Column("brand", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=50), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
    )
    op.create_table(
        "service_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "service_order_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("service_orders.id"), nullable=False),
        sa.Column("previous_status", status_enum, nullable=True),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
    )
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("aggregate_id", sa.String(length=50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("outbox_events")
    op.drop_table("service_order_history")
    op.drop_table("service_orders")
    op.drop_table("vehicles")
    op.drop_table("clients")
    status_enum.drop(op.get_bind(), checkfirst=True)
