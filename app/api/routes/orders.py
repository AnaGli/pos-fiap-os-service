from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    return OrderService(db)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(data: OrderCreate, service: OrderService = Depends(get_order_service)):
    return service.create(data)


@router.get("", response_model=list[OrderResponse])
def list_orders(
    client_id: int | None = None,
    vehicle_id: int | None = None,
    status: str | None = None,
    service: OrderService = Depends(get_order_service),
):
    return service.list(client_id, vehicle_id, status)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, service: OrderService = Depends(get_order_service)):
    return service.get_by_id(order_id)


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    service: OrderService = Depends(get_order_service),
):
    return service.update_status(order_id, data.status)
