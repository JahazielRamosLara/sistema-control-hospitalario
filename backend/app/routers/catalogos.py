"""Catálogos maestros: servicios, médicos, tipos de atención y listas de configuración."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from .. import constantes
from ..database import get_db
from ..models import Atencion, Medico, Paciente, Servicio, TipoAtencion
from ..schemas import (
    MedicoIn,
    MedicoOut,
    ServicioIn,
    ServicioOut,
    TipoAtencionIn,
    TipoAtencionOut,
)

router = APIRouter(tags=["catálogos"])


def _obtener(db: Session, modelo, id_: int, etiqueta: str):
    obj = db.get(modelo, id_)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{etiqueta} {id_} no encontrado")
    return obj


@router.get("/config")
def config():
    """Listas que alimentan los menús desplegables (hoja CONFIG)."""
    return {
        "turnos": constantes.TURNOS,
        "triage": constantes.TRIAGE,
        "sexos": constantes.SEXOS,
        "tipos_sangre": constantes.TIPOS_SANGRE,
        "estados_paciente": constantes.ESTADOS_PACIENTE,
        "semaforos": constantes.SEMAFOROS,
    }


# ---------- Servicios ----------
def _servicio_out(s: Servicio) -> ServicioOut:
    return ServicioOut(
        id=s.id,
        nombre=s.nombre,
        ubicacion=s.ubicacion,
        camas_censables=s.camas_censables,
        jefe_id=s.jefe_id,
        jefe_nombre=s.jefe.nombre if s.jefe else None,
    )


@router.get("/servicios", response_model=list[ServicioOut])
def listar_servicios(db: Session = Depends(get_db)):
    return [_servicio_out(s) for s in db.scalars(select(Servicio).order_by(Servicio.id))]


@router.post("/servicios", response_model=ServicioOut, status_code=201)
def crear_servicio(datos: ServicioIn, db: Session = Depends(get_db)):
    if datos.jefe_id is not None:
        _obtener(db, Medico, datos.jefe_id, "Médico")
    s = Servicio(**datos.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return _servicio_out(s)


@router.put("/servicios/{servicio_id}", response_model=ServicioOut)
def editar_servicio(servicio_id: int, datos: ServicioIn, db: Session = Depends(get_db)):
    s = _obtener(db, Servicio, servicio_id, "Servicio")
    if datos.jefe_id is not None:
        _obtener(db, Medico, datos.jefe_id, "Médico")
    for k, v in datos.model_dump().items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return _servicio_out(s)


@router.delete("/servicios/{servicio_id}", status_code=204)
def eliminar_servicio(servicio_id: int, db: Session = Depends(get_db)):
    s = _obtener(db, Servicio, servicio_id, "Servicio")
    if db.scalar(select(exists().where(Paciente.servicio_id == servicio_id))):
        raise HTTPException(status.HTTP_409_CONFLICT, "El servicio tiene pacientes adscritos")
    db.delete(s)
    db.commit()


# ---------- Médicos ----------
@router.get("/medicos", response_model=list[MedicoOut])
def listar_medicos(solo_activos: bool = False, db: Session = Depends(get_db)):
    q = select(Medico).order_by(Medico.id)
    if solo_activos:
        q = q.where(Medico.activo.is_(True))
    return db.scalars(q).all()


@router.post("/medicos", response_model=MedicoOut, status_code=201)
def crear_medico(datos: MedicoIn, db: Session = Depends(get_db)):
    m = Medico(**datos.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.put("/medicos/{medico_id}", response_model=MedicoOut)
def editar_medico(medico_id: int, datos: MedicoIn, db: Session = Depends(get_db)):
    m = _obtener(db, Medico, medico_id, "Médico")
    for k, v in datos.model_dump().items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/medicos/{medico_id}", status_code=204)
def eliminar_medico(medico_id: int, db: Session = Depends(get_db)):
    m = _obtener(db, Medico, medico_id, "Médico")
    if db.scalar(select(exists().where(Atencion.medico_id == medico_id))):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El médico tiene atenciones registradas; márcalo como inactivo en lugar de eliminarlo",
        )
    db.delete(m)
    db.commit()


# ---------- Tipos de atención ----------
@router.get("/tipos-atencion", response_model=list[TipoAtencionOut])
def listar_tipos(db: Session = Depends(get_db)):
    return db.scalars(select(TipoAtencion).order_by(TipoAtencion.id)).all()


@router.post("/tipos-atencion", response_model=TipoAtencionOut, status_code=201)
def crear_tipo(datos: TipoAtencionIn, db: Session = Depends(get_db)):
    t = TipoAtencion(**datos.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/tipos-atencion/{tipo_id}", response_model=TipoAtencionOut)
def editar_tipo(tipo_id: int, datos: TipoAtencionIn, db: Session = Depends(get_db)):
    t = _obtener(db, TipoAtencion, tipo_id, "Tipo de atención")
    for k, v in datos.model_dump().items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/tipos-atencion/{tipo_id}", status_code=204)
def eliminar_tipo(tipo_id: int, db: Session = Depends(get_db)):
    t = _obtener(db, TipoAtencion, tipo_id, "Tipo de atención")
    if db.scalar(select(exists().where(Atencion.tipo_atencion_id == tipo_id))):
        raise HTTPException(status.HTTP_409_CONFLICT, "El tipo de atención está en uso en la bitácora")
    db.delete(t)
    db.commit()
