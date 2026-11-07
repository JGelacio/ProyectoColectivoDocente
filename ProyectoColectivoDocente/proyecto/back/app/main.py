from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from . import models, schemas
from .auth import require_admin
from .database import get_db

app = FastAPI(title="PTAGS API")
admin = APIRouter(dependencies=[Depends(require_admin)])
frontend = Path(__file__).resolve().parents[2] / "front"
app.mount("/static", StaticFiles(directory=frontend), name="static")


@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse(frontend / "index.html")


@app.exception_handler(OperationalError)
def base_no_disponible(request, exc):
    return JSONResponse(status_code=503, content={"detail": "Base de datos no disponible"})


@app.get("/tags/consulta", response_model=schemas.FichaMascota)
def consultar_tag(
    response: Response, filtro: Annotated[schemas.ConsultaTag, Query()], db: Session = Depends(get_db)
):
    response.headers["Cache-Control"] = "no-store"
    mascota = db.scalar(select(models.Mascota).where(models.Mascota.tag == filtro.codigo))
    if mascota is None:
        raise HTTPException(404, "Tag no encontrado", headers={"Cache-Control": "no-store"})
    contacto = None
    if mascota.compartir_contacto:
        contacto = schemas.ContactoPublico(nombre=mascota.persona.nombre, telefono=mascota.persona.telefono)
    return schemas.FichaMascota(
        nombre=mascota.nombre, especie=mascota.especie, raza=mascota.raza, contacto=contacto
    )


# ---------- prueba de conexión ----------
@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "conectada"}


# ---------- tipo_persona ----------
@admin.get("/tipos-persona", response_model=list[schemas.TipoPersonaOut])
def listar_tipos(db: Session = Depends(get_db)):
    return db.scalars(select(models.TipoPersona)).all()


@admin.post("/tipos-persona", response_model=schemas.TipoPersonaOut, status_code=201)
def crear_tipo(data: schemas.TipoPersonaCreate, db: Session = Depends(get_db)):
    tipo = models.TipoPersona(**data.model_dump())
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return tipo


# ---------- personas ----------
def _get_persona(db: Session, persona_id: int, *, bloquear: bool = False) -> models.Persona:
    persona = db.get(models.Persona, persona_id, with_for_update=bloquear)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return persona


@admin.get("/personas", response_model=list[schemas.PersonaOut])
def listar_personas(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db)):
    return db.scalars(select(models.Persona).order_by(models.Persona.id).offset(skip).limit(limit)).all()


@admin.get("/personas/{persona_id}", response_model=schemas.PersonaOut)
def obtener_persona(persona_id: int, db: Session = Depends(get_db)):
    return _get_persona(db, persona_id)


@admin.post("/personas", response_model=schemas.PersonaOut, status_code=201)
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


@admin.put("/personas/{persona_id}", response_model=schemas.PersonaOut)
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


@admin.delete(
    "/personas/{persona_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar persona y todas sus mascotas",
    responses={
        404: {"description": "Persona no encontrada"},
        409: {"description": "Hay registros vinculados y no se eliminó ninguna ficha"},
    },
)
def eliminar_persona(persona_id: int, db: Session = Depends(get_db)):
    """Elimina a la persona y a todas sus mascotas en una sola operación definitiva."""
    _get_persona(db, persona_id, bloquear=True)
    borrar_persona_y_mascotas(db, persona_id)


@admin.post("/personas/{persona_id}/eliminar-con-mascotas", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cliente_con_mascotas(
    persona_id: int, data: schemas.EliminarCliente, db: Session = Depends(get_db)
):
    persona = _get_persona(db, persona_id, bloquear=True)
    tipo = (persona.tipo_persona.descripcion or "").strip().casefold()
    if tipo not in {"cliente", "clientes", "propietario", "propietarios"}:
        raise HTTPException(403, "Esta acción solo está disponible para clientes")

    mascotas_del_cliente = models.Mascota.personas_id == persona_id
    ids = db.scalars(select(models.Mascota.id).where(mascotas_del_cliente).with_for_update()).all()
    if sorted(ids) != sorted(data.mascotas_ids):
        raise HTTPException(409, "La lista de mascotas cambió. Revisa las fichas y confirma de nuevo.")

    borrar_persona_y_mascotas(db, persona_id)


def borrar_persona_y_mascotas(db: Session, persona_id: int):
    try:
        db.execute(delete(models.Mascota).where(models.Mascota.personas_id == persona_id))
        db.execute(delete(models.Persona).where(models.Persona.id == persona_id))
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            409, "La persona o sus mascotas tienen otros registros asociados. Se conservaron todas las fichas."
        ) from error


# ---------- mascotas ----------
@admin.get("/mascotas", response_model=list[schemas.MascotaOut])
def listar_mascotas(personas_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(models.Mascota).order_by(models.Mascota.id)
    if personas_id is not None:
        stmt = stmt.where(models.Mascota.personas_id == personas_id)
    return db.scalars(stmt).all()


@admin.get("/personas/{persona_id}/mascotas", response_model=list[schemas.MascotaOut])
def mascotas_de_persona(persona_id: int, db: Session = Depends(get_db)):
    return _get_persona(db, persona_id).mascotas


@admin.post("/mascotas", response_model=schemas.MascotaOut, status_code=201)
def crear_mascota(data: schemas.MascotaCreate, db: Session = Depends(get_db)):
    _get_persona(db, data.personas_id)
    mascota = models.Mascota(**data.model_dump())
    db.add(mascota)
    guardar_mascota(db, mascota)
    return mascota


@admin.delete(
    "/mascotas/{mascota_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar solo una mascota",
    responses={
        404: {"description": "Mascota no encontrada"},
        409: {"description": "La mascota tiene registros vinculados y se conservó su ficha"},
    },
)
def eliminar_mascota(mascota_id: int, db: Session = Depends(get_db)):
    """Elimina la mascota indicada. Su propietario y las demás mascotas se conservan."""
    try:
        resultado = db.execute(delete(models.Mascota).where(models.Mascota.id == mascota_id))
        if resultado.rowcount == 0:
            raise HTTPException(404, "Mascota no encontrada")
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "La mascota tiene otros registros asociados. Se conservó su ficha.") from error


@admin.put("/mascotas/{mascota_id}/tag", response_model=schemas.MascotaOut)
def asignar_tag(mascota_id: int, data: schemas.AsignarTag, db: Session = Depends(get_db)):
    mascota = buscar_mascota(db, mascota_id)
    mascota.tag = data.tag
    guardar_mascota(db, mascota)
    return mascota


@admin.put("/mascotas/{mascota_id}/contacto-publico", response_model=schemas.MascotaOut)
def configurar_contacto(mascota_id: int, compartir: bool, db: Session = Depends(get_db)):
    mascota = buscar_mascota(db, mascota_id)
    mascota.compartir_contacto = compartir
    guardar_mascota(db, mascota)
    return mascota


def buscar_mascota(db: Session, mascota_id: int):
    mascota = db.get(models.Mascota, mascota_id)
    if mascota is None:
        raise HTTPException(404, "Mascota no encontrada")
    return mascota


def guardar_mascota(db: Session, mascota: models.Mascota):
    codigo = mascota.tag
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if codigo is not None and db.scalar(
            select(models.Mascota.id).where(models.Mascota.tag == codigo)
        ) is not None:
            raise HTTPException(409, "El tag ya está asignado a una mascota") from error
        raise HTTPException(409, "No se pudo guardar la asociación de la mascota") from error
    db.refresh(mascota)


app.include_router(admin)
