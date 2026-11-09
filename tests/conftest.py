import pytest
from fastapi.testclient import TestClient

from app import events
from app.db import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    events.OUTBOX.clear()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def stocked(client):
    client.post("/warehouses", json={"code": "LON1", "name": "London",
                                     "address": {"line1": "1 Dock Rd", "city": "London", "postcode": "e16 1aa", "country": "gb"}})
    client.post("/products", json={"sku": "abc-1234", "name": "Widget", "unit_price": "19.99"})
    client.post("/products", json={"sku": "XYZ-0001", "name": "Gadget", "unit_price": 5})
    client.post("/stock/adjust", json={"warehouse_code": "LON1", "sku": "ABC-1234", "delta": 20})
    client.post("/stock/adjust", json={"warehouse_code": "LON1", "sku": "XYZ-0001", "delta": 8})
    events.OUTBOX.clear()
    return client
