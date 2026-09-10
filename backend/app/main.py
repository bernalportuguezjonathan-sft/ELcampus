from fastapi import FastAPI

from . import models
from .database import Base, engine
from .routers import productos, ventas

# Dev only: crea las tablas si no existen. Cuando el esquema empiece a
# cambiar seguido, esto se reemplaza por migraciones con Alembic.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="El Campus API")

app.include_router(productos.router)
app.include_router(ventas.router)


@app.get("/salud")
def salud():
    return {"estado": "ok"}
