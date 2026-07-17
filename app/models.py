"""SQLAlchemy 2.0 models — the relational schema.

Coming from MongoDB: each Mapped[...] attribute is a real column with a DB
constraint behind it, and relationships are foreign keys the database
enforces — not references your app code promises to keep consistent.
The unique constraints below replace the "check-then-insert" races you
guard against manually in Mongo.
"""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    bookings: Mapped[list[Booking]] = relationship(back_populates="user")


class Laboratory(Base):
    __tablename__ = "laboratories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100), index=True)
    address: Mapped[str] = mapped_column(String(400))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tests: Mapped[list[LabTest]] = relationship(back_populates="laboratory")
    slots: Mapped[list[Slot]] = relationship(back_populates="laboratory")


class LabTest(Base):
    __tablename__ = "lab_tests"
    # A lab can't list the same test code twice — enforced by the DB, not app code.
    __table_args__ = (UniqueConstraint("laboratory_id", "code", name="uq_lab_test_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    laboratory_id: Mapped[int] = mapped_column(
        ForeignKey("laboratories.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    sample_type: Mapped[str] = mapped_column(String(60))

    laboratory: Mapped[Laboratory] = relationship(back_populates="tests")


class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = (UniqueConstraint("laboratory_id", "starts_at", name="uq_lab_slot_time"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    laboratory_id: Mapped[int] = mapped_column(
        ForeignKey("laboratories.id", ondelete="CASCADE"), index=True
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    capacity: Mapped[int] = mapped_column(default=1)
    booked_count: Mapped[int] = mapped_column(default=0)

    laboratory: Mapped[Laboratory] = relationship(back_populates="slots")
    bookings: Mapped[list[Booking]] = relationship(back_populates="slot")


class BookingStatus(enum.Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class CollectionMode(enum.Enum):
    HOME = "home"
    LAB = "lab"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("slots.id"), index=True)
    lab_test_id: Mapped[int] = mapped_column(ForeignKey("lab_tests.id"))
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status"), default=BookingStatus.CONFIRMED
    )
    collection_mode: Mapped[CollectionMode] = mapped_column(
        Enum(CollectionMode, name="collection_mode")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="bookings")
    slot: Mapped[Slot] = relationship(back_populates="bookings")
    lab_test: Mapped[LabTest] = relationship()
