from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.outbox_event import OutboxEvent
from app.models.processed_event import ProcessedEvent
from app.models.service_order import ServiceOrder, ServiceOrderHistory, ServiceOrderStatus
from app.models.client import Client
from app.models.vehicle import Vehicle
from app.repositories import order_repository
from app.schemas.order import OrderCreate


class OrderService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: OrderCreate) -> ServiceOrder:
        client = self._upsert_client(data)
        vehicle = self._upsert_vehicle(data, client)

        order = ServiceOrder(
            client_id=client.id,
            vehicle_id=vehicle.id,
            description=data.description,
            status=ServiceOrderStatus.OPEN,
        )
        self.db.add(order)
        self.db.flush()
        self.db.add(
            ServiceOrderHistory(
                order_id=order.id,
                previous_status=None,
                status=order.status,
                source="os-service",
            )
        )
        self.db.add(
            OutboxEvent(
                event_type="OrderCreated",
                aggregate_id=str(order.id),
                payload={
                    "eventType": "OrderCreated",
                    "orderId": order.id,
                    "customer": {
                        "id": client.id,
                        "name": client.name,
                        "cpf": client.cpf,
                    },
                    "vehicle": {
                        "id": vehicle.id,
                        "plate": vehicle.plate,
                        "brand": vehicle.brand,
                        "model": vehicle.model,
                        "year": vehicle.year,
                    },
                    "description": order.description,
                },
            )
        )
        self.db.commit()
        return self.get_by_id(order.id)

    def _upsert_client(self, data: OrderCreate) -> Client:
        client = order_repository.get_client_by_cpf(self.db, data.customer.cpf)
        if client is None:
            client = Client(
                name=data.customer.name,
                cpf=data.customer.cpf,
                email=data.customer.email,
                is_active=True,
            )
            self.db.add(client)
            self.db.flush()
            return client

        if not client.is_active:
            raise HTTPException(status_code=422, detail="Client is inactive")
        client.name = data.customer.name
        client.email = data.customer.email
        return client

    def _upsert_vehicle(self, data: OrderCreate, client: Client) -> Vehicle:
        vehicle = order_repository.get_vehicle_by_plate(self.db, data.vehicle.plate)
        if vehicle is None:
            vehicle = Vehicle(client_id=client.id, **data.vehicle.model_dump())
            self.db.add(vehicle)
            self.db.flush()
            return vehicle

        if vehicle.client_id != client.id:
            raise HTTPException(status_code=409, detail="Vehicle belongs to another client")
        vehicle.brand = data.vehicle.brand
        vehicle.model = data.vehicle.model
        vehicle.year = data.vehicle.year
        return vehicle

    def get_by_id(self, order_id: int) -> ServiceOrder:
        order = order_repository.get_order(self.db, order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    def list(self, client_id: int | None, vehicle_id: int | None, status: str | None):
        return order_repository.list_orders(self.db, client_id, vehicle_id, status)

    def update_status(
        self, order_id: int, status: ServiceOrderStatus, source: str = "os-service"
    ) -> ServiceOrder:
        order = self.get_by_id(order_id)
        if order.status == status:
            return order

        previous_status = order.status
        order.status = status
        self.db.add(
            ServiceOrderHistory(
                order_id=order.id,
                previous_status=previous_status,
                status=status,
                source=source,
            )
        )
        self.db.commit()
        return self.get_by_id(order.id)

    def apply_external_event(
        self, event_id: str, event_type: str, order_id: int, status: ServiceOrderStatus
    ) -> ServiceOrder:
        if self.db.get(ProcessedEvent, event_id) is not None:
            return self.get_by_id(order_id)

        order = self.get_by_id(order_id)
        if order.status != status:
            previous_status = order.status
            order.status = status
            self.db.add(
                ServiceOrderHistory(
                    order_id=order.id,
                    previous_status=previous_status,
                    status=status,
                    source=event_type,
                )
            )
        self.db.add(
            ProcessedEvent(event_id=event_id, event_type=event_type, order_id=order_id)
        )
        self.db.commit()
        return self.get_by_id(order.id)
