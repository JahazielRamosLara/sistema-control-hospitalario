"""Autenticación y autorización.

- Contraseñas: Argon2id (argon2-cffi), con rehash automático si cambian los parámetros.
- Sesiones: token aleatorio de 256 bits en cookie HttpOnly + SameSite=Strict; en la base solo se guarda
  su SHA-256, de modo que una copia de la base no permite suplantar sesiones. Expiran por inactividad
  y por duración máxima, y se revocan al cerrar sesión, cambiar contraseña o desactivar al usuario.
- Fuerza bruta: bloqueo temporal de la cuenta tras N fallos y límite de intentos por IP.
- CSRF: toda petición que modifica datos debe traer la cabecera X-Requested-With (ver main.py), que un
  formulario de otro sitio no puede enviar; además la cookie es SameSite=Strict.
"""
import hashlib
import logging
import secrets
import string
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import EventoAcceso, Sesion, Usuario

log = logging.getLogger("seguridad")

COOKIE = "ch_sesion"
_ph = PasswordHasher()  # Argon2id con los parámetros recomendados por la librería
_HASH_FALSO = _ph.hash(secrets.token_hex(16))  # para igualar tiempos cuando el usuario no existe


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def _utc(d: datetime | None) -> datetime | None:
    """SQLite devuelve fechas sin zona; se interpretan como UTC."""
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


# ------------------------------------------------------------ Contraseñas
def hash_password(password: str) -> str:
    return _ph.hash(password)


def verificar_password(usuario: Usuario | None, password: str) -> bool:
    try:
        _ph.verify(usuario.password_hash if usuario else _HASH_FALSO, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    return usuario is not None


def validar_politica(password: str, usuario: str | None = None) -> None:
    """Longitud mínima de 10, con letras y números, y distinta del nombre de usuario."""
    errores = []
    if len(password) < 10:
        errores.append("al menos 10 caracteres")
    if len(password) > 128:
        errores.append("como máximo 128 caracteres")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        errores.append("letras y números")
    if usuario and usuario.lower() in password.lower():
        errores.append("no contener el nombre de usuario")
    if errores:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "La contraseña debe tener " + ", ".join(errores))


def password_aleatoria(n: int = 16) -> str:
    alfabeto = string.ascii_letters + string.digits
    while True:
        p = "".join(secrets.choice(alfabeto) for _ in range(n))
        if any(c.isdigit() for c in p) and any(c.isalpha() for c in p):
            return p


# ------------------------------------------------------------ Bitácora
def registrar(db: Session, usuario: str, evento: str, exito: bool, ip: str | None):
    db.add(EventoAcceso(usuario=usuario[:40], evento=evento, exito=exito, ip=ip))


def ip_cliente(request: Request) -> str | None:
    return request.client.host if request.client else None


# ------------------------------------------------------------ Límite por IP (en memoria)
_intentos_ip: dict[str, deque] = defaultdict(deque)


def ip_excedida(ip: str | None) -> bool:
    if not ip:
        return False
    ventana = settings.bloqueo_min * 60
    cola = _intentos_ip[ip]
    t = time.monotonic()
    while cola and t - cola[0] > ventana:
        cola.popleft()
    return len(cola) >= settings.max_intentos_por_ip


def anotar_fallo_ip(ip: str | None):
    if ip:
        _intentos_ip[ip].append(time.monotonic())


def reiniciar_limites():
    """Solo para pruebas."""
    _intentos_ip.clear()


# ------------------------------------------------------------ Sesiones
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def abrir_sesion(db: Session, response: Response, usuario: Usuario, request: Request) -> None:
    t = ahora()
    # Limpieza: sesiones vencidas de este usuario
    db.execute(delete(Sesion).where(Sesion.usuario_id == usuario.id, Sesion.expira_en < t))
    token = secrets.token_urlsafe(32)
    db.add(Sesion(
        token_hash=_hash_token(token),
        usuario_id=usuario.id,
        creada_en=t,
        expira_en=t + timedelta(hours=settings.sesion_horas),
        ultimo_uso=t,
        ip=ip_cliente(request),
        user_agent=(request.headers.get("user-agent") or "")[:255],
    ))
    response.set_cookie(
        COOKIE,
        token,
        max_age=settings.sesion_horas * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/api",
    )


def cerrar_sesion(db: Session, request: Request, response: Response) -> None:
    token = request.cookies.get(COOKIE)
    if token:
        db.execute(delete(Sesion).where(Sesion.token_hash == _hash_token(token)))
    response.delete_cookie(COOKIE, path="/api", httponly=True, secure=settings.cookie_secure, samesite="strict")


def revocar_sesiones(db: Session, usuario_id: int, excepto_token: str | None = None) -> None:
    q = delete(Sesion).where(Sesion.usuario_id == usuario_id)
    if excepto_token:
        q = q.where(Sesion.token_hash != _hash_token(excepto_token))
    db.execute(q)


def _no_autenticado(msg: str = "Sesión no válida o expirada") -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, msg)


def _usuario_de_sesion(request: Request, db: Session) -> Usuario:
    token = request.cookies.get(COOKIE)
    if not token:
        raise _no_autenticado("Inicia sesión para continuar")
    sesion = db.scalar(select(Sesion).where(Sesion.token_hash == _hash_token(token)))
    t = ahora()
    if sesion is None:
        raise _no_autenticado()
    inactiva = _utc(sesion.ultimo_uso) + timedelta(minutes=settings.sesion_inactividad_min) < t
    if _utc(sesion.expira_en) < t or inactiva:
        db.delete(sesion)
        db.commit()
        raise _no_autenticado("La sesión expiró; vuelve a iniciar sesión")
    usuario = sesion.usuario
    if not usuario.activo:
        db.delete(sesion)
        db.commit()
        raise _no_autenticado()
    if t - _utc(sesion.ultimo_uso) > timedelta(seconds=60):  # evita escribir en cada petición
        sesion.ultimo_uso = t
        db.commit()
    return usuario


def usuario_sesion(request: Request, db: Session = Depends(get_db)) -> Usuario:
    """Usuario autenticado, aunque deba cambiar su contraseña (para /auth/*)."""
    return _usuario_de_sesion(request, db)


def usuario_actual(usuario: Usuario = Depends(usuario_sesion)) -> Usuario:
    """Usuario autenticado y con contraseña definitiva: requisito de toda la API de datos."""
    if usuario.debe_cambiar_password:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Debes cambiar tu contraseña antes de continuar")
    return usuario


def requiere(*roles: str):
    """Dependencia que restringe una operación a ciertos roles (el administrador siempre puede)."""

    def _verificar(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol != "admin" and usuario.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Tu perfil no tiene permiso para esta operación")
        return usuario

    return _verificar


# ------------------------------------------------------------ Administrador inicial
def crear_admin_inicial(db: Session) -> None:
    if db.scalar(select(func.count(Usuario.id))):
        return
    generada = not settings.admin_password  # None o cadena vacía (compose pasa "" si no se define)
    password = settings.admin_password or password_aleatoria()
    db.add(Usuario(
        usuario=settings.admin_usuario,
        nombre="Administrador del sistema",
        rol="admin",
        password_hash=hash_password(password),
        debe_cambiar_password=True,
    ))
    db.commit()
    aviso = (
        "\n" + "=" * 64 +
        f"\n  Usuario administrador creado: {settings.admin_usuario}" +
        (f"\n  Contraseña temporal: {password}" if generada else "\n  Contraseña: la definida en ADMIN_PASSWORD") +
        "\n  Se pedirá cambiarla en el primer inicio de sesión." +
        "\n" + "=" * 64
    )
    print(aviso, flush=True)
