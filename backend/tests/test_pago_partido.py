"""Cobrar una venta con más de un medio de pago.

Pasa seguido: el cliente tiene algo de efectivo y el resto lo manda por
Nequi. Antes la venta guardaba un solo método, así que la plata partida
quedaba anotada toda en uno — y al cerrar el turno la caja no cuadraba.
"""

from datetime import date

from app import models


def _cobrar(cliente, items, **extra):
    cuerpo = {"tipo": "mostrador", "metodo_pago": "efectivo", "items": items, **extra}
    return cliente.post("/api/ventas", json=cuerpo)


# --------------------------------------------------------------- lo básico


def test_una_venta_normal_queda_con_un_solo_pago(cliente, datos):
    """Sin partir nada: sigue funcionando como siempre."""
    respuesta = _cobrar(cliente, [{"producto_id": datos["cerveza"].id, "cantidad": 2}])

    assert respuesta.status_code == 201
    venta = respuesta.json()
    assert venta["total"] == 7000
    assert venta["pagos"] == [{"metodo_pago": "efectivo", "monto": 7000}]


def test_se_puede_pagar_mitad_y_mitad(cliente, datos):
    respuesta = _cobrar(
        cliente,
        [{"producto_id": datos["cerveza"].id, "cantidad": 4}],  # 14.000
        pagos=[
            {"metodo_pago": "efectivo", "monto": 10000},
            {"metodo_pago": "nequi", "monto": 4000},
        ],
    )

    assert respuesta.status_code == 201
    venta = respuesta.json()
    assert venta["total"] == 14000
    assert {(p["metodo_pago"], p["monto"]) for p in venta["pagos"]} == {
        ("efectivo", 10000),
        ("nequi", 4000),
    }


def test_el_metodo_de_la_venta_queda_con_el_que_mas_pago(cliente, datos):
    """Para ver la venta de un vistazo. La plata exacta está en `pagos`."""
    respuesta = _cobrar(
        cliente,
        [{"producto_id": datos["cerveza"].id, "cantidad": 4}],
        pagos=[
            {"metodo_pago": "efectivo", "monto": 4000},
            {"metodo_pago": "nequi", "monto": 10000},
        ],
    )
    assert respuesta.json()["metodo_pago"] == "nequi"


def test_se_puede_partir_en_tres(cliente, datos):
    respuesta = _cobrar(
        cliente,
        [{"producto_id": datos["cerveza"].id, "cantidad": 4}],
        pagos=[
            {"metodo_pago": "efectivo", "monto": 5000},
            {"metodo_pago": "nequi", "monto": 5000},
            {"metodo_pago": "tarjeta", "monto": 4000},
        ],
    )
    assert respuesta.status_code == 201
    assert len(respuesta.json()["pagos"]) == 3


def test_dos_partes_del_mismo_medio_se_juntan(cliente, datos):
    """«Efectivo 10.000 + efectivo 4.000» es efectivo 14.000, no dos pagos."""
    respuesta = _cobrar(
        cliente,
        [{"producto_id": datos["cerveza"].id, "cantidad": 4}],
        pagos=[
            {"metodo_pago": "efectivo", "monto": 10000},
            {"metodo_pago": "efectivo", "monto": 4000},
        ],
    )
    assert respuesta.json()["pagos"] == [{"metodo_pago": "efectivo", "monto": 14000}]


# ------------------------------------------------- que la plata cuadre


def test_no_se_cobra_si_los_pagos_no_alcanzan(cliente, datos):
    """Cobrar de menos es plata que se pierde y nadie se entera después."""
    respuesta = _cobrar(
        cliente,
        [{"producto_id": datos["cerveza"].id, "cantidad": 4}],  # 14.000
        pagos=[
            {"metodo_pago": "efectivo", "monto": 5000},
            {"metodo_pago": "nequi", "monto": 4000},
        ],
    )
    assert respuesta.status_code == 422
    assert "faltan" in respuesta.json()["detail"]


def test_no_se_cobra_si_los_pagos_se_pasan(cliente, datos):
    respuesta = _cobrar(
        cliente,
        [{"producto_id": datos["cerveza"].id, "cantidad": 4}],
        pagos=[
            {"metodo_pago": "efectivo", "monto": 10000},
            {"metodo_pago": "nequi", "monto": 9000},
        ],
    )
    assert respuesta.status_code == 422
    assert "sobran" in respuesta.json()["detail"]


def test_un_pago_que_no_cuadra_no_deja_media_venta_guardada(cliente, db, datos):
    antes = db.query(models.Venta).count()
    stock_antes = datos["cerveza"].stock_actual

    _cobrar(
        cliente,
        [{"producto_id": datos["cerveza"].id, "cantidad": 4}],
        pagos=[{"metodo_pago": "efectivo", "monto": 1000}],
    )

    db.expire_all()
    assert db.query(models.Venta).count() == antes
    assert db.query(models.PagoVenta).count() == 0
    assert datos["cerveza"].stock_actual == stock_antes


def test_un_pago_en_cero_se_rechaza(cliente, datos):
    respuesta = _cobrar(
        cliente,
        [{"producto_id": datos["cerveza"].id, "cantidad": 4}],
        pagos=[
            {"metodo_pago": "efectivo", "monto": 14000},
            {"metodo_pago": "nequi", "monto": 0},
        ],
    )
    assert respuesta.status_code == 422


def test_un_pago_negativo_se_rechaza(cliente, datos):
    respuesta = _cobrar(
        cliente,
        [{"producto_id": datos["cerveza"].id, "cantidad": 4}],
        pagos=[
            {"metodo_pago": "efectivo", "monto": 20000},
            {"metodo_pago": "nequi", "monto": -6000},
        ],
    )
    assert respuesta.status_code == 422


# ------------------------------------------------------- mesas del restaurante


def test_una_mesa_tambien_se_puede_pagar_partida(como, cliente, datos):
    mesero = como("mesero")
    pedido = mesero.post(
        "/api/pedidos/enviar",
        json={"mesa": 4, "items": [{"plato_id": datos["picada"].id, "cantidad": 1}]},
    ).json()

    respuesta = cliente.post(
        f"/api/pedidos/{pedido['id']}/cobrar",
        json={
            "metodo_pago": "efectivo",
            "pagos": [
                {"metodo_pago": "efectivo", "monto": 20000},
                {"metodo_pago": "daviplata", "monto": 25000},
            ],
        },
    )

    # Cobrar una mesa devuelve 200: la venta es nueva, pero la mesa que se
    # cierra ya existía.
    assert respuesta.status_code == 200
    venta = respuesta.json()
    assert venta["total"] == 45000
    assert {(p["metodo_pago"], p["monto"]) for p in venta["pagos"]} == {
        ("efectivo", 20000),
        ("daviplata", 25000),
    }


def test_si_el_pago_de_la_mesa_no_cuadra_la_mesa_sigue_abierta(como, cliente, datos):
    """Lo peor sería dejarla cerrada sin haber cobrado bien."""
    mesero = como("mesero")
    pedido = mesero.post(
        "/api/pedidos/enviar",
        json={"mesa": 5, "items": [{"plato_id": datos["picada"].id, "cantidad": 1}]},
    ).json()

    respuesta = cliente.post(
        f"/api/pedidos/{pedido['id']}/cobrar",
        json={
            "metodo_pago": "efectivo",
            "pagos": [{"metodo_pago": "efectivo", "monto": 20000}],
        },
    )
    assert respuesta.status_code == 422

    sigue = cliente.get("/api/pedidos/mesa/5").json()
    assert sigue is not None
    assert sigue["estado"] == "abierto"


# ------------------------------------------------ que los reportes cuadren


def test_el_reporte_reparte_la_plata_entre_los_dos_medios(cliente, como, datos):
    _cobrar(
        cliente,
        [{"producto_id": datos["cerveza"].id, "cantidad": 4}],  # 14.000
        pagos=[
            {"metodo_pago": "efectivo", "monto": 10000},
            {"metodo_pago": "nequi", "monto": 4000},
        ],
    )

    resumen = como("admin").get("/api/reportes/dia").json()
    assert resumen["total"] == 14000
    por_metodo = {m["metodo_pago"]: m["total"] for m in resumen["por_metodo"]}
    assert por_metodo == {"efectivo": 10000, "nequi": 4000}


def test_el_cierre_de_caja_solo_espera_el_efectivo_de_verdad(cliente, datos):
    """El faltante fantasma que motivó todo esto.

    $14.000 de venta pagados con $10.000 en efectivo: en el cajón hay
    $10.000, no $14.000. Contando la venta entera, el arqueo acusaba un
    faltante de $4.000 que nadie se robó.
    """
    cliente.post("/api/caja/abrir", json={"base_inicial": 50000})

    _cobrar(
        cliente,
        [{"producto_id": datos["cerveza"].id, "cantidad": 4}],
        pagos=[
            {"metodo_pago": "efectivo", "monto": 10000},
            {"metodo_pago": "nequi", "monto": 4000},
        ],
    )

    cierre = cliente.post("/api/caja/cerrar", json={"efectivo_contado": 60000}).json()
    assert cierre["efectivo_esperado"] == 60000
    assert cierre["diferencia"] == 0


def test_una_venta_anulada_no_cuenta_en_ningun_medio(cliente, como, datos):
    venta = _cobrar(
        cliente,
        [{"producto_id": datos["cerveza"].id, "cantidad": 4}],
        pagos=[
            {"metodo_pago": "efectivo", "monto": 10000},
            {"metodo_pago": "nequi", "monto": 4000},
        ],
    ).json()

    como("admin").post(
        f"/api/ventas/{venta['id']}/anular", json={"motivo": "se equivocó de mesa"}
    )

    resumen = como("admin").get("/api/reportes/dia").json()
    assert resumen["por_metodo"] == []


def test_la_venta_partida_cuenta_una_vez_en_cada_medio(cliente, como, datos):
    """`cantidad` es en cuántas ventas se usó ese medio, no cuántas ventas hubo."""
    _cobrar(
        cliente,
        [{"producto_id": datos["cerveza"].id, "cantidad": 4}],
        pagos=[
            {"metodo_pago": "efectivo", "monto": 10000},
            {"metodo_pago": "nequi", "monto": 4000},
        ],
    )

    resumen = como("admin").get(f"/api/reportes/dia?fecha={date.today()}").json()
    cuantas = {m["metodo_pago"]: m["cantidad"] for m in resumen["por_metodo"]}
    assert cuantas == {"efectivo": 1, "nequi": 1}
