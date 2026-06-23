from sqlalchemy import String, Numeric, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid

class Order(Base):
    __tablename__ = "orders"

    id      : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    status  : Mapped[str]       = mapped_column(String(20), default="pending")
    total   : Mapped[float]     = mapped_column(Numeric(10, 2))

    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", lazy="selectin")


class OrderItem(Base):
    __tablename__ = "order_items"

    id         : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id   : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"))
    product_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    quantity   : Mapped[int]       = mapped_column()
    unit_price : Mapped[float]     = mapped_column(Numeric(10, 2))

    order: Mapped["Order"] = relationship("Order", back_populates="items")