"""App entrypoint — wires routers, like your index.js/app.js in Express.

Run locally:  uvicorn app.main:app --reload
Docs:         http://localhost:8000/docs  (generated from the Pydantic models)
"""
from fastapi import FastAPI

from app.routers import auth, bookings, catalog

app = FastAPI(
    title="MediLab API",
    version="0.1.0",
    description=(
        "Lab-test booking backend — a FastAPI + PostgreSQL port of a lab-booking "
        "microservice originally shipped commercially on Node.js + MongoDB."
    ),
)

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(bookings.router)


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok"}
