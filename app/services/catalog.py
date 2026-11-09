from typing import List, Tuple

from sqlalchemy.orm import Session

from app import models, schemas


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


def create_warehouse(db: Session, data: schemas.WarehouseIn) -> models.Warehouse:
    if db.query(models.Warehouse).filter_by(code=data.code).first():
        raise Conflict(f"warehouse {data.code} exists")
    row = models.Warehouse(code=data.code, name=data.name, **data.address.model_dump(exclude={"line2"}))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_warehouse(db: Session, code: str) -> models.Warehouse:
    row = db.query(models.Warehouse).filter_by(code=code).first()
    if row is None:
        raise NotFound(f"warehouse {code}")
    return row


def create_product(db: Session, data: schemas.ProductIn) -> models.Product:
    if db.query(models.Product).filter_by(sku=data.sku).first():
        raise Conflict(f"product {data.sku} exists")
    row = models.Product(**data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_product(db: Session, sku: str) -> models.Product:
    row = db.query(models.Product).filter_by(sku=sku.upper()).first()
    if row is None:
        raise NotFound(f"product {sku}")
    return row


def update_product(db: Session, sku: str, data: schemas.ProductUpdate) -> models.Product:
    row = get_product(db, sku)
    current = schemas.ProductOut.model_validate(row)
    merged = current.model_copy(update=data.model_dump(exclude_unset=True))
    row.name, row.unit_price = merged.name, merged.unit_price
    db.commit()
    db.refresh(row)
    return row


def list_products(db: Session, offset: int, limit: int) -> Tuple[List[models.Product], int]:
    q = db.query(models.Product).order_by(models.Product.sku)
    return q.offset(offset).limit(limit).all(), q.count()
