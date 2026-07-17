"""Slots and the transactional booking flow.

The core concurrency lesson of this project: in MongoDB you'd guard slot
capacity with an atomic findOneAndUpdate filter; in PostgreSQL you take a
row lock inside a transaction (SELECT ... FOR UPDATE). Two concurrent
requests for the last seat serialize on the lock — the second one re-reads
the incremented booked_count and gets a 409, never an overbooking.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Booking, BookingStatus, Laboratory, LabTest, Slot, User
from app.schemas import BookingIn, BookingOut, SlotIn, SlotOut

router = APIRouter(tags=["bookings"])


@router.post(
    "/laboratories/{laboratory_id}/slots",
    response_model=SlotOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_slot(
    laboratory_id: int,
    body: SlotIn,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if await db.get(Laboratory, laboratory_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Laboratory not found")

    slot = Slot(laboratory_id=laboratory_id, **body.model_dump())
    db.add(slot)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Slot already exists at this time")
    await db.refresh(slot)
    return slot


@router.get("/laboratories/{laboratory_id}/slots", response_model=list[SlotOut])
async def list_slots(
    laboratory_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Slot)
        .where(Slot.laboratory_id == laboratory_id)
        .order_by(Slot.starts_at)
        .limit(limit)
        .offset(offset)
    )
    return (await db.scalars(stmt)).all()


@router.post("/bookings", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
async def create_booking(
    body: BookingIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Row lock: concurrent bookings for this slot queue up here until commit.
    slot = await db.scalar(select(Slot).where(Slot.id == body.slot_id).with_for_update())
    if slot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Slot not found")
    if slot.booked_count >= slot.capacity:
        raise HTTPException(status.HTTP_409_CONFLICT, "Slot is fully booked")

    test = await db.scalar(
        select(LabTest).where(
            LabTest.id == body.lab_test_id, LabTest.laboratory_id == slot.laboratory_id
        )
    )
    if test is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test not offered by this laboratory")

    slot.booked_count += 1
    booking = Booking(
        user_id=user.id,
        slot_id=slot.id,
        lab_test_id=test.id,
        collection_mode=body.collection_mode,
    )
    db.add(booking)
    # Single commit = one atomic unit: counter increment + booking row
    # succeed or fail together, and the row lock releases here.
    await db.commit()
    await db.refresh(booking)
    return booking


@router.post("/bookings/{booking_id}/cancel", response_model=BookingOut)
async def cancel_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = await db.scalar(
        select(Booking).where(Booking.id == booking_id, Booking.user_id == user.id)
    )
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    if booking.status is BookingStatus.CANCELLED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Booking already cancelled")

    slot = await db.scalar(select(Slot).where(Slot.id == booking.slot_id).with_for_update())
    booking.status = BookingStatus.CANCELLED
    slot.booked_count -= 1
    await db.commit()
    await db.refresh(booking)
    return booking


@router.get("/bookings/me", response_model=list[BookingOut])
async def my_bookings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Booking).where(Booking.user_id == user.id).order_by(Booking.created_at.desc())
    return (await db.scalars(stmt)).all()
