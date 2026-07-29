"""Handlers invoked by the RabbitMQ consumer added in the integration stage."""

from sqlalchemy.orm import Session

from app.models.service_order import ServiceOrderStatus
from app.services.order_service import OrderService


EVENT_STATUS = {
    "BudgetCreated": ServiceOrderStatus.WAITING_APPROVAL,
    "PaymentApproved": ServiceOrderStatus.PAID,
    "ExecutionStarted": ServiceOrderStatus.IN_EXECUTION,
    "ExecutionFinished": ServiceOrderStatus.COMPLETED,
    "RefundProcessed": ServiceOrderStatus.CANCELLED,
}


def handle_event(db: Session, event: dict):
    event_type = event["eventType"]
    if event_type not in EVENT_STATUS:
        raise ValueError(f"Unsupported OS event: {event_type}")
    return OrderService(db).apply_external_event(
        event_id=event["eventId"],
        event_type=event_type,
        order_id=event["orderId"],
        status=EVENT_STATUS[event_type],
    )
