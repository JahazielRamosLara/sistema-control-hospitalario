from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from .config import settings
from .database import Base, engine
from .routers import atenciones, catalogos, pacientes, tablero


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Sistema de Control Hospitalario",
    version="1.0.0",
    description="Seguimiento clínico, estratificación de riesgo del paciente y generación de expediente.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrityError)
async def integridad(_: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={"detail": "El registro viola una restricción de unicidad o integridad (¿clave o cédula duplicada?)"},
    )


for r in (catalogos.router, pacientes.router, atenciones.router, tablero.router):
    app.include_router(r, prefix="/api")


@app.get("/api/salud", tags=["sistema"])
def salud():
    return {"estado": "ok"}
