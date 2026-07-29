import json
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_os_service.db"
os.environ["RABBITMQ_URL"] = "amqp://guest:guest@localhost:5672/"

from app.database import Base, SessionLocal, engine
from app.events.handlers import handle_event
from app.messaging import consumer, outbox_publisher
from app.messaging.outbox_publisher import publish_pending_events
from app.messaging.rabbitmq import RabbitMQPublisher, declare_topology, rabbitmq_url, routing_key_for
from app.messaging.topology import EXCHANGE_NAME, QUEUE_BINDINGS, QueueBinding
from app.models.outbox_event import OutboxEvent


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_rabbitmq_url_reads_env():
    assert rabbitmq_url() == "amqp://guest:guest@localhost:5672/"


def test_routing_key_for_converts_camel_case():
    assert routing_key_for("PaymentApproved") == "payment.approved"
    assert routing_key_for("ExecutionFinished") == "execution.finished"


def test_declare_topology_declares_exchange_and_bindings():
    calls = []

    class FakeChannel:
        def exchange_declare(self, **kwargs):
            calls.append(("exchange", kwargs))

        def queue_declare(self, **kwargs):
            calls.append(("queue", kwargs))

        def queue_bind(self, **kwargs):
            calls.append(("bind", kwargs))

    channel = FakeChannel()
    bindings = [QueueBinding("os.test", "os.test.key")]

    declare_topology(channel, bindings)

    assert calls[0] == ("exchange", {"exchange": EXCHANGE_NAME, "exchange_type": "topic", "durable": True})
    assert ("queue", {"queue": "os.test", "durable": True}) in calls
    assert ("bind", {"exchange": EXCHANGE_NAME, "queue": "os.test", "routing_key": "os.test.key"}) in calls


def test_rabbitmq_publisher_uses_expected_routing_key(monkeypatch):
    published = {}

    class FakeChannel:
        def confirm_delivery(self):
            published["confirmed"] = True

        def basic_publish(self, **kwargs):
            published.update(kwargs)

    class FakeConnection:
        def __init__(self):
            self.channel_instance = FakeChannel()

        def channel(self):
            return self.channel_instance

        def close(self):
            published["closed"] = True

    monkeypatch.setattr("app.messaging.rabbitmq.build_connection", lambda: FakeConnection())
    monkeypatch.setattr("app.messaging.rabbitmq.declare_topology", lambda channel, bindings: None)

    RabbitMQPublisher().publish("PaymentApproved", {"orderId": 1})

    assert published["exchange"] == EXCHANGE_NAME
    assert published["routing_key"] == "payment.approved"
    assert json.loads(published["body"]) == {"orderId": 1}
    assert published["mandatory"] is True
    assert published["closed"] is True


def test_queue_bindings_cover_expected_event_routes():
    existing_bindings = {(binding.queue_name, binding.routing_key) for binding in QUEUE_BINDINGS}
    assert ("os.budget-created", "budget.created") in existing_bindings
    assert ("os.payment-approved", "payment.approved") in existing_bindings
    assert ("os.execution-started", "execution.started") in existing_bindings
    assert ("os.execution-finished", "execution.finished") in existing_bindings
    assert ("os.refund-processed", "refund.processed") in existing_bindings


def test_publish_pending_events_marks_event_as_published(monkeypatch):
    published_messages = []

    class FakePublisher:
        def publish(self, event_type, message):
            published_messages.append((event_type, message))

    monkeypatch.setattr("app.messaging.outbox_publisher.RabbitMQPublisher", lambda: FakePublisher())

    with SessionLocal() as db:
        event = OutboxEvent(
            event_type="OrderCreated",
            aggregate_id="101",
            payload={"orderId": 101, "description": "Ruído no motor"},
        )
        db.add(event)
        db.commit()

    count = publish_pending_events()

    assert count == 1
    assert published_messages[0][0] == "OrderCreated"
    assert published_messages[0][1]["eventType"] == "OrderCreated"

    with SessionLocal() as db:
        persisted = db.query(OutboxEvent).one()
        assert persisted.published_at is not None


def test_publish_pending_events_returns_zero_when_no_events(monkeypatch):
    monkeypatch.setattr("app.messaging.outbox_publisher.RabbitMQPublisher", lambda: object())

    count = publish_pending_events()

    assert count == 0


def test_outbox_publisher_main_retries_after_error(monkeypatch):
    calls = {"publish": 0, "sleep": 0, "logged": 0}

    def fake_publish_pending_events():
        calls["publish"] += 1
        if calls["publish"] == 1:
            raise RuntimeError("boom")
        raise KeyboardInterrupt()

    def fake_sleep(seconds):
        calls["sleep"] += 1

    def fake_exception(message):
        calls["logged"] += 1

    monkeypatch.setattr(outbox_publisher, "publish_pending_events", fake_publish_pending_events)
    monkeypatch.setattr(outbox_publisher.time, "sleep", fake_sleep)
    monkeypatch.setattr(outbox_publisher.logger, "exception", fake_exception)

    try:
        outbox_publisher.main()
    except KeyboardInterrupt:
        pass

    assert calls["publish"] == 2
    assert calls["sleep"] >= 1
    assert calls["logged"] == 1


def test_consumer_main_processes_message_and_acknowledges(monkeypatch):
    consumed = {}

    class FakeMethod:
        delivery_tag = "tag-1"

    class FakeChannel:
        def basic_qos(self, prefetch_count):
            consumed["prefetch_count"] = prefetch_count

        def basic_consume(self, queue, on_message_callback):
            consumed.setdefault("queues", []).append(queue)
            consumed["callback"] = on_message_callback

        def start_consuming(self):
            consumed["started"] = True
            consumed["callback"](
                self,
                FakeMethod(),
                None,
                json.dumps({"eventType": "PaymentApproved", "eventId": "evt-1", "orderId": 10}).encode(),
            )

        def basic_ack(self, delivery_tag):
            consumed["ack"] = delivery_tag

        def basic_nack(self, delivery_tag, requeue):
            consumed["nack"] = (delivery_tag, requeue)

    class FakeConnection:
        def __init__(self):
            self.channel_instance = FakeChannel()

        def channel(self):
            return self.channel_instance

    monkeypatch.setattr("app.messaging.consumer.build_connection", lambda: FakeConnection())
    monkeypatch.setattr("app.messaging.consumer.declare_topology", lambda channel, bindings: None)
    monkeypatch.setattr("app.messaging.consumer.handle_event", lambda db, event: consumed.setdefault("event", event))

    consumer.main()

    assert consumed["prefetch_count"] == 10
    assert set(consumed["queues"]) == {binding.queue_name for binding in QUEUE_BINDINGS}
    assert consumed["started"] is True
    assert consumed["event"] == {"eventType": "PaymentApproved", "eventId": "evt-1", "orderId": 10}
    assert consumed["ack"] == "tag-1"
    assert "nack" not in consumed


def test_consumer_main_requeues_message_on_processing_error(monkeypatch):
    consumed = {}

    class FakeMethod:
        delivery_tag = "tag-2"

    class FakeChannel:
        def basic_qos(self, prefetch_count):
            consumed["prefetch_count"] = prefetch_count

        def basic_consume(self, queue, on_message_callback):
            consumed["callback"] = on_message_callback

        def start_consuming(self):
            consumed["callback"](
                self,
                FakeMethod(),
                None,
                json.dumps({"eventType": "PaymentApproved", "eventId": "evt-2", "orderId": 11}).encode(),
            )

        def basic_ack(self, delivery_tag):
            consumed["ack"] = delivery_tag

        def basic_nack(self, delivery_tag, requeue):
            consumed["nack"] = (delivery_tag, requeue)

    class FakeConnection:
        def __init__(self):
            self.channel_instance = FakeChannel()

        def channel(self):
            return self.channel_instance

    monkeypatch.setattr("app.messaging.consumer.build_connection", lambda: FakeConnection())
    monkeypatch.setattr("app.messaging.consumer.declare_topology", lambda channel, bindings: None)

    def raise_error(db, event):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.messaging.consumer.handle_event", raise_error)

    consumer.main()

    assert consumed["nack"] == ("tag-2", True)
    assert "ack" not in consumed


def test_handle_event_raises_for_unsupported_event():
    with SessionLocal() as db:
        try:
            handle_event(db, {"eventType": "UnknownEvent"})
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert "Unsupported OS event" in str(exc)
