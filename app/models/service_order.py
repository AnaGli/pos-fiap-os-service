import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ServiceOrderStatus(str, enum.Enum):
    OPEN = "OPEN"
    WAITING_DIAGNOSIS = "WAITING_DIAGNOSIS"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAID = "PAID"
    IN_EXECUTION = "IN_EXECUTION"
    COMPLETED = "COMPLETED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    CANCELLED = "CANCELLED"


class ServiceOrder(Base):
    __tablename__ = "service_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ServiceOrderStatus] = mapped_column(
        Enum(ServiceOrderStatus), nullable=False, default=ServiceOrderStatus.OPEN
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    client = relationship("Client")
    vehicle = relationship("Vehicle")
    history = relationship(
        "ServiceOrderHistory",
        back_populates="service_order",
        cascade="all, delete-orphan",
        order_by="ServiceOrderHistory.id",
    )


class ServiceOrderHistory(Base):
    __tablename__ = "service_order_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("service_orders.id"), nullable=False)
    previous_status: Mapped[ServiceOrderStatus | None] = mapped_column(
        Enum(ServiceOrderStatus), nullable=True
    )
    status: Mapped[ServiceOrderStatus] = mapped_column(Enum(ServiceOrderStatus), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source: Mapped[str] = mapped_column(String(80), nullable=False)

    service_order = relationship("ServiceOrder", back_populates="history")
