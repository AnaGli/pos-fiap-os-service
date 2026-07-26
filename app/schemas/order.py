from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.service_order import ServiceOrderStatus


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    cpf: str = Field(min_length=11, max_length=11)
    email: str = Field(min_length=1, max_length=100)


class VehicleCreate(BaseModel):
    plate: str = Field(min_length=1, max_length=10)
    brand: str = Field(min_length=1, max_length=50)
    model: str = Field(min_length=1, max_length=50)
    year: int = Field(ge=1886, le=9999)


class OrderCreate(BaseModel):
    customer: CustomerCreate
    vehicle: VehicleCreate
    description: str = Field(min_length=1, max_length=4000)


class OrderStatusUpdate(BaseModel):
    status: ServiceOrderStatus


class OrderHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    previous_status: ServiceOrderStatus | None
    status: ServiceOrderStatus
    occurred_at: datetime
    source: str


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    vehicle_id: int
    description: str
    status: ServiceOrderStatus
    created_at: datetime
    updated_at: datetime
    history: list[OrderHistoryResponse]
