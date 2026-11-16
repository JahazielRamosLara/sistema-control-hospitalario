from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constantes import ESTADOS_PACIENTE, SEMAFOROS, SEXOS, TIPOS_SANGRE, TRIAGE, TURNOS


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Catálogos ----------
class ServicioIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    ubicacion: str | None = None
    camas_censables: int = Field(0, ge=0)
    jefe_id: int | None = None


class ServicioOut(ServicioIn, ORM):
    id: int
    jefe_nombre: str | None = None


class MedicoIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=160)
    especialidad: str | None = None
    cedula_profesional: str | None = Field(None, max_length=20)
    turno: str | None = None
    activo: bool = True

    @field_validator("turno")
    @classmethod
    def _turno(cls, v):
        if v is not None and v not in TURNOS:
            raise ValueError(f"Turno inválido. Opciones: {', '.join(TURNOS)}")
        return v


class MedicoOut(MedicoIn, ORM):
    id: int


class TipoAtencionIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    categoria: str | None = None


class TipoAtencionOut(TipoAtencionIn, ORM):
    id: int


# ---------- Riesgo ----------
class UmbralIn(BaseModel):
    eventos_minimos: int = Field(ge=0)
    nivel: str = Field(min_length=2, max_length=40)
    semaforo: str
    accion: str | None = None
    alerta: bool = False

    @field_validator("semaforo")
    @classmethod
    def _semaforo(cls, v):
        if v not in SEMAFOROS:
            raise ValueError(f"Semáforo inválido. Opciones: {', '.join(SEMAFOROS)}")
        return v


class UmbralOut(UmbralIn, ORM):
    id: int


class Riesgo(BaseModel):
    eventos_criticos: int
    nivel: str
    semaforo: str
    accion: str | None
    alerta: bool


# ---------- Pacientes ----------
class PacienteIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=160)
    servicio_id: int | None = None
    medico_tratante_id: int | None = None
    fecha_nacimiento: date | None = None
    sexo: str | None = None
    tipo_sangre: str | None = None
    alergias: str | None = None
    contacto_emergencia: str | None = None
    telefono: str | None = None
    estado: str = "Activo"

    @field_validator("sexo")
    @classmethod
    def _sexo(cls, v):
        if v not in (None, *SEXOS):
            raise ValueError("Sexo debe ser M o F")
        return v

    @field_validator("tipo_sangre")
    @classmethod
    def _sangre(cls, v):
        if v not in (None, *TIPOS_SANGRE):
            raise ValueError("Tipo de sangre inválido")
        return v

    @field_validator("estado")
    @classmethod
    def _estado(cls, v):
        if v not in ESTADOS_PACIENTE:
            raise ValueError("Estado inválido")
        return v

    @field_validator("fecha_nacimiento")
    @classmethod
    def _nacimiento(cls, v):
        if v is not None and v > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura")
        return v


class PacienteOut(BaseModel):
    id: int
    expediente: str
    nombre: str
    servicio_id: int | None
    servicio: str | None
    medico_tratante_id: int | None
    medico_tratante: str | None
    fecha_nacimiento: date | None
    edad: int | None
    sexo: str | None
    tipo_sangre: str | None
    alergias: str | None
    contacto_emergencia: str | None
    telefono: str | None
    estado: str
    total_atenciones: int = 0
    riesgo: Riesgo


# ---------- Atenciones ----------
class AtencionIn(BaseModel):
    paciente_id: int
    tipo_atencion_id: int
    medico_id: int
    turno: str
    triage: str
    nota_clinica: str | None = None
    plan_manejo: str | None = None
    fecha: date | None = None  # si se omite, se sella con la fecha del día
    evento_critico: bool = False

    @field_validator("turno")
    @classmethod
    def _turno(cls, v):
        if v not in TURNOS:
            raise ValueError(f"Turno inválido. Opciones: {', '.join(TURNOS)}")
        return v

    @field_validator("triage")
    @classmethod
    def _triage(cls, v):
        if v not in TRIAGE:
            raise ValueError("Nivel de triage inválido")
        return v


class AtencionOut(BaseModel):
    id: int
    paciente_id: int
    expediente: str
    paciente: str
    servicio: str | None
    medico_tratante: str | None
    tipo_atencion_id: int
    tipo_atencion: str
    medico_id: int
    medico: str
    turno: str
    triage: str
    nota_clinica: str | None
    plan_manejo: str | None
    fecha: date
    evento_critico: bool
    total_eventos_criticos: int
    nivel_riesgo: str
    semaforo: str


class PaginaAtenciones(BaseModel):
    total: int
    items: list[AtencionOut]


class PacienteDetalle(PacienteOut):
    atenciones: list[AtencionOut]
    ultima_atencion: date | None


class ConteoNivel(BaseModel):
    nivel: str
    semaforo: str
    pacientes: int


class ConteoServicio(BaseModel):
    servicio: str
    atenciones: int
    eventos_criticos: int


class Indicadores(BaseModel):
    pacientes_registrados: int
    atenciones_registradas: int
    eventos_criticos: int
    pacientes_en_alerta: int
    medicos_activos: int
    camas_censables: int
    distribucion_riesgo: list[ConteoNivel]
    atenciones_por_servicio: list[ConteoServicio]
    pacientes_prioritarios: list[PacienteOut]
