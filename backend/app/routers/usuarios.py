"""Administración de usuarios y bitácora de accesos (solo administrador)."""
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import seguridad as seg
from ..constantes import ROLES
from ..database import get_db
from ..models import EventoAcceso, Usuario

router = APIRouter(prefix="/usuarios", tags=["usuarios"], dependencies=[Depends(seg.requiere("admin"))])


def _rol(v: str) -> str:
    if v not in ROLES:
        raise ValueError(f"Rol inválido. Opciones: {', '.join(ROLES)}")
    return v


class UsuarioCrear(BaseModel):
    usuario: str = Field(min_length=3, max_length=40)
    nombre: str = Field(min_length=3, max_length=160)
    rol: str

    @field_validator("usuario")
    @classmethod
    def _usuario(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.fullmatch(r"[a-z0-9._-]+", v):
            raise ValueError("Solo letras minúsculas, números, punto, guion y guion bajo")
        return v

    @field_validator("rol")
    @classmethod
    def _v_rol(cls, v: str) -> str:
        return _rol(v)


class UsuarioEditar(BaseModel):
    nombre: str = Field(min_length=3, max_length=160)
    rol: str
    activo: bool

    @field_validator("rol")
    @classmethod
    def _v_rol(cls, v: str) -> str:
        return _rol(v)


class UsuarioOut(BaseModel):
    id: int
    usuario: str
    nombre: str
    rol: str
    activo: bool
    debe_cambiar_password: bool
    bloqueado: bool
    ultimo_acceso: datetime | None


class PasswordTemporal(BaseModel):
    usuario: UsuarioOut
    password_temporal: str


class EventoOut(BaseModel):
    fecha: datetime
    usuario: str
    evento: str
    exito: bool
    ip: str | None


def _out(u: Usuario) -> UsuarioOut:
    bloq = u.bloqueado_hasta is not None and seg._utc(u.bloqueado_hasta) > seg.ahora()
    return UsuarioOut(id=u.id, usuario=u.usuario, nombre=u.nombre, rol=u.rol, activo=u.activo,
                      debe_cambiar_password=u.debe_cambiar_password, bloqueado=bloq,
                      ultimo_acceso=seg._utc(u.ultimo_acceso))


def _obtener(db: Session, usuario_id: int) -> Usuario:
    u = db.get(Usuario, usuario_id)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    return u


@router.get("/roles")
def roles():
    return ROLES


@router.get("", response_model=list[UsuarioOut])
def listar(db: Session = Depends(get_db)):
    return [_out(u) for u in db.scalars(select(Usuario).order_by(Usuario.usuario))]


@router.post("", response_model=PasswordTemporal, status_code=201)
def crear(datos: UsuarioCrear, request: Request, admin: Usuario = Depends(seg.usuario_actual),
          db: Session = Depends(get_db)):
    if db.scalar(select(Usuario).where(Usuario.usuario == datos.usuario)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese nombre de usuario ya existe")
    temporal = seg.password_aleatoria()
    u = Usuario(**datos.model_dump(), password_hash=seg.hash_password(temporal), debe_cambiar_password=True)
    db.add(u)
    seg.registrar(db, admin.usuario, f"alta_usuario:{datos.usuario}", True, seg.ip_cliente(request))
    db.commit()
    return PasswordTemporal(usuario=_out(u), password_temporal=temporal)


@router.put("/{usuario_id}", response_model=UsuarioOut)
def editar(usuario_id: int, datos: UsuarioEditar, admin: Usuario = Depends(seg.usuario_actual),
           db: Session = Depends(get_db)):
    u = _obtener(db, usuario_id)
    if u.id == admin.id and (datos.rol != "admin" or not datos.activo):
        raise HTTPException(status.HTTP_409_CONFLICT, "No puedes quitarte el rol de administrador ni desactivarte")
    u.nombre, u.rol, u.activo = datos.nombre, datos.rol, datos.activo
    if not u.activo:
        seg.revocar_sesiones(db, u.id)
    db.commit()
    return _out(u)


@router.post("/{usuario_id}/restablecer-password", response_model=PasswordTemporal)
def restablecer(usuario_id: int, request: Request, admin: Usuario = Depends(seg.usuario_actual),
                db: Session = Depends(get_db)):
    """Genera una contraseña temporal, desbloquea la cuenta y cierra sus sesiones."""
    u = _obtener(db, usuario_id)
    temporal = seg.password_aleatoria()
    u.password_hash = seg.hash_password(temporal)
    u.debe_cambiar_password = True
    u.intentos_fallidos = 0
    u.bloqueado_hasta = None
    seg.revocar_sesiones(db, u.id)
    seg.registrar(db, admin.usuario, f"restablecer_password:{u.usuario}", True, seg.ip_cliente(request))
    db.commit()
    return PasswordTemporal(usuario=_out(u), password_temporal=temporal)


@router.get("/accesos", response_model=list[EventoOut])
def accesos(limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)):
    eventos = db.scalars(select(EventoAcceso).order_by(EventoAcceso.fecha.desc(), EventoAcceso.id.desc()).limit(limit))
    return [EventoOut(fecha=seg._utc(e.fecha), usuario=e.usuario, evento=e.evento, exito=e.exito, ip=e.ip)
            for e in eventos]
