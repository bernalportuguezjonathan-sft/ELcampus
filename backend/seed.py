"""Carga datos de prueba para desarrollo.

Uso:  .venv/Scripts/python.exe seed.py

Las claves son de desarrollo. Antes de usar el sistema en el negocio hay
que crear los usuarios reales y borrar estos.
"""

from datetime import date, timedelta

from app import models
from app.database import Base, SessionLocal, engine
from app.security import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

if db.query(models.Usuario).count() == 0:
    db.add_all(
        [
            models.Usuario(
                nombre="admin",
                rol=models.RolUsuario.administrador,
                password_hash=hash_password("campus123"),
            ),
            models.Usuario(
                nombre="vendedor",
                rol=models.RolUsuario.vendedor,
                password_hash=hash_password("campus123"),
            ),
            models.Usuario(
                nombre="mesero",
                rol=models.RolUsuario.mesero,
                password_hash=hash_password("campus123"),
            ),
        ]
    )

if db.query(models.Producto).count() == 0:
    db.add_all(
        [
            models.Producto(
                codigo_barras="7701234567890",
                nombre="Cerveza Aguila 330ml",
                precio=3500,
                stock_actual=120,
                categoria="cerveza",
            ),
            models.Producto(
                codigo_barras="7702345678901",
                nombre="Gaseosa Postobón 400ml",
                precio=2500,
                stock_actual=60,
                categoria="bebidas",
            ),
            models.Producto(
                codigo_barras="7703456789012",
                nombre="Papas Margarita 25g",
                precio=2000,
                stock_actual=4,
                categoria="snacks",
            ),
            models.Producto(
                codigo_barras="MORRAJA-KG",
                nombre="Morraja",
                precio=0,
                tipo_venta=models.TipoVenta.peso,
                precio_por_kg=18000,
                stock_actual=15,
                categoria="restaurante",
            ),
        ]
    )

if db.query(models.Plato).count() == 0:
    hoy = date.today()
    db.add_all(
        [
            models.Plato(nombre="Picada", precio=45000, tipo=models.TipoPlato.fijo),
            models.Plato(
                nombre="Pechuga a la plancha", precio=25000, tipo=models.TipoPlato.fijo
            ),
            models.Plato(nombre="Morraja", precio=22000, tipo=models.TipoPlato.fijo),
            models.Plato(
                nombre="Sancocho de gallina",
                precio=28000,
                tipo=models.TipoPlato.especial,
                activo_desde=hoy,
                activo_hasta=hoy + timedelta(days=2),
            ),
        ]
    )

db.commit()
print("Datos de prueba cargados.")
print("Usuarios:", db.query(models.Usuario).count(), "(admin / vendedor / mesero — clave: campus123)")
print("Productos:", db.query(models.Producto).count())
print("Platos:", db.query(models.Plato).count())
db.close()
