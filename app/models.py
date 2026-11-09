"""ORM tables."""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db import Base


class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(Integer, primary_key=True)
    code = Column(String(8), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    line1 = Column(String(120), nullable=False)
    city = Column(String(80), nullable=False)
    postcode = Column(String(16), nullable=False)
    country = Column(String(2), nullable=False)
    stock = relationship("StockItem", back_populates="warehouse")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    sku = Column(String(8), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    stock = relationship("StockItem", back_populates="product")


class StockItem(Base):
    __tablename__ = "stock_items"
    __table_args__ = (UniqueConstraint("warehouse_id", "product_id"),)
    id = Column(Integer, primary_key=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    on_hand = Column(Integer, nullable=False, default=0)
    reserved = Column(Integer, nullable=False, default=0)
    warehouse = relationship("Warehouse", back_populates="stock")
    product = relationship("Product", back_populates="stock")
    reservations = relationship("Reservation", back_populates="stock_item")

    @property
    def available(self) -> int:
        return self.on_hand - self.reserved


class Reservation(Base):
    __tablename__ = "reservations"
    id = Column(Integer, primary_key=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)
    order_ref = Column(String(40), nullable=False)
    qty = Column(Integer, nullable=False)
    status = Column(String(16), nullable=False, default="active")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    stock_item = relationship("StockItem", back_populates="reservations")
