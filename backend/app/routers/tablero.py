"""MENU (indicadores en tiempo real) y TABLA_RIESGO."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..seguridad import requiere
from ..models import Atencion, Medico, Paciente, Servicio, UmbralRiesgo
from ..riesgo import atenciones_por_paciente, clasificar, eventos_por_paciente, tabla
from ..schemas import ConteoNivel, ConteoServicio, Indicadores, UmbralIn, UmbralOut
from ..serializacion import paciente_out

router = APIRouter(tags=["tablero"])


@router.get("/indicadores", response_model=Indicadores)
def indicadores(db: Session = Depends(get_db)):
    umbrales = tabla(db)
    eventos = eventos_por_paciente(db)
    totales = atenciones_por_paciente(db)
    pacientes = db.scalars(
        select(Paciente).options(selectinload(Paciente.servicio), selectinload(Paciente.medico_tratante))
    ).all()

    # Pacientes por nivel (cuenta pacientes, no atenciones)
    conteo = {u.nivel: 0 for u in umbrales}
    for p in pacientes:
        n = clasificar(eventos.get(p.id, 0), umbrales).nivel
        conteo[n] = conteo.get(n, 0) + 1
    semaforo = {u.nivel: u.semaforo for u in umbrales}
    distribucion = [ConteoNivel(nivel=k, semaforo=semaforo.get(k, "Gris"), pacientes=v) for k, v in conteo.items()]

    prioritarios = [
        paciente_out(p, eventos.get(p.id, 0), umbrales, totales.get(p.id, 0))
        for p in pacientes
        if clasificar(eventos.get(p.id, 0), umbrales).alerta
    ]
    prioritarios.sort(key=lambda p: (-p.riesgo.eventos_criticos, p.expediente))

    por_servicio = db.execute(
        select(
            Servicio.nombre,
            func.count(Atencion.id),
            func.coalesce(func.sum(case((Atencion.evento_critico.is_(True), 1), else_=0)), 0),
        )
        .join(Paciente, Paciente.servicio_id == Servicio.id)
        .join(Atencion, Atencion.paciente_id == Paciente.id)
        .group_by(Servicio.nombre)
        .order_by(func.count(Atencion.id).desc())
    ).all()

    return Indicadores(
        pacientes_registrados=len(pacientes),
        atenciones_registradas=db.scalar(select(func.count(Atencion.id))) or 0,
        eventos_criticos=db.scalar(select(func.count(Atencion.id)).where(Atencion.evento_critico.is_(True))) or 0,
        pacientes_en_alerta=len(prioritarios),
        medicos_activos=db.scalar(select(func.count(Medico.id)).where(Medico.activo.is_(True))) or 0,
        camas_censables=db.scalar(select(func.coalesce(func.sum(Servicio.camas_censables), 0))) or 0,
        distribucion_riesgo=distribucion,
        atenciones_por_servicio=[
            ConteoServicio(servicio=s, atenciones=a, eventos_criticos=e) for s, a, e in por_servicio
        ],
        pacientes_prioritarios=prioritarios,
    )


@router.get("/riesgo", response_model=list[UmbralOut])
def obtener_tabla(db: Session = Depends(get_db)):
    return tabla(db)


@router.put("/riesgo", response_model=list[UmbralOut], dependencies=[Depends(requiere())])
def reemplazar_tabla(umbrales: list[UmbralIn], db: Session = Depends(get_db)):
    """Reemplaza la escala completa. Se ordena por eventos mínimos; debe iniciar en 0 y no repetir umbrales."""
    if not umbrales:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "La tabla de riesgo no puede quedar vacía")
    ordenados = sorted(umbrales, key=lambda u: u.eventos_minimos)
    valores = [u.eventos_minimos for u in ordenados]
    if valores[0] != 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "El primer umbral debe ser 0 eventos")
    if len(set(valores)) != len(valores):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Hay umbrales repetidos")
    db.execute(delete(UmbralRiesgo))
    db.add_all(UmbralRiesgo(**u.model_dump()) for u in ordenados)
    db.commit()
    return tabla(db)
