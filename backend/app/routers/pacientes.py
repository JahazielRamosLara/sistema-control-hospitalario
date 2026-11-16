"""BASE_PACIENTES + BUSCAR_PACIENTE + EXPEDIENTE_PACIENTE."""
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..seguridad import requiere
from ..models import Atencion, Medico, Paciente, Servicio
from ..pdf import expediente_pdf
from ..riesgo import atenciones_por_paciente, eventos_por_paciente, tabla
from ..schemas import PacienteDetalle, PacienteIn, PacienteOut
from ..serializacion import atencion_out, paciente_out

router = APIRouter(prefix="/pacientes", tags=["pacientes"])

_CARGA = (selectinload(Paciente.servicio), selectinload(Paciente.medico_tratante))


def siguiente_expediente(db: Session) -> str:
    """Siguiente consecutivo con formato EXP-0000 (macro NuevoPaciente)."""
    mayor = 0
    for exp in db.scalars(select(Paciente.expediente)):
        m = re.fullmatch(r"EXP-(\d+)", exp)
        if m:
            mayor = max(mayor, int(m.group(1)))
    return f"EXP-{mayor + 1:04d}"


def _validar_refs(db: Session, datos: PacienteIn):
    if datos.servicio_id is not None and db.get(Servicio, datos.servicio_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "El servicio indicado no existe")
    if datos.medico_tratante_id is not None and db.get(Medico, datos.medico_tratante_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "El médico tratante indicado no existe")


def _cargar(db: Session, paciente_id: int) -> Paciente:
    p = db.scalar(select(Paciente).options(*_CARGA).where(Paciente.id == paciente_id))
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paciente no encontrado")
    return p


def _detalle(db: Session, p: Paciente) -> PacienteDetalle:
    umbrales = tabla(db)
    atenciones = db.scalars(
        select(Atencion)
        .options(selectinload(Atencion.tipo_atencion), selectinload(Atencion.medico))
        .where(Atencion.paciente_id == p.id)
        .order_by(Atencion.fecha, Atencion.id)
    ).all()
    eventos = sum(1 for a in atenciones if a.evento_critico)
    base = paciente_out(p, eventos, umbrales, len(atenciones))
    return PacienteDetalle(
        **base.model_dump(),
        atenciones=[atencion_out(a, eventos, umbrales) for a in atenciones],
        ultima_atencion=max((a.fecha for a in atenciones), default=None),
    )


@router.get("", response_model=list[PacienteOut])
def listar(
    q: str | None = Query(None, description="Busca por expediente o nombre"),
    servicio_id: int | None = None,
    nivel: str | None = Query(None, description="Filtra por nivel de riesgo"),
    solo_alerta: bool = False,
    db: Session = Depends(get_db),
):
    consulta = select(Paciente).options(*_CARGA).order_by(Paciente.expediente)
    if q:
        patron = f"%{q.strip()}%"
        consulta = consulta.where(or_(Paciente.expediente.ilike(patron), Paciente.nombre.ilike(patron)))
    if servicio_id is not None:
        consulta = consulta.where(Paciente.servicio_id == servicio_id)
    pacientes = db.scalars(consulta).all()
    umbrales = tabla(db)
    eventos = eventos_por_paciente(db)
    totales = atenciones_por_paciente(db)
    salida = [paciente_out(p, eventos.get(p.id, 0), umbrales, totales.get(p.id, 0)) for p in pacientes]
    if nivel:
        salida = [p for p in salida if p.riesgo.nivel == nivel]
    if solo_alerta:
        salida = [p for p in salida if p.riesgo.alerta]
    return salida


@router.get("/siguiente-expediente")
def obtener_siguiente_expediente(db: Session = Depends(get_db)):
    return {"expediente": siguiente_expediente(db)}


@router.get("/expediente/{expediente}", response_model=PacienteDetalle)
def buscar_por_expediente(expediente: str, db: Session = Depends(get_db)):
    p = db.scalar(
        select(Paciente).options(*_CARGA).where(func.upper(Paciente.expediente) == expediente.strip().upper())
    )
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"El expediente {expediente} no existe")
    return _detalle(db, p)


@router.get("/{paciente_id}", response_model=PacienteDetalle)
def obtener(paciente_id: int, db: Session = Depends(get_db)):
    return _detalle(db, _cargar(db, paciente_id))


@router.post("", response_model=PacienteOut, status_code=201, dependencies=[Depends(requiere("admision"))])
def crear(datos: PacienteIn, db: Session = Depends(get_db)):
    _validar_refs(db, datos)
    for _ in range(3):  # reintenta si otro usuario tomó el mismo consecutivo
        p = Paciente(expediente=siguiente_expediente(db), **datos.model_dump())
        db.add(p)
        try:
            db.commit()
            break
        except IntegrityError:
            db.rollback()
    else:
        raise HTTPException(status.HTTP_409_CONFLICT, "No se pudo asignar número de expediente; reintenta")
    p = _cargar(db, p.id)
    return paciente_out(p, 0, tabla(db), 0)


@router.put("/{paciente_id}", response_model=PacienteOut, dependencies=[Depends(requiere("admision"))])
def editar(paciente_id: int, datos: PacienteIn, db: Session = Depends(get_db)):
    p = _cargar(db, paciente_id)
    _validar_refs(db, datos)
    for k, v in datos.model_dump().items():
        setattr(p, k, v)
    db.commit()
    p = _cargar(db, paciente_id)
    eventos = eventos_por_paciente(db, [p.id]).get(p.id, 0)
    total = atenciones_por_paciente(db, [p.id]).get(p.id, 0)
    return paciente_out(p, eventos, tabla(db), total)


@router.delete("/{paciente_id}", status_code=204, dependencies=[Depends(requiere())])
def eliminar(paciente_id: int, db: Session = Depends(get_db)):
    p = _cargar(db, paciente_id)
    db.delete(p)
    db.commit()


@router.get("/{paciente_id}/expediente.pdf")
def descargar_expediente(paciente_id: int, db: Session = Depends(get_db)):
    detalle = _detalle(db, _cargar(db, paciente_id))
    contenido = expediente_pdf(detalle)
    nombre = f"EXPEDIENTE_{detalle.expediente}.pdf"
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{nombre}"'},
    )
