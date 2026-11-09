from typing import List

from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from orders_common import EventType
from app import events, models, schemas
from app.services.catalog import Conflict, NotFound, get_product, get_warehouse
from app.settings import settings


def _stock_row(db: Session, warehouse_code: str, sku: str, create: bool = False) -> models.StockItem:
    wh, product = get_warehouse(db, warehouse_code), get_product(db, sku)
    row = db.query(models.StockItem).filter_by(warehouse_id=wh.id, product_id=product.id).first()
    if row is None:
        if not create:
            raise NotFound(f"no stock of {sku} in {warehouse_code}")
        row = models.StockItem(warehouse=wh, product=product, on_hand=0, reserved=0)
        db.add(row)
    return row


def adjust(db: Session, data: schemas.StockAdjust) -> models.StockItem:
    row = _stock_row(db, data.warehouse_code, data.sku, create=True)
    if row.on_hand + data.delta < row.reserved:
        raise Conflict("cannot go below reserved quantity")
    row.on_hand += data.delta
    db.commit()
    db.refresh(row)
    _maybe_low(row)
    return row


def stock_for_warehouse(db: Session, code: str) -> List[schemas.StockOut]:
    wh = get_warehouse(db, code)
    return [schemas.StockOut.from_row(r) for r in wh.stock]


def reserve(db: Session, req: schemas.ReservationRequest) -> schemas.ReservationResult:
    rows = [(line, _stock_row(db, req.warehouse_code, line.sku)) for line in req.lines]
    short = [f"{line.sku} (wanted {line.qty}, available {row.available})" for line, row in rows if row.available < line.qty]
    if short:
        raise Conflict("insufficient stock: " + ", ".join(short))
    created = []
    for line, row in rows:
        row.reserved += line.qty
        res = models.Reservation(stock_item=row, order_ref=req.order_ref, qty=line.qty)
        db.add(res)
        created.append(res)
    db.commit()
    for (line, row), res in zip(rows, created):
        db.refresh(res)
        events.publish(EventType.STOCK_RESERVED, order_ref=req.order_ref, sku=line.sku, qty=line.qty,
                       warehouse=req.warehouse_code)
        _maybe_low(row)
    out = TypeAdapter(List[schemas.ReservationOut]).validate_python(created, from_attributes=True)
    return schemas.ReservationResult(order_ref=req.order_ref, reservations=out)


def release(db: Session, order_ref: str) -> int:
    active = db.query(models.Reservation).filter_by(order_ref=order_ref, status="active").all()
    if not active:
        raise NotFound(f"no active reservations for {order_ref}")
    for res in active:
        res.status = "released"
        res.stock_item.reserved -= res.qty
        events.publish(EventType.STOCK_RELEASED, order_ref=order_ref, qty=res.qty)
    db.commit()
    return len(active)


def _maybe_low(row: models.StockItem) -> None:
    if row.available <= settings.low_stock_threshold:
        events.publish(EventType.STOCK_LOW, sku=row.product.sku, warehouse=row.warehouse.code,
                       available=row.available)
