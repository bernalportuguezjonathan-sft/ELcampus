import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_db
from app.main import app
from app.security import hash_password


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def datos(db):
    vendedor = models.Usuario(
        nombre="Vendedor de prueba",
        rol=models.RolUsuario.vendedor,
        password_hash=hash_password("clave-de-prueba"),
    )
    cerveza = models.Producto(
        codigo_barras="7701234567890",
        nombre="Cerveza Aguila 330ml",
        precio=3500,
        stock_actual=100,
    )
    morraja = models.Producto(
        codigo_barras="MORRAJA-KG",
        nombre="Morraja",
        precio=0,
        tipo_venta=models.TipoVenta.peso,
        precio_por_kg=18000,
        stock_actual=20,
    )
    picada = models.Plato(nombre="Picada", precio=45000, tipo=models.TipoPlato.fijo)
    db.add_all([vendedor, cerveza, morraja, picada])
    db.commit()
    return {
        "vendedor": vendedor,
        "cerveza": cerveza,
        "morraja": morraja,
        "picada": picada,
    }
