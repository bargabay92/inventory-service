"""API schemas. Read models subclass orders_common.ORMModel (orm_mode) and are built from ORM rows."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, conint, conlist, root_validator, validator

from orders_common import Address, Money, ORMModel, Sku
from app.settings import settings


class WarehouseIn(BaseModel):
    code: str = Field(..., regex=r"^[A-Z]{2,4}\d{1,4}$")
    name: str = Field(..., min_length=1, max_length=120)
    address: Address


class WarehouseOut(ORMModel):
    id: int
    code: str
    name: str
    address: Address

    @root_validator(pre=True)
    def address_from_columns(cls, values):
        # ORM rows store the address as flat columns
        if "address" not in values and values.get("city") is not None:
            values = dict(values)
            values["address"] = {k: values.get(k) for k in ("line1", "city", "postcode", "country")}
        return values


class ProductIn(BaseModel):
    sku: Sku
    name: str = Field(..., min_length=1, max_length=200)
    unit_price: Money

    class Config:
        schema_extra = {"example": {"sku": "ABC-1234", "name": "Widget", "unit_price": "19.99"}}


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    unit_price: Optional[Money] = None


class ProductOut(ORMModel):
    id: int
    sku: Sku
    name: str
    unit_price: Money


class StockOut(ORMModel):
    warehouse_code: str
    sku: Sku
    on_hand: int
    reserved: int
    available: int

    @classmethod
    def from_row(cls, row) -> "StockOut":
        return cls(warehouse_code=row.warehouse.code, sku=row.product.sku, on_hand=row.on_hand,
                   reserved=row.reserved, available=row.available)


class StockAdjust(BaseModel):
    warehouse_code: str
    sku: Sku
    delta: int

    @validator("delta")
    def not_zero(cls, v):
        if v == 0:
            raise ValueError("delta must not be 0")
        return v


class ReservationLine(BaseModel):
    sku: Sku
    qty: conint(gt=0)

    @validator("qty")
    def under_limit(cls, v):
        if v > settings.max_reservation_qty:
            raise ValueError(f"at most {settings.max_reservation_qty} per line")
        return v


class ReservationRequest(BaseModel):
    order_ref: str = Field(..., min_length=3, max_length=40)
    warehouse_code: str
    lines: conlist(ReservationLine, min_items=1, max_items=50)

    @root_validator(skip_on_failure=True)
    def unique_skus(cls, values):
        skus = [l.sku for l in values["lines"]]
        if len(skus) != len(set(skus)):
            raise ValueError("each sku may appear once")
        return values


class ReservationOut(ORMModel):
    id: int
    order_ref: str
    qty: int
    status: str
    created_at: datetime


class ReservationResult(BaseModel):
    order_ref: str
    reservations: List[ReservationOut]
