from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict

class StatusesSettable(str, Enum):
    pending = 'pending'
    confirmed = 'confirmed'
    shipped = 'shipped'
    delivered = 'delivered'
    cancelled = 'cancelled'

class SalesOrderCreate(BaseModel):
    status: str = 'pending'
    total: Decimal = Field(..., ge=0, decimal_places=2)

class SalesOrderItemCreate(BaseModel):
    sales_order_id: int = int
    product_id: int = int
    quantity: int = int
    unit_price: Decimal = Field(..., ge=0, decimal_places=2)
    discount_total: Decimal = Field(default=0, ge=0, decimal_places=2)

class SalesOrderStatusUpdate(BaseModel):
    status: StatusesSettable

class SalesOrderItemUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=0)
    discount_total: Decimal | None = Field(default=None, ge=0, decimal_places=2)

class SalesOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: str
    total: Decimal
    created_at: datetime

class SalesOrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sales_order_id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    discount_total: Decimal
    struck_out: bool