from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Servicio(Base):
    __tablename__ = "servicios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    ubicacion: Mapped[str | None] = mapped_column(String(120))
    camas_censables: Mapped[int] = mapped_column(Integer, default=0)
    jefe_id: Mapped[int | None] = mapped_column(ForeignKey("medicos.id", ondelete="SET NULL"))

    jefe: Mapped["Medico | None"] = relationship(foreign_keys=[jefe_id])


class Medico(Base):
    __tablename__ = "medicos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(160))
    especialidad: Mapped[str | None] = mapped_column(String(120))
    cedula_profesional: Mapped[str | None] = mapped_column(String(20), unique=True)
    turno: Mapped[str | None] = mapped_column(String(30))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class TipoAtencion(Base):
    __tablename__ = "tipos_atencion"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    categoria: Mapped[str | None] = mapped_column(String(80))


class Paciente(Base):
    __tablename__ = "pacientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    expediente: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(160), index=True)
    servicio_id: Mapped[int | None] = mapped_column(ForeignKey("servicios.id", ondelete="SET NULL"))
    medico_tratante_id: Mapped[int | None] = mapped_column(ForeignKey("medicos.id", ondelete="SET NULL"))
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date)
    sexo: Mapped[str | None] = mapped_column(String(1))
    tipo_sangre: Mapped[str | None] = mapped_column(String(4))
    alergias: Mapped[str | None] = mapped_column(String(200))
    contacto_emergencia: Mapped[str | None] = mapped_column(String(160))
    telefono: Mapped[str | None] = mapped_column(String(30))
    estado: Mapped[str] = mapped_column(String(30), default="Activo")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    servicio: Mapped[Servicio | None] = relationship()
    medico_tratante: Mapped[Medico | None] = relationship()
    atenciones: Mapped[list["Atencion"]] = relationship(
        back_populates="paciente", cascade="all, delete-orphan", order_by="Atencion.fecha, Atencion.id"
    )


class Atencion(Base):
    """Bitácora SEGUIMIENTO_CLINICO: cada fila es una atención prestada a un paciente."""

    __tablename__ = "atenciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id", ondelete="CASCADE"), index=True)
    tipo_atencion_id: Mapped[int] = mapped_column(ForeignKey("tipos_atencion.id"))
    medico_id: Mapped[int] = mapped_column(ForeignKey("medicos.id"))
    turno: Mapped[str] = mapped_column(String(30))
    triage: Mapped[str] = mapped_column(String(40))
    nota_clinica: Mapped[str | None] = mapped_column(Text)
    plan_manejo: Mapped[str | None] = mapped_column(Text)
    fecha: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    evento_critico: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    paciente: Mapped[Paciente] = relationship(back_populates="atenciones")
    tipo_atencion: Mapped[TipoAtencion] = relationship()
    medico: Mapped[Medico] = relationship()


class UmbralRiesgo(Base):
    """TABLA_RIESGO: el nivel es el último umbral que no supera el número de eventos críticos."""

    __tablename__ = "tabla_riesgo"

    id: Mapped[int] = mapped_column(primary_key=True)
    eventos_minimos: Mapped[int] = mapped_column(Integer, unique=True)
    nivel: Mapped[str] = mapped_column(String(40))
    semaforo: Mapped[str] = mapped_column(String(20))
    accion: Mapped[str | None] = mapped_column(String(200))
    alerta: Mapped[bool] = mapped_column(Boolean, default=False)
