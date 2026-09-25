"""Platos de precio libre, y el precio que queda congelado al pedir.

Dos cosas distintas que se tocan:

1. La picada va "desde $40.000": quien toma el pedido escribe cuánto vale,
   con el precio del catálogo como piso.

2. Lo que se pidió cuesta lo que costaba cuando se pidió. Si el
   administrador sube un precio a mitad de servicio, la mesa que ya estaba
   abierta no cambia de cuenta.
"""

import pytest

from app import models


@pytest.fixture
def picada_libre(db, datos):
    """La picada, cobrada por precio libre desde $40.000."""
    plato = datos["picada"]
    plato.precio = 40000
    plato.precio_libre = True
    db.commit()
    return plato


def enviar(c, mesa, items):
    return c.post("/api/pedidos/enviar", json={"mesa": mesa, "items": items})


# ------------------------------------------------------- precio libre


def test_la_picada_se_cobra_a_lo_que_diga_el_mesero(como, picada_libre):
    respuesta = enviar(
        como("mesero"),
        3,
        [{"plato_id": picada_libre.id, "cantidad": 1, "precio_unitario": 55000}],
    )

    assert respuesta.status_code == 201
    pedido = respuesta.json()
    assert pedido["total"] == 55000
    assert pedido["detalles"][0]["precio_unitario"] == 55000


def test_sin_precio_no_deja_pedir_la_picada(como, db, picada_libre):
    respuesta = enviar(como("mesero"), 3, [{"plato_id": picada_libre.id, "cantidad": 1}])

    assert respuesta.status_code == 422
    assert "precio libre" in respuesta.json()["detail"]
    # y la mesa no quedó abierta a medias
    assert db.query(models.PedidoMesa).count() == 0


def test_no_se_puede_cobrar_por_debajo_del_minimo(como, db, picada_libre):
    respuesta = enviar(
        como("mesero"),
        3,
        [{"plato_id": picada_libre.id, "cantidad": 1, "precio_unitario": 25000}],
    )

    assert respuesta.status_code == 422
    assert db.query(models.PedidoMesa).count() == 0


def test_el_minimo_exacto_sí_pasa(como, picada_libre):
    respuesta = enviar(
        como("mesero"),
        3,
        [{"plato_id": picada_libre.id, "cantidad": 1, "precio_unitario": 40000}],
    )
    assert respuesta.status_code == 201


def test_dos_picadas_de_precios_distintos_conviven(como, picada_libre, datos):
    mesero = como("mesero")
    enviar(mesero, 3, [{"plato_id": picada_libre.id, "cantidad": 1, "precio_unitario": 40000}])
    segunda = enviar(
        mesero, 3, [{"plato_id": picada_libre.id, "cantidad": 1, "precio_unitario": 70000}]
    )

    detalles = segunda.json()["detalles"]
    # No se fusionan: son dos picadas distintas aunque sean el mismo plato.
    assert sorted(d["precio_unitario"] for d in detalles) == [40000, 70000]
    assert segunda.json()["total"] == 110000


def test_un_plato_normal_ignora_el_precio_que_le_manden(como, datos):
    """Nadie rebaja la pechuga escribiendo otro número."""
    respuesta = enviar(
        como("mesero"),
        3,
        [{"plato_id": datos["picada"].id, "cantidad": 1, "precio_unitario": 1}],
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["detalles"][0]["precio_unitario"] == 45000


# --------------------------------------------- el precio queda congelado


def test_subir_el_precio_no_le_mueve_la_cuenta_a_una_mesa_abierta(como, db, datos):
    """Lo que el cliente pidió cuesta lo que le dijeron que costaba."""
    mesero = como("mesero")
    pedido = enviar(mesero, 3, [{"plato_id": datos["picada"].id, "cantidad": 2}]).json()
    assert pedido["total"] == 90000

    datos["picada"].precio = 60000
    db.commit()

    de_nuevo = mesero.get(f"/api/pedidos/{pedido['id']}").json()
    assert de_nuevo["total"] == 90000, "la mesa abierta cambió de precio sola"


def test_lo_que_se_pida_despues_sí_usa_el_precio_nuevo(como, db, datos):
    mesero = como("mesero")
    enviar(mesero, 3, [{"plato_id": datos["picada"].id, "cantidad": 1}])

    datos["picada"].precio = 60000
    db.commit()

    segunda = enviar(mesero, 3, [{"plato_id": datos["picada"].id, "cantidad": 1}])
    precios = sorted(d["precio_unitario"] for d in segunda.json()["detalles"])
    assert precios == [45000, 60000]


def test_el_producto_tambien_congela_su_precio(como, db, datos):
    mesero = como("mesero")
    pedido = enviar(mesero, 3, [{"producto_id": datos["cerveza"].id, "cantidad": 2}]).json()
    assert pedido["total"] == 7000

    datos["cerveza"].precio = 9000
    db.commit()

    de_nuevo = mesero.get(f"/api/pedidos/{pedido['id']}").json()
    assert de_nuevo["total"] == 7000


def test_al_cobrar_la_mesa_se_cobra_el_precio_congelado(como, db, datos):
    mesero = como("mesero")
    admin = como("admin")
    pedido = enviar(mesero, 3, [{"plato_id": datos["picada"].id, "cantidad": 1}]).json()

    datos["picada"].precio = 99000
    db.commit()

    venta = admin.post(
        f"/api/pedidos/{pedido['id']}/cobrar", json={"metodo_pago": "efectivo"}
    )
    assert venta.status_code == 200
    assert venta.json()["total"] == 45000
