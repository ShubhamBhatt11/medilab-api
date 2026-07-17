from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Laboratory, LabTest, User
from app.schemas import LaboratoryIn, LaboratoryOut, LabTestIn, LabTestOut

router = APIRouter(tags=["catalog"])


@router.post("/laboratories", response_model=LaboratoryOut, status_code=status.HTTP_201_CREATED)
async def create_laboratory(
    body: LaboratoryIn,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    lab = Laboratory(**body.model_dump())
    db.add(lab)
    await db.commit()
    await db.refresh(lab)
    return lab


@router.get("/laboratories", response_model=list[LaboratoryOut])
async def list_laboratories(
    city: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Laboratory).order_by(Laboratory.id).limit(limit).offset(offset)
    if city:
        stmt = stmt.where(Laboratory.city.ilike(city))
    return (await db.scalars(stmt)).all()


@router.post(
    "/laboratories/{laboratory_id}/tests",
    response_model=LabTestOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_test(
    laboratory_id: int,
    body: LabTestIn,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if await db.get(Laboratory, laboratory_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Laboratory not found")

    test = LabTest(laboratory_id=laboratory_id, **body.model_dump())
    db.add(test)
    try:
        await db.commit()
    except IntegrityError:
        # uq_lab_test_code — the DB is the source of truth for uniqueness,
        # so a concurrent duplicate insert fails here, not silently.
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Test code already exists for this lab")
    await db.refresh(test)
    return test


@router.get("/laboratories/{laboratory_id}/tests", response_model=list[LabTestOut])
async def list_tests(
    laboratory_id: int,
    q: str | None = Query(default=None, description="Filter by test name"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(LabTest)
        .where(LabTest.laboratory_id == laboratory_id)
        .order_by(LabTest.name)
        .limit(limit)
        .offset(offset)
    )
    if q:
        stmt = stmt.where(LabTest.name.ilike(f"%{q}%"))
    return (await db.scalars(stmt)).all()
