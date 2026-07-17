"""Pydantic v2 schemas — request validation + response serialization.

The FastAPI equivalent of Joi/Zod validators AND your response DTO mapping
in one place. from_attributes=True lets a response model be built straight
from a SQLAlchemy ORM object (like calling .toJSON() on a Mongoose doc,
but the shape is an explicit, documented contract).
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import BookingStatus, CollectionMode


# ---- auth ----
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=1, max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str


# ---- catalog ----
class LaboratoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=400)


class LaboratoryOut(LaboratoryIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class LabTestIn(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    sample_type: str = Field(min_length=1, max_length=60)


class LabTestOut(LabTestIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    laboratory_id: int


# ---- slots & bookings ----
class SlotIn(BaseModel):
    starts_at: datetime
    capacity: int = Field(default=1, ge=1, le=100)


class SlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    laboratory_id: int
    starts_at: datetime
    capacity: int
    booked_count: int


class BookingIn(BaseModel):
    slot_id: int
    lab_test_id: int
    collection_mode: CollectionMode


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slot_id: int
    lab_test_id: int
    status: BookingStatus
    collection_mode: CollectionMode
    created_at: datetime
