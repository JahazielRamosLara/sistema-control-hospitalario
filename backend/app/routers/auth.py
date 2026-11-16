"""Inicio y cierre de sesión, usuario actual y cambio de contraseña."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import seguridad as seg
from ..config import settings
from ..constantes import ROLES
from ..database import get_db
from ..models import Usuario

router = APIRouter(prefix="/auth", tags=["autenticación"])

MENSAJE_FALLO = "Usuario o contraseña incorrectos (tras varios intentos la cuenta se bloquea temporalmente)"


class LoginIn(BaseModel):
    usuario: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=128)


class CambioPasswordIn(BaseModel):
    actual: str = Field(min_length=1, max_length=128)
    nueva: str = Field(min_length=1, max_length=128)


class UsuarioActual(BaseModel):
    id: int
    usuario: str
    nombre: str
    rol: str
    rol_nombre: str
    debe_cambiar_password: bool


def yo(u: Usuario) -> UsuarioActual:
    return UsuarioActual(id=u.id, usuario=u.usuario, nombre=u.nombre, rol=u.rol, rol_nombre=ROLES.get(u.rol, u.rol),
                         debe_cambiar_password=u.debe_cambiar_password)


@router.post("/login", response_model=UsuarioActual)
def login(datos: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = seg.ip_cliente(request)
    nombre = datos.usuario.strip().lower()
    if seg.ip_excedida(ip):
        seg.registrar(db, nombre, "login_ip_limitada", False, ip)
        db.commit()
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Demasiados intentos desde este equipo; espera unos minutos")

    u = db.scalar(select(Usuario).where(func.lower(Usuario.usuario) == nombre))
    t = seg.ahora()
    bloqueado = u is not None and u.bloqueado_hasta is not None and seg._utc(u.bloqueado_hasta) > t
    # Se verifica siempre (también con usuario inexistente o bloqueado) para no filtrar información por tiempos.
    correcto = seg.verificar_password(u, datos.password)

    if not correcto or bloqueado or not u.activo:
        seg.anotar_fallo_ip(ip)
        evento = "login_bloqueado" if bloqueado else "login_fallido"
        if u is not None and not bloqueado:
            u.intentos_fallidos += 1
            if u.intentos_fallidos >= settings.max_intentos_login:
                u.bloqueado_hasta = t + timedelta(minutes=settings.bloqueo_min)
                u.intentos_fallidos = 0
                evento = "cuenta_bloqueada"
        seg.registrar(db, nombre, evento, False, ip)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, MENSAJE_FALLO)

    u.intentos_fallidos = 0
    u.bloqueado_hasta = None
    u.ultimo_acceso = t
    if seg._ph.check_needs_rehash(u.password_hash):
        u.password_hash = seg.hash_password(datos.password)
    # Una sesión nueva en cada login (evita fijación de sesión): se descarta la cookie que trajera.
    seg.cerrar_sesion(db, request, response)
    seg.abrir_sesion(db, response, u, request)
    seg.registrar(db, u.usuario, "login", True, ip)
    db.commit()
    return yo(u)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(seg.COOKIE)
    if token:
        try:
            u = seg.usuario_sesion(request, db)
            seg.registrar(db, u.usuario, "logout", True, seg.ip_cliente(request))
        except HTTPException:
            pass
    seg.cerrar_sesion(db, request, response)
    db.commit()


@router.get("/me", response_model=UsuarioActual)
def me(u: Usuario = Depends(seg.usuario_sesion)):
    return yo(u)


@router.post("/cambiar-password", response_model=UsuarioActual)
def cambiar_password(datos: CambioPasswordIn, request: Request, u: Usuario = Depends(seg.usuario_sesion),
                     db: Session = Depends(get_db)):
    ip = seg.ip_cliente(request)
    if not seg.verificar_password(u, datos.actual):
        seg.registrar(db, u.usuario, "cambio_password", False, ip)
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña actual no es correcta")
    if datos.nueva == datos.actual:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "La nueva contraseña debe ser distinta de la actual")
    seg.validar_politica(datos.nueva, u.usuario)
    u.password_hash = seg.hash_password(datos.nueva)
    u.debe_cambiar_password = False
    # Se cierran las demás sesiones abiertas de este usuario
    seg.revocar_sesiones(db, u.id, excepto_token=request.cookies.get(seg.COOKIE))
    seg.registrar(db, u.usuario, "cambio_password", True, ip)
    db.commit()
    return yo(u)
