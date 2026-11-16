from datetime import date

from .models import Atencion, Paciente, UmbralRiesgo
from .riesgo import clasificar
from .schemas import AtencionOut, PacienteOut, Riesgo


def edad(nacimiento: date | None, hoy: date | None = None) -> int | None:
    if nacimiento is None:
        return None
    hoy = hoy or date.today()
    return hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))


def riesgo(eventos: int, umbrales: list[UmbralRiesgo]) -> Riesgo:
    n = clasificar(eventos, umbrales)
    return Riesgo(eventos_criticos=eventos, nivel=n.nivel, semaforo=n.semaforo, accion=n.accion, alerta=n.alerta)


def paciente_out(p: Paciente, eventos: int, umbrales: list[UmbralRiesgo], total_atenciones: int = 0) -> PacienteOut:
    return PacienteOut(
        id=p.id,
        expediente=p.expediente,
        nombre=p.nombre,
        servicio_id=p.servicio_id,
        servicio=p.servicio.nombre if p.servicio else None,
        medico_tratante_id=p.medico_tratante_id,
        medico_tratante=p.medico_tratante.nombre if p.medico_tratante else None,
        fecha_nacimiento=p.fecha_nacimiento,
        edad=edad(p.fecha_nacimiento),
        sexo=p.sexo,
        tipo_sangre=p.tipo_sangre,
        alergias=p.alergias,
        contacto_emergencia=p.contacto_emergencia,
        telefono=p.telefono,
        estado=p.estado,
        total_atenciones=total_atenciones,
        riesgo=riesgo(eventos, umbrales),
    )


def atencion_out(a: Atencion, eventos: int, umbrales: list[UmbralRiesgo]) -> AtencionOut:
    p = a.paciente
    n = clasificar(eventos, umbrales)
    return AtencionOut(
        id=a.id,
        paciente_id=p.id,
        expediente=p.expediente,
        paciente=p.nombre,
        servicio=p.servicio.nombre if p.servicio else None,
        medico_tratante=p.medico_tratante.nombre if p.medico_tratante else None,
        tipo_atencion_id=a.tipo_atencion_id,
        tipo_atencion=a.tipo_atencion.nombre,
        medico_id=a.medico_id,
        medico=a.medico.nombre,
        turno=a.turno,
        triage=a.triage,
        nota_clinica=a.nota_clinica,
        plan_manejo=a.plan_manejo,
        fecha=a.fecha,
        evento_critico=a.evento_critico,
        total_eventos_criticos=eventos,
        nivel_riesgo=n.nivel,
        semaforo=n.semaforo,
    )
