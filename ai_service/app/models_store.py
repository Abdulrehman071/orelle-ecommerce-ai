"""READ-ONLY mappings onto the tables Django already created (names follow Django's `<app>_<model>`).

Only the columns the assistant needs are mapped. Django stores UUID primary keys as 32-char hex on
SQLite, which SQLAlchemy's `Uuid` type reads/writes natively.
"""
from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class StoreBase(DeclarativeBase):
    pass


class Category(StoreBase):
    __tablename__ = "catalog_category"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(10))


class Size(StoreBase):
    __tablename__ = "catalog_size"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(10))
    order: Mapped[int] = mapped_column(Integer, default=0)


class Color(StoreBase):
    __tablename__ = "catalog_color"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))


class Product(StoreBase):
    __tablename__ = "catalog_product"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220))
    sku: Mapped[str] = mapped_column(String(50))
    category_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("catalog_category.id"))
    description: Mapped[str] = mapped_column(Text, default="")
    material: Mapped[str] = mapped_column(String(200), default="")
    fit: Mapped[str] = mapped_column(String(10), default="regular")
    care_instructions: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_new_arrival: Mapped[bool] = mapped_column(Boolean, default=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)

    category: Mapped[Category] = relationship(lazy="joined")
    variants: Mapped[list["Variant"]] = relationship(back_populates="product")

    @property
    def current_price(self) -> Decimal:
        return self.sale_price if self.sale_price else self.price

    @property
    def discount_percent(self) -> int:
        if self.sale_price and self.price > 0:
            return round((1 - (self.sale_price / self.price)) * 100)
        return 0


class Variant(StoreBase):
    __tablename__ = "catalog_productvariant"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("catalog_product.id"))
    size_id: Mapped[int] = mapped_column(Integer, ForeignKey("catalog_size.id"))
    color_id: Mapped[int] = mapped_column(Integer, ForeignKey("catalog_color.id"))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    variant_sku: Mapped[str] = mapped_column(String(60))

    product: Mapped[Product] = relationship(back_populates="variants")
    size: Mapped[Size] = relationship(lazy="joined")
    color: Mapped[Color] = relationship(lazy="joined")


class User(StoreBase):
    __tablename__ = "accounts_user"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String(254))
    role: Mapped[str] = mapped_column(String(10), default="customer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)


class Token(StoreBase):
    """Django REST Framework auth token (what the React app sends as `Authorization: Token ...`)."""
    __tablename__ = "authtoken_token"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts_user.id"))


class Order(StoreBase):
    __tablename__ = "orders_order"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    order_number: Mapped[str] = mapped_column(String(20))
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("accounts_user.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(254))
    delivery_method: Mapped[str] = mapped_column(String(10))
    payment_method: Mapped[str] = mapped_column(String(15))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    shipping_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    coupon_code: Mapped[str] = mapped_column(String(30), default="")
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime)  # stored as naive UTC by Django (USE_TZ=True)

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
    shipment: Mapped["Shipment | None"] = relationship(uselist=False)


class OrderItem(StoreBase):
    __tablename__ = "orders_orderitem"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("orders_order.id"))
    variant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("catalog_productvariant.id"))
    product_name: Mapped[str] = mapped_column(String(200))
    size_label: Mapped[str] = mapped_column(String(10))
    color_name: Mapped[str] = mapped_column(String(50))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    quantity: Mapped[int] = mapped_column(Integer)

    order: Mapped[Order] = relationship(back_populates="items")
    variant: Mapped[Variant] = relationship()


class Shipment(StoreBase):
    __tablename__ = "orders_shipment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("orders_order.id"))
    carrier: Mapped[str] = mapped_column(String(100), default="")
    tracking_number: Mapped[str] = mapped_column(String(100), default="")
    shipped_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    estimated_delivery_days: Mapped[str] = mapped_column(String(20), default="5-7")


class Coupon(StoreBase):
    __tablename__ = "promotions_coupon"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    code: Mapped[str] = mapped_column(String(30))
    discount_type: Mapped[str] = mapped_column(String(10))
    value: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    min_order_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    max_discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    start_date: Mapped[dt.datetime] = mapped_column(DateTime)
    expiry_date: Mapped[dt.datetime] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
