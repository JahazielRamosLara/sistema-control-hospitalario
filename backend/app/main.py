from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import database
from .config import settings
from .database import Base
from .routers import atenciones, auth, catalogos, pacientes, tablero, usuarios
from .seguridad import crear_admin_inicial, usuario_actual


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=database.engine)
    with Session(database.engine) as db:
        crear_admin_inicial(db)
    yield


app = FastAPI(
    title="Sistema de Control Hospitalario",
    version="1.1.0",
    description="Seguimiento clínico, estratificación de riesgo del paciente y generación de expediente.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-Requested-With"],
)

METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS"}


@app.middleware("http")
async def proteccion_csrf_y_cabeceras(request: Request, call_next):
    # CSRF: un formulario o <img> de otro sitio no puede añadir cabeceras personalizadas; fetch() desde otro
    # origen sí podría, pero exige un preflight CORS que solo aceptamos para los orígenes configurados.
    if request.method not in METODOS_SEGUROS and request.url.path.startswith("/api/"):
        if request.headers.get("x-requested-with") != "fetch":
            return JSONResponse(status_code=403, content={"detail": "Petición rechazada (falta cabecera anti-CSRF)"})
    respuesta = await call_next(request)
    respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
    respuesta.headers.setdefault("Referrer-Policy", "same-origin")
    if request.url.path.startswith("/api/"):
        respuesta.headers.setdefault("Cache-Control", "no-store")  # datos clínicos: no cachear
    return respuesta


@app.exception_handler(IntegrityError)
async def integridad(_: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={"detail": "El registro viola una restricción de unicidad o integridad (¿clave o cédula duplicada?)"},
    )


app.include_router(auth.router, prefix="/api")
app.include_router(usuarios.router, prefix="/api")
# Todo lo demás exige sesión válida; las escrituras además exigen rol (ver cada router).
for r in (catalogos.router, pacientes.router, atenciones.router, tablero.router):
    app.include_router(r, prefix="/api", dependencies=[Depends(usuario_actual)])


@app.get("/api/salud", tags=["sistema"])
def salud():
    return {"estado": "ok"}
