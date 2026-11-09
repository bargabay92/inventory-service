import pytest
from pydantic import ValidationError

from app import schemas
from app.settings import Settings


def test_settings_env(monkeypatch):
    monkeypatch.setenv("INVENTORY_LOW_STOCK_THRESHOLD", "9")
    assert Settings().low_stock_threshold == 9


def test_event_payload_serialises():
    from orders_common import EventType
    from app.events import OUTBOX, publish
    e = publish(EventType.STOCK_LOW, sku="ABC-1234", available=2)
    assert OUTBOX[-1].startswith(b"{") and e.source == "inventory"


def test_stock_adjust_rejects_zero():
    with pytest.raises(ValidationError):
        schemas.StockAdjust(warehouse_code="LON1", sku="ABC-1234", delta=0)


def test_product_update_partial():
    assert schemas.ProductUpdate(name="New").dict(exclude_unset=True) == {"name": "New"}
