import json

from app import events


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_warehouse_round_trip(client):
    r = client.post("/warehouses", json={"code": "MAN2", "name": "Manchester",
                                         "address": {"line1": "5 Mill St", "city": "Manchester", "postcode": "m1 1ad", "country": "GB"}})
    assert r.status_code == 201
    body = r.json()
    assert body["address"] == {"line1": "5 Mill St", "line2": None, "city": "Manchester", "postcode": "M11AD", "country": "GB"}


def test_warehouse_validation(client):
    r = client.post("/warehouses", json={"code": "bad", "name": "x", "address": {"line1": "a", "city": "b", "postcode": "1", "country": "GB"}})
    assert r.status_code == 422


def test_products_page_and_money(stocked):
    page = stocked.get("/products?limit=1").json()
    assert page["total"] == 2 and page["limit"] == 1
    assert page["items"][0] == {"id": 1, "sku": "ABC-1234", "name": "Widget", "unit_price": 19.99}


def test_duplicate_product(stocked):
    assert stocked.post("/products", json={"sku": "ABC-1234", "name": "Again", "unit_price": 1}).status_code == 409


def test_patch_product_keeps_unset_fields(stocked):
    r = stocked.patch("/products/abc-1234", json={"unit_price": "21.50"})
    assert r.status_code == 200
    assert r.json()["name"] == "Widget" and r.json()["unit_price"] == 21.5


def test_stock_levels(stocked):
    rows = stocked.get("/warehouses/LON1/stock").json()
    assert {(r["sku"], r["available"]) for r in rows} == {("ABC-1234", 20), ("XYZ-0001", 8)}


def test_reserve_and_events(stocked):
    r = stocked.post("/reservations", json={"order_ref": "ORD-1", "warehouse_code": "LON1",
                                            "lines": [{"sku": "abc-1234", "qty": 3}, {"sku": "XYZ-0001", "qty": 4}]})
    assert r.status_code == 201, r.text
    assert [x["qty"] for x in r.json()["reservations"]] == [3, 4]
    kinds = [json.loads(m)["eventType"] for m in events.OUTBOX]
    assert kinds == ["stock.reserved", "stock.reserved", "stock.low"]  # XYZ drops to 4 available


def test_reserve_insufficient(stocked):
    r = stocked.post("/reservations", json={"order_ref": "ORD-2", "warehouse_code": "LON1", "lines": [{"sku": "XYZ-0001", "qty": 9}]})
    assert r.status_code == 409 and "available 8" in r.json()["detail"]


def test_reserve_validation(stocked):
    dup = {"order_ref": "ORD-3", "warehouse_code": "LON1", "lines": [{"sku": "ABC-1234", "qty": 1}, {"sku": "abc-1234", "qty": 1}]}
    assert stocked.post("/reservations", json=dup).status_code == 422
    empty = {"order_ref": "ORD-3", "warehouse_code": "LON1", "lines": []}
    assert stocked.post("/reservations", json=empty).status_code == 422
    too_many = {"order_ref": "ORD-3", "warehouse_code": "LON1", "lines": [{"sku": "ABC-1234", "qty": 101}]}
    assert stocked.post("/reservations", json=too_many).status_code == 422


def test_release(stocked):
    stocked.post("/reservations", json={"order_ref": "ORD-4", "warehouse_code": "LON1", "lines": [{"sku": "ABC-1234", "qty": 5}]})
    assert stocked.delete("/reservations/ORD-4").json() == {"released": 1}
    assert stocked.delete("/reservations/ORD-4").status_code == 404
    rows = {r["sku"]: r for r in stocked.get("/warehouses/LON1/stock").json()}
    assert rows["ABC-1234"]["reserved"] == 0


def test_adjust_below_reserved(stocked):
    stocked.post("/reservations", json={"order_ref": "ORD-5", "warehouse_code": "LON1", "lines": [{"sku": "ABC-1234", "qty": 10}]})
    r = stocked.post("/stock/adjust", json={"warehouse_code": "LON1", "sku": "ABC-1234", "delta": -15})
    assert r.status_code == 409


def test_openapi_has_shared_types(client):
    spec = client.get("/openapi.json").json()["components"]["schemas"]
    assert spec["ProductIn"]["properties"]["unit_price"]["pattern"] == r"^\d+(\.\d{1,2})?$"
    assert spec["ProductIn"]["example"]["sku"] == "ABC-1234"
