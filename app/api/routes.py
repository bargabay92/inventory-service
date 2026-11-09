from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from orders_common import Page
from app import schemas
from app.db import get_session
from app.services import catalog, stock
from app.services.catalog import Conflict, NotFound

router = APIRouter()


def guard(fn, *args):
    try:
        return fn(*args)
    except NotFound as e:
        raise HTTPException(404, str(e))
    except Conflict as e:
        raise HTTPException(409, str(e))


@router.post("/warehouses", response_model=schemas.WarehouseOut, status_code=201)
def create_warehouse(body: schemas.WarehouseIn, db: Session = Depends(get_session)):
    return schemas.WarehouseOut.from_orm(guard(catalog.create_warehouse, db, body))


@router.get("/warehouses/{code}/stock", response_model=List[schemas.StockOut])
def warehouse_stock(code: str, db: Session = Depends(get_session)):
    return guard(stock.stock_for_warehouse, db, code)


@router.post("/products", response_model=schemas.ProductOut, status_code=201)
def create_product(body: schemas.ProductIn, db: Session = Depends(get_session)):
    return guard(catalog.create_product, db, body)


@router.get("/products", response_model=Page[schemas.ProductOut])
def list_products(offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=500),
                  db: Session = Depends(get_session)):
    rows, total = catalog.list_products(db, offset, limit)
    return Page[schemas.ProductOut](items=[schemas.ProductOut.from_orm(r) for r in rows], total=total,
                                    offset=offset, limit=limit)


@router.patch("/products/{sku}", response_model=schemas.ProductOut)
def update_product(sku: str, body: schemas.ProductUpdate, db: Session = Depends(get_session)):
    return guard(catalog.update_product, db, sku, body)


@router.post("/stock/adjust", response_model=schemas.StockOut)
def adjust_stock(body: schemas.StockAdjust, db: Session = Depends(get_session)):
    return schemas.StockOut.from_row(guard(stock.adjust, db, body))


@router.post("/reservations", response_model=schemas.ReservationResult, status_code=201)
def reserve(body: schemas.ReservationRequest, db: Session = Depends(get_session)):
    return guard(stock.reserve, db, body)


@router.delete("/reservations/{order_ref}")
def release(order_ref: str, db: Session = Depends(get_session)):
    return {"released": guard(stock.release, db, order_ref)}
