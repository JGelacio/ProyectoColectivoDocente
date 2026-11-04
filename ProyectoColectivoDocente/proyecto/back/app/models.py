from datetime import date

from sqlalchemy import CHAR, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class TipoPersona(Base):
    __tablename__ = "tipo_persona"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    descripcion: Mapped[str | None] = mapped_column(String(45))

    personas: Mapped[list["Persona"]] = relationship(back_populates="tipo_persona")


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipo_persona_id: Mapped[int] = mapped_column(ForeignKey("tipo_persona.id"))
    nombre: Mapped[str | None] = mapped_column(String(45))
    telefono: Mapped[str | None] = mapped_column(String(45))
    email: Mapped[str | None] = mapped_column(String(45))
    direccion: Mapped[str | None] = mapped_column(String(45))

    tipo_persona: Mapped[TipoPersona] = relationship(back_populates="personas")
    mascotas: Mapped[list["Mascota"]] = relationship(back_populates="persona")


class Mascota(Base):
    __tablename__ = "mascotas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    personas_id: Mapped[int] = mapped_column(ForeignKey("personas.id"))
    nombre: Mapped[str | None] = mapped_column(String(45))
    especie: Mapped[str | None] = mapped_column(String(45))
    raza: Mapped[str | None] = mapped_column(String(45))
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date)
    sexo: Mapped[str | None] = mapped_column(CHAR(2))
    tag: Mapped[str | None] = mapped_column(String(200))

    persona: Mapped[Persona] = relationship(back_populates="mascotas")
