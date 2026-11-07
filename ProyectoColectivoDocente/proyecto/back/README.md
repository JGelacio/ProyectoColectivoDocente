# PTAGS

FastAPI sirve la aplicación web y se conecta a la base MySQL existente. Ejecuta estos pasos desde `proyecto/back`.

## Preparar la base

- **Base existente.** Conserva la configuración y los datos. Haz una copia de seguridad y aplica una sola vez `mysql -u TU_USUARIO -p ptags < migrations/001_tags.sql`. Si tienes duplicados, identifica primero a qué mascota pertenece cada código y resuélvelos antes de volver a ejecutar la migración. Para otro nombre de base, reemplaza `ptags`. Para una base remota, usa el host y puerto configurados para esa instancia.
- **Base nueva.** Importa el esquema con `mysql -u TU_USUARIO -p < ../basededatos.sql`. Este esquema ya incluye la columna de autorización y la restricción de tag único.

## Iniciar en el Mac

```bash
python3 -m venv .venv-ptags
source .venv-ptags/bin/activate
python -m pip install -r requirements.txt
```

Si aún no tienes `.env`, copia `.env.example` a `.env`. Configura la conexión existente con `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME` o `DATABASE_URL`. Define `PTAGS_ADMIN_USER` y una contraseña propia en `PTAGS_ADMIN_PASSWORD`. Usa caracteres ASCII y evita los dos puntos en el nombre de usuario.

```bash
python -m uvicorn app.main:app --reload
```

- Aplicación: http://127.0.0.1:8000/
- Conexión MySQL: http://127.0.0.1:8000/health/db
- Documentación de la API: http://127.0.0.1:8000/docs

El servidor escucha solo en el equipo de forma predeterminada. Si publicas la aplicación, sirve el acceso administrativo sobre HTTPS. La administración usa HTTP Basic con las credenciales de `.env`.

## Probar el flujo

1. Entra en **Administración**. Si todavía no existe un tipo de cliente, pulsa **Habilitar Cliente**. El panel muestra **Cliente** como única opción de registro y reconoce el tipo **Propietario** de versiones anteriores.
2. Registra un cliente y luego su mascota. Puedes escribir el código al registrarla o asignarlo después desde **Asignar o reemplazar tag**.
3. En **Consultar un tag**, introduce el código. La ficha muestra nombre, especie y raza. Para autorizar o revocar la publicación del nombre y teléfono del propietario, usa **Contacto en la ficha pública**. El correo y la dirección quedan en la administración.
4. Intenta asignar el mismo código a otra mascota. La API devuelve un conflicto y conserva la asignación original.
5. Para el lector MFRC522 de `Hardware/Hardware.ino`, conecta la placa por USB y cierra el monitor serie. Abre la app en Chrome de escritorio, pulsa **Conectar lector USB**, selecciona el puerto de la placa y acerca la tarjeta. La ficha se consulta automáticamente. También puedes abrir el monitor serie a 9600 baudios y pegar en el formulario la línea que empieza por `UID de la tarjeta:`.

Los códigos existentes se conservan tal como están en MySQL. Si un RFID se guardó antes con espacios entre bytes, vuelve a asignarlo usando la línea del monitor para guardarlo en formato compacto.

## Eliminar personas y mascotas

Abre `/docs`. Inicia sesión con **Authorize**, consulta los IDs con **GET /personas** o **GET /mascotas** y usa **Try it out** en la operación que corresponda.

- **DELETE /personas/{persona_id}** elimina la persona y todas sus mascotas.
- **DELETE /mascotas/{mascota_id}** elimina solo la mascota indicada. Su propietario y las demás mascotas se conservan.

**Execute** realiza el borrado definitivo. El código **204** indica que se completó. **409** indica que hay otros registros vinculados y se conservaron todas las fichas.

## Pruebas automatizadas

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Las pruebas usan una base SQLite temporal y verifican registro, asignación, unicidad, consulta, privacidad y validaciones sin modificar MySQL.
