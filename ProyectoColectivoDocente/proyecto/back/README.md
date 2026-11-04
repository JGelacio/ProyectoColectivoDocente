# PTAGS API (FastAPI + MySQL)

## 1. Crear la base de datos
```bash
mysql -u root -p < ../basededatos.sql
```

## 2. Entorno virtual y dependencias
```bash
cd back
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Configurar credenciales
```bash
cp .env.example .env            # y edita DB_USER / DB_PASSWORD
```

## 4. Ejecutar
```bash
uvicorn app.main:app --reload
```
- Documentación interactiva: http://127.0.0.1:8000/docs
- Probar la conexión: http://127.0.0.1:8000/health/db

## Estructura
```
back/
├── app/
│   ├── database.py   # engine, sesión y dependencia get_db
│   ├── models.py     # modelos SQLAlchemy (tipo_persona, personas, mascotas)
│   ├── schemas.py    # validación Pydantic (entrada/salida)
│   └── main.py       # endpoints
├── requirements.txt
└── .env.example
```

Las tablas ya existen por el script SQL, por eso no se usa `Base.metadata.create_all()`.
