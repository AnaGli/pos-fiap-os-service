from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.client import Client
from app.models.service_order import ServiceOrder
from app.models.vehicle import Vehicle


def get_client(db: Session, client_id: int) -> Client | None:
    return db.get(Client, client_id)


def get_client_by_cpf(db: Session, cpf: str) -> Client | None:
    return db.scalar(select(Client).where(Client.cpf == cpf))


def get_vehicle(db: Session, vehicle_id: int) -> Vehicle | None:
    return db.get(Vehicle, vehicle_id)


def get_vehicle_by_plate(db: Session, plate: str) -> Vehicle | None:
    return db.scalar(select(Vehicle).where(Vehicle.plate == plate))


def get_order(db: Session, order_id: int) -> ServiceOrder | None:
    statement = (
        select(ServiceOrder)
        .where(ServiceOrder.id == order_id)
        .options(selectinload(ServiceOrder.history))
    )
    return db.scalar(statement)


def list_orders(
    db: Session, client_id: int | None, vehicle_id: int | None, status: str | None
) -> list[ServiceOrder]:
    statement = select(ServiceOrder).options(selectinload(ServiceOrder.history))
    if client_id is not None:
        statement = statement.where(ServiceOrder.client_id == client_id)
    if vehicle_id is not None:
        statement = statement.where(ServiceOrder.vehicle_id == vehicle_id)
    if status is not None:
        statement = statement.where(ServiceOrder.status == status)
    return list(db.scalars(statement.order_by(ServiceOrder.created_at.desc())))
