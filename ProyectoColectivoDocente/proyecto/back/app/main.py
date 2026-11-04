from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models, schemas
from .database import get_db

app = FastAPI(title="PTAGS API")


# ---------- prueba de conexión ----------
@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "conectada"}


# ---------- tipo_persona ----------
@app.get("/tipos-persona", response_model=list[schemas.TipoPersonaOut])
def listar_tipos(db: Session = Depends(get_db)):
    return db.scalars(select(models.TipoPersona)).all()


@app.post("/tipos-persona", response_model=schemas.TipoPersonaOut, status_code=201)
def crear_tipo(data: schemas.TipoPersonaCreate, db: Session = Depends(get_db)):
    tipo = models.TipoPersona(**data.model_dump())
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return tipo


# ---------- personas ----------
def _get_persona(db: Session, persona_id: int) -> models.Persona:
    persona = db.get(models.Persona, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return persona


@app.get("/personas", response_model=list[schemas.PersonaOut])
def listar_personas(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.scalars(select(models.Persona).offset(skip).limit(limit)).all()


@app.get("/personas/{persona_id}", response_model=schemas.PersonaOut)
def obtener_persona(persona_id: int, db: Session = Depends(get_db)):
    return _get_persona(db, persona_id)


@app.post("/personas", response_model=schemas.PersonaOut, status_code=201)
def crear_persona(data: schemas.PersonaCreate, db: Session = Depends(get_db)):
    persona = models.Persona(**data.model_dump())
    db.add(persona)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="tipo_persona_id no existe")
    db.refresh(persona)
    return persona


@app.put("/personas/{persona_id}", response_model=schemas.PersonaOut)
def actualizar_persona(persona_id: int, data: schemas.PersonaUpdate, db: Session = Depends(get_db)):
    persona = _get_persona(db, persona_id)
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(persona, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="tipo_persona_id no existe")
    db.refresh(persona)
    return persona


@app.delete("/personas/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_persona(persona_id: int, db: Session = Depends(get_db)):
    persona = _get_persona(db, persona_id)
    db.delete(persona)
    try:
        db.commit()
    except IntegrityError:
        # Las FK están en ON DELETE RESTRICT
        db.rollback()
        raise HTTPException(status_code=409, detail="La persona tiene registros asociados (mascotas, usuarios, etc.)")


# ---------- mascotas ----------
@app.get("/mascotas", response_model=list[schemas.MascotaOut])
def listar_mascotas(personas_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(models.Mascota)
    if personas_id is not None:
        stmt = stmt.where(models.Mascota.personas_id == personas_id)
    return db.scalars(stmt).all()


@app.get("/personas/{persona_id}/mascotas", response_model=list[schemas.MascotaOut])
def mascotas_de_persona(persona_id: int, db: Session = Depends(get_db)):
    return _get_persona(db, persona_id).mascotas


@app.post("/mascotas", response_model=schemas.MascotaOut, status_code=201)
def crear_mascota(data: schemas.MascotaCreate, db: Session = Depends(get_db)):
    mascota = models.Mascota(**data.model_dump())
    db.add(mascota)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="personas_id no existe")
    db.refresh(mascota)
    return mascota
