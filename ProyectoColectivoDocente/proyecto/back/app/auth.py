import os
from secrets import compare_digest

from fastapi import Depends, HTTPException, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials

basic = HTTPBasic(auto_error=False)


def require_admin(response: Response, credentials: HTTPBasicCredentials | None = Depends(basic)):
    response.headers["Cache-Control"] = "no-store"
    username = os.getenv("PTAGS_ADMIN_USER", "admin").encode()
    password = os.getenv("PTAGS_ADMIN_PASSWORD", "").encode()
    if not password:
        raise HTTPException(503, "Configura PTAGS_ADMIN_PASSWORD para habilitar la administración")
    if credentials:
        valid_user = compare_digest(credentials.username.encode(), username)
        valid_password = compare_digest(credentials.password.encode(), password)
        if valid_user and valid_password:
            return
    raise HTTPException(401, "Acceso de administración requerido", headers={"WWW-Authenticate": "Basic"})
