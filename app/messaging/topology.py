from dataclasses import dataclass


EXCHANGE_NAME = "workshop.events"


@dataclass(frozen=True)
class QueueBinding:
    queue_name: str
    routing_key: str


QUEUE_BINDINGS = [
    QueueBinding("os.budget-created", "budget.created"),
    QueueBinding("os.payment-approved", "payment.approved"),
    QueueBinding("os.execution-started", "execution.started"),
    QueueBinding("os.execution-finished", "execution.finished"),
    QueueBinding("os.refund-processed", "refund.processed"),
]
