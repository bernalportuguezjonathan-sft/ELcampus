"""El listado de mesas del día que ve el administrador.

Quiere ver el salón completo: qué mesas se atendieron, quién las atendió,
qué pidió cada una y cuánto costó. Las cobradas y las que siguen abiertas.
"""

from datetime import datetime, timedelta

from app import models


def enviar(c, mesa, items):
    return c.post("/api/pedidos/enviar", json={"mesa": mesa, "items": items})


def test_una_mesa_recien_abierta_ya_aparece(como, datos):
    mesero = como("mesero")
    enviar(mesero, 4, [{"plato_id": datos["picada"].id, "cantidad": 2}])

    reporte = como("admin").get("/api/reportes/mesas").json()

    assert reporte["cuantas"] == 1
    assert reporte["total"] == 90000
    mesa = reporte["mesas"][0]
    assert mesa["mesa"] == 4
    assert mesa["estado"] == "abierto"


def test_sale_quien_atendio_la_mesa(como, datos):
    enviar(como("mesero"), 4, [{"plato_id": datos["picada"].id, "cantidad": 1}])

    mesa = como("admin").get("/api/reportes/mesas").json()["mesas"][0]
    assert mesa["mesero_nombre"] == "mesero"


def test_sale_el_detalle_con_el_precio_de_cada_cosa(como, datos):
    enviar(
        como("mesero"),
        4,
        [
            {"plato_id": datos["picada"].id, "cantidad": 2},
            {"producto_id": datos["cerveza"].id, "cantidad": 3},
        ],
    )

    mesa = como("admin").get("/api/reportes/mesas").json()["mesas"][0]
    porNombre = {d["nombre"]: d for d in mesa["detalles"]}

    assert porNombre["Picada"]["cantidad"] == 2
    assert porNombre["Picada"]["precio_unitario"] == 45000
    assert porNombre["Picada"]["subtotal"] == 90000

    assert porNombre["Cerveza Aguila 330ml"]["precio_unitario"] == 3500
    assert porNombre["Cerveza Aguila 330ml"]["subtotal"] == 10500

    assert mesa["total"] == 100500


def test_una_mesa_ya_cobrada_sigue_en_el_listado(como, datos):
    """El administrador revisa el día entero, no solo lo que está abierto."""
    mesero = como("mesero")
    admin = como("admin")
    pedido = enviar(mesero, 4, [{"plato_id": datos["picada"].id, "cantidad": 1}]).json()
    admin.post(f"/api/pedidos/{pedido['id']}/cobrar", json={"metodo_pago": "efectivo"})

    reporte = admin.get("/api/reportes/mesas").json()
    assert reporte["cuantas"] == 1
    assert reporte["mesas"][0]["estado"] == "pagado"


def test_varias_mesas_suman_al_total(como, datos):
    mesero = como("mesero")
    enviar(mesero, 4, [{"plato_id": datos["picada"].id, "cantidad": 1}])
    enviar(mesero, 8, [{"producto_id": datos["cerveza"].id, "cantidad": 2}])

    reporte = como("admin").get("/api/reportes/mesas").json()
    assert reporte["cuantas"] == 2
    assert reporte["total"] == 45000 + 7000
    assert sorted(m["mesa"] for m in reporte["mesas"]) == [4, 8]


def test_las_mesas_de_ayer_no_entran(como, db, datos):
    mesero = como("mesero")
    pedido = enviar(mesero, 4, [{"plato_id": datos["picada"].id, "cantidad": 1}]).json()

    de_ayer = db.get(models.PedidoMesa, pedido["id"])
    de_ayer.hora_apertura = datetime.now() - timedelta(days=1)
    db.commit()

    reporte = como("admin").get("/api/reportes/mesas").json()
    assert reporte["cuantas"] == 0
    assert reporte["total"] == 0


def test_se_puede_pedir_el_de_otro_dia(como, db, datos):
    mesero = como("mesero")
    pedido = enviar(mesero, 4, [{"plato_id": datos["picada"].id, "cantidad": 1}]).json()

    ayer = (datetime.now() - timedelta(days=1)).date()
    db.get(models.PedidoMesa, pedido["id"]).hora_apertura = datetime.combine(
        ayer, datetime.min.time()
    ) + timedelta(hours=20)
    db.commit()

    reporte = como("admin").get(f"/api/reportes/mesas?fecha={ayer.isoformat()}").json()
    assert reporte["cuantas"] == 1


def test_un_dia_sin_mesas_responde_vacio(como, datos):
    reporte = como("admin").get("/api/reportes/mesas").json()
    assert reporte == {
        "fecha": reporte["fecha"],
        "mesas": [],
        "total": 0,
        "cuantas": 0,
    }


def test_el_vendedor_no_ve_este_reporte(cliente, datos):
    assert cliente.get("/api/reportes/mesas").status_code == 403


def test_el_mesero_tampoco(como, datos):
    assert como("mesero").get("/api/reportes/mesas").status_code == 403
