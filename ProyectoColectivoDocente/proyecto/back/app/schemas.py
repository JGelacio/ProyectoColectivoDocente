import re
from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints, field_validator


def limpiar_tag(value):
    if not isinstance(value, str):
        return value
    value = value.strip()
    uid = re.fullmatch(r"(?:UID de la tarjeta:\s*)?([0-9a-f]{2}(?: [0-9a-f]{2}){3,9})", value, re.IGNORECASE)
    if uid:
        return uid[1].replace(" ", "").upper()
    return value


def validar_tag(value: str) -> str:
    if not value or not value.isprintable():
        raise ValueError("Ingresa un código de tag válido")
    return value


CodigoTag = Annotated[str, BeforeValidator(limpiar_tag), Field(max_length=200), AfterValidator(validar_tag)]
Nombre = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=45)]


# ---------- tipo_persona ----------
class TipoPersonaCreate(BaseModel):
    descripcion: Nombre


class TipoPersonaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    descripcion: str | None


# ---------- personas ----------
class PersonaBase(BaseModel):
    tipo_persona_id: int
    nombre: str | None = Field(default=None, max_length=45)
    telefono: str | None = Field(default=None, max_length=45)
    email: str | None = Field(default=None, max_length=45)
    direccion: str | None = Field(default=None, max_length=45)


class PersonaCreate(PersonaBase):
    tipo_persona_id: int = Field(gt=0)
    nombre: Nombre


class PersonaUpdate(BaseModel):
    tipo_persona_id: int | None = None
    nombre: str | None = Field(default=None, max_length=45)
    telefono: str | None = Field(default=None, max_length=45)
    email: str | None = Field(default=None, max_length=45)
    direccion: str | None = Field(default=None, max_length=45)


class EliminarCliente(BaseModel):
    mascotas_ids: list[Annotated[int, Field(gt=0)]]


class PersonaOut(PersonaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- mascotas ----------
class MascotaBase(BaseModel):
    personas_id: int
    nombre: str | None = Field(default=None, max_length=45)
    especie: str | None = Field(default=None, max_length=45)
    raza: str | None = Field(default=None, max_length=45)
    fecha_nacimiento: date | None = None
    sexo: str | None = Field(default=None, max_length=2)
    tag: str | None = Field(default=None, max_length=200)


class MascotaCreate(MascotaBase):
    personas_id: int = Field(gt=0)
    nombre: Nombre
    especie: Nombre
    tag: CodigoTag | None = None
    compartir_contacto: bool = False

    @field_validator("fecha_nacimiento")
    @classmethod
    def validar_fecha(cls, value: date | None):
        if value and value > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura")
        return value


class ConsultaTag(BaseModel):
    codigo: CodigoTag


class AsignarTag(BaseModel):
    tag: CodigoTag


class ContactoPublico(BaseModel):
    nombre: str | None
    telefono: str | None


class FichaMascota(BaseModel):
    nombre: str | None
    especie: str | None
    raza: str | None
    contacto: ContactoPublico | None


class MascotaOut(MascotaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    compartir_contacto: bool
