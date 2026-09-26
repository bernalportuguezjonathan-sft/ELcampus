"""Qué productos puede pedir el mesero desde una mesa.

El negocio es supermercado entre semana y restaurante los fines de semana.
El mesero solo debe ver lo que se pide sentado —las bebidas— y no el
mercado, que se vende escaneándolo en la caja.
"""

from app import models


def test_un_producto_nuevo_no_entra_a_la_carta_por_defecto(como, datos):
    """Se marca a propósito: si no, el mercado entero le saldría al mesero."""
    respuesta = como("admin").post(
        "/api/productos",
        json={"codigo_barras": "111", "nombre": "Arroz 500g", "precio": 3000},
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["en_carta"] is False


def test_se_puede_crear_marcado(como, datos):
    respuesta = como("admin").post(
        "/api/productos",
        json={
            "codigo_barras": "222",
            "nombre": "Cerveza Club Colombia",
            "precio": 4500,
            "en_carta": True,
        },
    )
    assert respuesta.json()["en_carta"] is True


def test_el_filtro_devuelve_solo_lo_de_la_mesa(como, db, datos):
    admin = como("admin")
    admin.post(
        "/api/productos",
        json={"codigo_barras": "333", "nombre": "Cerveza Poker", "precio": 3500, "en_carta": True},
    )
    admin.post(
        "/api/productos",
        json={"codigo_barras": "444", "nombre": "Panela", "precio": 5000},
    )

    de_mesa = {p["nombre"] for p in admin.get("/api/productos?en_carta=true").json()}
    assert de_mesa == {"Cerveza Poker"}


def test_sin_filtro_sale_todo_el_catalogo(como, datos):
    admin = como("admin")
    admin.post(
        "/api/productos",
        json={"codigo_barras": "555", "nombre": "Panela", "precio": 5000},
    )
    todo = {p["nombre"] for p in admin.get("/api/productos").json()}
    assert "Panela" in todo
    assert "Cerveza Aguila 330ml" in todo


def test_el_admin_puede_marcarlo_despues(como, datos):
    """Se le olvidó al crearlo y lo corrige sin tener que borrarlo."""
    admin = como("admin")
    creado = admin.post(
        "/api/productos",
        json={"codigo_barras": "666", "nombre": "Gaseosa 1.5L", "precio": 6000},
    ).json()

    admin.patch(f"/api/productos/{creado['id']}", json={"en_carta": True})
    de_mesa = {p["nombre"] for p in admin.get("/api/productos?en_carta=true").json()}
    assert "Gaseosa 1.5L" in de_mesa


def test_el_admin_puede_sacarlo_de_la_carta(como, datos):
    admin = como("admin")
    creado = admin.post(
        "/api/productos",
        json={"codigo_barras": "777", "nombre": "Michelada", "precio": 9000, "en_carta": True},
    ).json()

    admin.patch(f"/api/productos/{creado['id']}", json={"en_carta": False})
    assert admin.get("/api/productos?en_carta=true").json() == []


def test_el_mesero_puede_consultar_la_carta(como, db, datos):
    """Es lo que carga su celular al abrir una mesa."""
    datos["cerveza"].en_carta = True
    db.commit()

    respuesta = como("mesero").get("/api/productos?en_carta=true")
    assert respuesta.status_code == 200
    assert [p["nombre"] for p in respuesta.json()] == ["Cerveza Aguila 330ml"]


def test_el_mesero_no_puede_cambiar_la_carta(como, datos):
    respuesta = como("mesero").patch(
        f"/api/productos/{datos['cerveza'].id}", json={"en_carta": True}
    )
    assert respuesta.status_code == 403


def test_una_bebida_de_carta_se_puede_pedir_en_la_mesa(como, db, datos):
    """La prueba de fondo: que sirva para lo que es."""
    datos["cerveza"].en_carta = True
    db.commit()

    respuesta = como("mesero").post(
        "/api/pedidos/enviar",
        json={"mesa": 6, "items": [{"producto_id": datos["cerveza"].id, "cantidad": 3}]},
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["total"] == 10500


def test_marcarlo_no_le_quita_el_codigo_de_barras(como, db, datos):
    """Una bebida de mesa se sigue pudiendo escanear en la caja."""
    datos["cerveza"].en_carta = True
    db.commit()

    respuesta = como("admin").get("/api/productos/codigo/7701234567890")
    assert respuesta.status_code == 200
    assert respuesta.json()["en_carta"] is True
