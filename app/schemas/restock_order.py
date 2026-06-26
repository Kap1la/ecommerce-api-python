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

class RestockOrderCreate(BaseModel):
    status: str = 'pending'

class RestockOrderItemCreate(BaseModel):
    purchase_order_id: int = int
    product_id: int = int
    quantity: int = int

class RestockOrderStatusUpdate(BaseModel):
    status: StatusesSettable

class RestockOrderItemUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=0)

class RestockOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: str
    created_at: datetime

class RestockOrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purchase_order_id: int
    product_id: int
    quantity: int
    struck_out: bool