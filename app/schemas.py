"""API schemas. Read models subclass orders_common.ORMModel (from_attributes) and are built from ORM rows."""
from datetime import datetime
from typing import List, Optional

from pydantic import field_validator, model_validator, ConfigDict, BaseModel, Field

from orders_common import Address, Money, ORMModel, Sku
from app.settings import settings
from typing_extensions import Annotated


class WarehouseIn(BaseModel):
    code: str = Field(..., pattern=r"^[A-Z]{2,4}\d{1,4}$")
    name: str = Field(..., min_length=1, max_length=120)
    address: Address


class WarehouseOut(ORMModel):
    id: int
    code: str
    name: str
    address: Address

    @model_validator(mode="before")
    @classmethod
    def address_from_columns(cls, data):
        # ORM rows store the address as flat columns. In v1 this got a dict-like view of the row;
        # in v2 (from_attributes) it gets the SQLAlchemy object itself, so read attributes.
        cols = ("line1", "city", "postcode", "country")
        if isinstance(data, dict):
            if "address" not in data and data.get("city") is not None:
                data = {**data, "address": {k: data.get(k) for k in cols}}
            return data
        if getattr(data, "city", None) is not None and not hasattr(data, "address"):
            return {**{f: getattr(data, f) for f in cls.model_fields if f != "address"},
                    "address": {k: getattr(data, k) for k in cols}}
        return data


class ProductIn(BaseModel):
    sku: Sku
    name: str = Field(..., min_length=1, max_length=200)
    unit_price: Money
    model_config = ConfigDict(json_schema_extra={"example": {"sku": "ABC-1234", "name": "Widget", "unit_price": "19.99"}})


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

    @field_validator("delta")
    @classmethod
    def not_zero(cls, v):
        if v == 0:
            raise ValueError("delta must not be 0")
        return v


class ReservationLine(BaseModel):
    sku: Sku
    qty: Annotated[int, Field(gt=0)]

    @field_validator("qty")
    @classmethod
    def under_limit(cls, v):
        if v > settings.max_reservation_qty:
            raise ValueError(f"at most {settings.max_reservation_qty} per line")
        return v


class ReservationRequest(BaseModel):
    order_ref: str = Field(..., min_length=3, max_length=40)
    warehouse_code: str
    lines: Annotated[List[ReservationLine], Field(min_length=1, max_length=50)]

    # v1 root_validator(skip_on_failure=True) -> v2 "after" validator: runs once every field is valid
    @model_validator(mode="after")
    def unique_skus(self):
        skus = [l.sku for l in self.lines]
        if len(skus) != len(set(skus)):
            raise ValueError("each sku may appear once")
        return self


class ReservationOut(ORMModel):
    id: int
    order_ref: str
    qty: int
    status: str
    created_at: datetime


class ReservationResult(BaseModel):
    order_ref: str
    reservations: List[ReservationOut]
