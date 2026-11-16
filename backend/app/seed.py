"""Carga los datos de ejemplo (ficticios) del libro original.

Uso:
    python -m app.seed            # crea tablas y carga si la base está vacía
    python -m app.seed --reset    # borra todo y vuelve a cargar
"""
import json
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine
from .models import Atencion, Medico, Paciente, Servicio, TipoAtencion, UmbralRiesgo

DATOS = Path(__file__).with_name("seed_data.json")


def _reiniciar_secuencias(db: Session):
    if db.get_bind().dialect.name != "postgresql":
        return
    for tabla in ("servicios", "medicos", "tipos_atencion", "pacientes", "atenciones", "tabla_riesgo"):
        db.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), COALESCE((SELECT MAX(id) FROM {tabla}), 0) + 1, false)"
        ))


def cargar(db: Session, datos: dict | None = None):
    datos = datos or json.loads(DATOS.read_text(encoding="utf-8"))

    medicos = {}
    for m in datos["medicos"]:
        obj = Medico(id=m["id"], nombre=m["nombre"], especialidad=m["especialidad"],
                     cedula_profesional=m["cedula_profesional"], turno=m["turno"])
        db.add(obj)
        medicos[m["nombre"]] = obj
    db.flush()

    servicios = {}
    for i, s in enumerate(datos["servicios"], start=1):
        jefe = medicos.get(s["jefe"])
        obj = Servicio(id=i, nombre=s["nombre"], ubicacion=s["ubicacion"], camas_censables=s["camas_censables"],
                       jefe_id=jefe.id if jefe else None)
        db.add(obj)
        servicios[s["nombre"]] = obj

    tipos = {}
    for i, t in enumerate(datos["tipos_atencion"], start=1):
        obj = TipoAtencion(id=i, nombre=t["nombre"], categoria=t["categoria"])
        db.add(obj)
        tipos[t["nombre"]] = obj

    for u in datos["riesgo"]:
        db.add(UmbralRiesgo(eventos_minimos=u["eventos_minimos"], nivel=u["nivel"], semaforo=u["semaforo"],
                            accion=u["accion"], alerta=u["eventos_minimos"] >= 5))
    db.flush()

    pacientes = {}
    for i, p in enumerate(datos["pacientes"], start=1):
        obj = Paciente(
            id=i,
            expediente=p["expediente"],
            nombre=p["nombre"],
            servicio_id=servicios[p["servicio"]].id if p["servicio"] in servicios else None,
            medico_tratante_id=medicos[p["medico_tratante"]].id if p["medico_tratante"] in medicos else None,
            fecha_nacimiento=date.fromisoformat(p["fecha_nacimiento"]) if p["fecha_nacimiento"] else None,
            sexo=p["sexo"],
            tipo_sangre=p["tipo_sangre"],
            alergias=p["alergias"],
            contacto_emergencia=p["contacto_emergencia"],
            telefono=p["telefono"],
        )
        db.add(obj)
        pacientes[p["expediente"]] = obj
    db.flush()

    for i, a in enumerate(datos["atenciones"], start=1):
        db.add(Atencion(
            id=i,
            paciente_id=pacientes[a["expediente"]].id,
            tipo_atencion_id=tipos[a["tipo_atencion"]].id,
            medico_id=a["medico_id"],
            turno=a["turno"],
            triage=a["triage"],
            nota_clinica=a["nota_clinica"],
            plan_manejo=a["plan_manejo"],
            fecha=date.fromisoformat(a["fecha"]),
            evento_critico=a["evento_critico"],
        ))
    db.flush()
    _reiniciar_secuencias(db)
    db.commit()


def main():
    reset = "--reset" in sys.argv
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(func.count(Paciente.id))):
            print("La base ya contiene datos; usa --reset para reemplazarlos.")
            return
        cargar(db)
        print(
            "Datos cargados:",
            {m.__tablename__: db.scalar(select(func.count()).select_from(m))
             for m in (Servicio, Medico, TipoAtencion, UmbralRiesgo, Paciente, Atencion)},
        )


if __name__ == "__main__":
    main()
