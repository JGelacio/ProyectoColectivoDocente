import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


class PTAGSTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)

        def test_db():
            with Session(self.engine) as db:
                yield db

        self.addCleanup(self.engine.dispose)
        app.dependency_overrides[get_db] = test_db
        self.addCleanup(app.dependency_overrides.pop, get_db)
        self.enterContext(patch.dict("os.environ", {
            "PTAGS_ADMIN_USER": "admin", "PTAGS_ADMIN_PASSWORD": "test-password",
        }))
        self.client = self.enterContext(TestClient(app))
        self.auth = ("admin", "test-password")

    def post(self, path, data):
        return self.client.post(path, json=data, auth=self.auth)

    def owner(self):
        tipo = self.post("/tipos-persona", {"descripcion": "Propietario"})
        self.assertEqual(tipo.status_code, 201, tipo.text)
        persona = self.post("/personas", {
            "tipo_persona_id": tipo.json()["id"],
            "nombre": "Ana",
            "telefono": "3000000000",
            "email": "ana@example.org",
            "direccion": "Dirección de prueba",
        })
        self.assertEqual(persona.status_code, 201, persona.text)
        return persona.json()["id"]

    def lookup(self, tag):
        return self.client.get("/tags/consulta", params={"codigo": tag})

    def test_registro_asignacion_consulta_y_privacidad(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/static/app.js").status_code, 200)
        self.assertEqual(self.client.get("/health/db").status_code, 200)
        owner = self.owner()
        pet = self.post("/mascotas", {"personas_id": owner, "nombre": "Luna", "especie": "Perro"})
        self.assertEqual(pet.status_code, 201, pet.text)
        pet_id = pet.json()["id"]
        path = f"/mascotas/{pet_id}"
        tag = "UID de la tarjeta: 0a b2 03 f4"
        assigned = self.client.put(path + "/tag", auth=self.auth, json={"tag": tag})
        self.assertEqual(assigned.status_code, 200, assigned.text)
        self.assertEqual(assigned.json()["tag"], "0AB203F4")
        public = self.lookup(tag)
        self.assertEqual(public.status_code, 200, public.text)
        self.assertEqual(public.headers["cache-control"], "no-store")
        self.assertEqual(public.json(), {
            "nombre": "Luna", "especie": "Perro", "raza": None, "contacto": None,
        })

        duplicate = self.post("/mascotas", {
            "personas_id": owner, "nombre": "Sol", "especie": "Gato", "tag": "0AB203F4",
        })
        self.assertEqual(duplicate.status_code, 409, duplicate.text)
        pets = self.client.get("/mascotas", auth=self.auth).json()
        self.assertEqual([pet["id"] for pet in pets], [pet_id])

        for allowed in (True, False):
            updated = self.client.put(
                path + "/contacto-publico", auth=self.auth, params={"compartir": allowed}
            )
            self.assertEqual(updated.status_code, 200, updated.text)
            expected = {"nombre": "Ana", "telefono": "3000000000"} if allowed else None
            self.assertEqual(self.lookup("0AB203F4").json()["contacto"], expected)

        replaced = self.client.put(path + "/tag", auth=self.auth, json={"tag": "PTAGS-42"})
        self.assertEqual(replaced.status_code, 200, replaced.text)
        self.assertEqual(self.lookup(tag).status_code, 404)
        self.assertEqual(self.lookup("PTAGS-42").status_code, 200)

    def test_eliminar_cliente_y_mascotas_confirmadas(self):
        owner = self.owner()
        path = f"/personas/{owner}"
        delete_path = path + "/eliminar-con-mascotas"
        ids = []
        for nombre, tag in (("Luna", "PTAGS-10"), ("Sol", "PTAGS-11")):
            pet = self.post("/mascotas", {"personas_id": owner, "nombre": nombre, "especie": "Perro", "tag": tag})
            self.assertEqual(pet.status_code, 201, pet.text)
            ids.append(pet.json()["id"])

        self.assertEqual(self.client.post(delete_path, json={"mascotas_ids": ids}).status_code, 401)
        self.assertEqual(self.post(delete_path, {"mascotas_ids": ids[:1]}).status_code, 409)
        self.assertEqual(self.lookup("PTAGS-10").status_code, 200)
        self.assertEqual(self.lookup("PTAGS-11").status_code, 200)

        result = self.post(delete_path, {"mascotas_ids": ids[::-1]})
        self.assertEqual(result.status_code, 204, result.text)
        self.assertEqual(self.client.get(path, auth=self.auth).status_code, 404)
        self.assertEqual(self.lookup("PTAGS-10").status_code, 404)
        self.assertEqual(self.lookup("PTAGS-11").status_code, 404)
        self.assertEqual(self.post(delete_path, {"mascotas_ids": ids}).status_code, 404)

    def test_eliminacion_revierte_si_el_cliente_tiene_otras_referencias(self):
        owner = self.owner()
        pet = self.post("/mascotas", {
            "personas_id": owner, "nombre": "Luna", "especie": "Perro", "tag": "PTAGS-12",
        })
        self.assertEqual(pet.status_code, 201, pet.text)
        # El esquema MySQL incluye vínculos a personas que no están en los modelos de la API.
        with self.engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE usuarios_prueba (persona_id INTEGER REFERENCES personas(id) ON DELETE RESTRICT)"
            ))
            connection.execute(text("INSERT INTO usuarios_prueba VALUES (:persona_id)"), {"persona_id": owner})

        path = f"/personas/{owner}"
        results = (
            self.post(path + "/eliminar-con-mascotas", {"mascotas_ids": [pet.json()["id"]]}),
            self.client.delete(path, auth=self.auth),
        )
        for result in results:
            self.assertEqual(result.status_code, 409, result.text)
        self.assertEqual(self.client.get(path, auth=self.auth).status_code, 200)
        self.assertEqual(self.lookup("PTAGS-12").status_code, 200)

    def test_eliminacion_combinada_solo_para_clientes(self):
        tipo = self.post("/tipos-persona", {"descripcion": "Veterinario"})
        persona = self.post("/personas", {"tipo_persona_id": tipo.json()["id"], "nombre": "Veterinaria"})
        self.assertEqual(persona.status_code, 201, persona.text)
        path = f"/personas/{persona.json()['id']}"
        self.assertEqual(self.post(path + "/eliminar-con-mascotas", {"mascotas_ids": []}).status_code, 403)
        self.assertEqual(self.client.get(path, auth=self.auth).status_code, 200)

    def test_borrar_persona_y_mascota_desde_delete(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        self.assertIn("delete", paths["/personas/{persona_id}"])
        self.assertIn("delete", paths["/mascotas/{mascota_id}"])

        owner = self.owner()
        mascota_ids = []
        for nombre, tag in (("Luna", "PTAGS-21"), ("Sol", "PTAGS-22")):
            pet = self.post("/mascotas", {
                "personas_id": owner, "nombre": nombre, "especie": "Perro", "tag": tag,
            })
            self.assertEqual(pet.status_code, 201, pet.text)
            mascota_ids.append(pet.json()["id"])

        persona_path = f"/personas/{owner}"
        mascota_path = f"/mascotas/{mascota_ids[0]}"
        self.assertEqual(self.client.delete(persona_path).status_code, 401)
        self.assertEqual(self.client.delete(mascota_path).status_code, 401)
        result = self.client.delete(mascota_path, auth=self.auth)
        self.assertEqual(result.status_code, 204, result.text)
        self.assertEqual(self.client.get(persona_path, auth=self.auth).status_code, 200)
        self.assertEqual(self.lookup("PTAGS-21").status_code, 404)
        self.assertEqual(self.lookup("PTAGS-22").status_code, 200)
        self.assertEqual(self.client.delete(mascota_path, auth=self.auth).status_code, 404)

        result = self.client.delete(persona_path, auth=self.auth)
        self.assertEqual(result.status_code, 204, result.text)
        self.assertEqual(self.client.get(persona_path, auth=self.auth).status_code, 404)
        self.assertEqual(self.lookup("PTAGS-22").status_code, 404)

    def test_borrar_mascota_con_registros_asociados(self):
        owner = self.owner()
        pet = self.post("/mascotas", {
            "personas_id": owner, "nombre": "Luna", "especie": "Perro", "tag": "PTAGS-23",
        })
        self.assertEqual(pet.status_code, 201, pet.text)
        pet_id = pet.json()["id"]
        with self.engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE citas_prueba (mascota_id INTEGER REFERENCES mascotas(id) ON DELETE RESTRICT)"
            ))
            connection.execute(text("INSERT INTO citas_prueba VALUES (:mascota_id)"), {"mascota_id": pet_id})

        self.assertEqual(self.client.delete(f"/mascotas/{pet_id}", auth=self.auth).status_code, 409)
        self.assertEqual(self.client.delete(f"/personas/{owner}", auth=self.auth).status_code, 409)
        self.assertEqual(self.lookup("PTAGS-23").status_code, 200)

    def test_acceso_y_validaciones(self):
        self.assertEqual(self.client.get("/personas").status_code, 401)
        self.assertEqual(self.client.get("/mascotas", auth=("admin", "incorrecta")).status_code, 401)
        with patch.dict("os.environ", {"PTAGS_ADMIN_PASSWORD": ""}):
            self.assertEqual(self.client.get("/personas").status_code, 503)
        self.assertEqual(self.lookup(" ").status_code, 422)
        self.assertEqual(self.lookup("desconocido").status_code, 404)
        data = {"personas_id": 99, "nombre": "Luna", "especie": "Perro"}
        self.assertEqual(self.post("/mascotas", data).status_code, 404)
        self.assertEqual(self.post("/mascotas", {**data, "nombre": " "}).status_code, 422)
        self.assertEqual(self.post("/mascotas", {**data, "fecha_nacimiento": "2999-01-01"}).status_code, 422)
        self.assertEqual(self.client.put("/mascotas/99/tag", auth=self.auth, json={"tag": "ABC"}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
