from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


def test_sin_token_no_se_entra(db, datos):
    app.dependency_overrides[get_db] = lambda: db
    try:
        anonimo = TestClient(app)
        assert anonimo.get("/api/productos").status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_login_con_clave_correcta_devuelve_sesion(db, datos):
    app.dependency_overrides[get_db] = lambda: db
    try:
        c = TestClient(app)
        respuesta = c.post(
            "/api/auth/entrar", json={"nombre": "vendedor", "clave": "clave-de-prueba"}
        )
        assert respuesta.status_code == 200
        sesion = respuesta.json()
        assert sesion["rol"] == "vendedor"
        assert sesion["access_token"]
    finally:
        app.dependency_overrides.clear()


def test_login_con_clave_incorrecta_se_rechaza(db, datos):
    app.dependency_overrides[get_db] = lambda: db
    try:
        c = TestClient(app)
        respuesta = c.post(
            "/api/auth/entrar", json={"nombre": "vendedor", "clave": "la-que-no-es"}
        )
        assert respuesta.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_el_mesero_no_puede_cobrar(como, datos):
    mesero = como("mesero")
    respuesta = mesero.post(
        "/api/ventas",
        json={
            "tipo": "mostrador",
            "metodo_pago": "efectivo",
            "items": [{"producto_id": datos["cerveza"].id, "cantidad": 1}],
        },
    )
    assert respuesta.status_code == 403


def test_el_vendedor_no_puede_cambiar_precios(cliente, datos):
    respuesta = cliente.patch(
        f"/api/productos/{datos['cerveza'].id}", json={"precio": 1}
    )
    assert respuesta.status_code == 403
    assert datos["cerveza"].precio == 3500


def test_el_administrador_si_puede_cambiar_precios(como, datos):
    admin = como("admin")
    respuesta = admin.patch(f"/api/productos/{datos['cerveza'].id}", json={"precio": 4000})

    assert respuesta.status_code == 200
    assert respuesta.json()["precio"] == 4000


def test_el_administrador_tambien_puede_cobrar(como, datos):
    admin = como("admin")
    respuesta = admin.post(
        "/api/ventas",
        json={
            "tipo": "mostrador",
            "metodo_pago": "efectivo",
            "items": [{"producto_id": datos["cerveza"].id, "cantidad": 1}],
        },
    )
    assert respuesta.status_code == 201
