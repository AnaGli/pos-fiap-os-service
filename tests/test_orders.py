import os

os.environ["DATABASE_URL"] = "sqlite:///./test_os_service.db"

from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models.outbox_event import OutboxEvent
from app.events.handlers import handle_event

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


ORDER_PAYLOAD = {
    "customer": {"name": "Ana", "cpf": "12345678901", "email": "ana@example.com"},
    "vehicle": {"plate": "ABC1234", "brand": "Ford", "model": "Ka", "year": 2020},
    "description": "Motor perde potência ao acelerar.",
}


def test_create_order_records_history_and_outbox():
    response = client.post("/orders", json=ORDER_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "OPEN"
    assert body["description"] == ORDER_PAYLOAD["description"]
    assert body["history"][0]["previous_status"] is None

    with SessionLocal() as db:
        event = db.query(OutboxEvent).one()
        assert event.event_type == "OrderCreated"
        assert event.payload["orderId"] == body["id"]
        assert event.payload["description"] == ORDER_PAYLOAD["description"]


def test_status_change_is_registered_in_history():
    order_id = client.post("/orders", json=ORDER_PAYLOAD).json()["id"]

    response = client.patch(f"/orders/{order_id}/status", json={"status": "WAITING_DIAGNOSIS"})

    assert response.status_code == 200
    assert [entry["status"] for entry in response.json()["history"]] == ["OPEN", "WAITING_DIAGNOSIS"]


def test_budget_event_updates_status_once():
    order_id = client.post("/orders", json=ORDER_PAYLOAD).json()["id"]
    event = {"eventId": "budget-1", "eventType": "BudgetCreated", "orderId": order_id}

    with SessionLocal() as db:
        handle_event(db, event)
    with SessionLocal() as db:
        result = handle_event(db, event)

    assert result.status.value == "WAITING_APPROVAL"
    response = client.get(f"/orders/{order_id}")
    assert [entry["status"] for entry in response.json()["history"]] == ["OPEN", "WAITING_APPROVAL"]
