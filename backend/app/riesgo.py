"""Motor de estratificación de riesgo (equivalente a COUNTIFS + BUSCARV aproximado del libro original)."""
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Atencion, UmbralRiesgo


@dataclass
class Nivel:
    nivel: str
    semaforo: str
    accion: str | None
    alerta: bool


SIN_TABLA = Nivel("SIN CLASIFICAR", "Gris", None, False)


def tabla(db: Session) -> list[UmbralRiesgo]:
    return list(db.scalars(select(UmbralRiesgo).order_by(UmbralRiesgo.eventos_minimos)))


def clasificar(eventos: int, umbrales: list[UmbralRiesgo]) -> Nivel:
    """Devuelve el último umbral cuyo mínimo no supera `eventos` (umbrales ordenados de menor a mayor)."""
    elegido = None
    for u in umbrales:
        if u.eventos_minimos <= eventos:
            elegido = u
        else:
            break
    if elegido is None:
        return SIN_TABLA
    return Nivel(elegido.nivel, elegido.semaforo, elegido.accion, elegido.alerta)


def eventos_por_paciente(db: Session, paciente_ids: list[int] | None = None) -> dict[int, int]:
    """Acumulado histórico de eventos críticos por paciente."""
    q = (
        select(Atencion.paciente_id, func.count())
        .where(Atencion.evento_critico.is_(True))
        .group_by(Atencion.paciente_id)
    )
    if paciente_ids is not None:
        q = q.where(Atencion.paciente_id.in_(paciente_ids))
    return {pid: n for pid, n in db.execute(q)}


def atenciones_por_paciente(db: Session, paciente_ids: list[int] | None = None) -> dict[int, int]:
    q = select(Atencion.paciente_id, func.count()).group_by(Atencion.paciente_id)
    if paciente_ids is not None:
        q = q.where(Atencion.paciente_id.in_(paciente_ids))
    return {pid: n for pid, n in db.execute(q)}
