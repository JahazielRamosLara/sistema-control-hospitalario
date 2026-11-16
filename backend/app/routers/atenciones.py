"""SEGUIMIENTO_CLINICO: bitácora de atenciones."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..seguridad import requiere
from ..models import Atencion, Medico, Paciente, TipoAtencion
from ..riesgo import eventos_por_paciente, tabla
from ..schemas import AtencionIn, AtencionOut, PaginaAtenciones
from ..serializacion import atencion_out

router = APIRouter(prefix="/atenciones", tags=["seguimiento clínico"])

_CARGA = (
    selectinload(Atencion.paciente).selectinload(Paciente.servicio),
    selectinload(Atencion.paciente).selectinload(Paciente.medico_tratante),
    selectinload(Atencion.tipo_atencion),
    selectinload(Atencion.medico),
)


def _salida(db: Session, atenciones: list[Atencion]) -> list[AtencionOut]:
    umbrales = tabla(db)
    eventos = eventos_por_paciente(db, list({a.paciente_id for a in atenciones}))
    return [atencion_out(a, eventos.get(a.paciente_id, 0), umbrales) for a in atenciones]


def _validar(db: Session, datos: AtencionIn):
    """Verificación de existencia (en el Excel la fila se resaltaba en ámbar)."""
    if db.get(Paciente, datos.paciente_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "El expediente indicado no existe")
    if db.get(TipoAtencion, datos.tipo_atencion_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "El tipo de atención no existe")
    if db.get(Medico, datos.medico_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "El médico indicado no existe")
    if datos.fecha and datos.fecha > date.today():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "La fecha de la atención no puede ser futura")


def _cargar(db: Session, atencion_id: int) -> Atencion:
    a = db.scalar(select(Atencion).options(*_CARGA).where(Atencion.id == atencion_id))
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Atención no encontrada")
    return a


@router.get("", response_model=PaginaAtenciones)
def listar(
    paciente_id: int | None = None,
    medico_id: int | None = None,
    servicio_id: int | None = None,
    turno: str | None = None,
    solo_criticos: bool = False,
    desde: date | None = None,
    hasta: date | None = None,
    q: str | None = Query(None, description="Texto en nota, plan, expediente o nombre"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    filtros = []
    if paciente_id is not None:
        filtros.append(Atencion.paciente_id == paciente_id)
    if medico_id is not None:
        filtros.append(Atencion.medico_id == medico_id)
    if servicio_id is not None:
        filtros.append(Paciente.servicio_id == servicio_id)
    if turno:
        filtros.append(Atencion.turno == turno)
    if solo_criticos:
        filtros.append(Atencion.evento_critico.is_(True))
    if desde:
        filtros.append(Atencion.fecha >= desde)
    if hasta:
        filtros.append(Atencion.fecha <= hasta)
    if q:
        patron = f"%{q.strip()}%"
        filtros.append(
            or_(
                Atencion.nota_clinica.ilike(patron),
                Atencion.plan_manejo.ilike(patron),
                Paciente.expediente.ilike(patron),
                Paciente.nombre.ilike(patron),
            )
        )
    base = select(Atencion).join(Atencion.paciente).where(*filtros)
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    atenciones = db.scalars(
        base.options(*_CARGA).order_by(Atencion.fecha.desc(), Atencion.id.desc()).limit(limit).offset(offset)
    ).all()
    return PaginaAtenciones(total=total, items=_salida(db, list(atenciones)))


@router.get("/{atencion_id}", response_model=AtencionOut)
def obtener(atencion_id: int, db: Session = Depends(get_db)):
    return _salida(db, [_cargar(db, atencion_id)])[0]


@router.post("", response_model=AtencionOut, status_code=201, dependencies=[Depends(requiere("medico"))])
def crear(datos: AtencionIn, db: Session = Depends(get_db)):
    _validar(db, datos)
    valores = datos.model_dump()
    valores["fecha"] = valores["fecha"] or date.today()  # sello de fecha automático
    a = Atencion(**valores)
    db.add(a)
    db.commit()
    return _salida(db, [_cargar(db, a.id)])[0]


@router.put("/{atencion_id}", response_model=AtencionOut, dependencies=[Depends(requiere("medico"))])
def editar(atencion_id: int, datos: AtencionIn, db: Session = Depends(get_db)):
    a = _cargar(db, atencion_id)
    _validar(db, datos)
    valores = datos.model_dump()
    valores["fecha"] = valores["fecha"] or a.fecha
    for k, v in valores.items():
        setattr(a, k, v)
    db.commit()
    db.expire_all()
    return _salida(db, [_cargar(db, atencion_id)])[0]


@router.delete("/{atencion_id}", status_code=204, dependencies=[Depends(requiere())])
def eliminar(atencion_id: int, db: Session = Depends(get_db)):
    a = _cargar(db, atencion_id)
    db.delete(a)
    db.commit()
