from datetime import date

from pydantic import BaseModel, ConfigDict, Field


# ---------- tipo_persona ----------
class TipoPersonaCreate(BaseModel):
    descripcion: str = Field(max_length=45)


class TipoPersonaOut(TipoPersonaCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- personas ----------
class PersonaBase(BaseModel):
    tipo_persona_id: int
    nombre: str | None = Field(default=None, max_length=45)
    telefono: str | None = Field(default=None, max_length=45)
    email: str | None = Field(default=None, max_length=45)
    direccion: str | None = Field(default=None, max_length=45)


class PersonaCreate(PersonaBase):
    pass


class PersonaUpdate(BaseModel):
    tipo_persona_id: int | None = None
    nombre: str | None = Field(default=None, max_length=45)
    telefono: str | None = Field(default=None, max_length=45)
    email: str | None = Field(default=None, max_length=45)
    direccion: str | None = Field(default=None, max_length=45)


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
    pass


class MascotaOut(MascotaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
