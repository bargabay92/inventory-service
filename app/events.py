"""Publishes orders_common events. The bus is an in-memory outbox here; production uses the broker."""
from typing import List

from orders_common import EventType, OrderEvent
from app.settings import settings

OUTBOX: List[bytes] = []


def publish(event_type: EventType, **payload) -> OrderEvent:
    event = OrderEvent(event_type=event_type, source=settings.service_name, payload=payload)
    OUTBOX.append(event.to_message())
    return event
