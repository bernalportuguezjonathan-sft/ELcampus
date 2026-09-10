def _cobrar(client, vendedor_id, items, **extra):
    cuerpo = {
        "tipo": "mostrador",
        "metodo_pago": "efectivo",
        "vendedor_id": vendedor_id,
        "items": items,
        **extra,
    }
    return client.post("/ventas", json=cuerpo)


def test_venta_simple_calcula_total_y_descuenta_stock(client, datos):
    respuesta = _cobrar(
        client,
        datos["vendedor"].id,
        [{"producto_id": datos["cerveza"].id, "cantidad": 3}],
    )

    assert respuesta.status_code == 201
    venta = respuesta.json()
    assert venta["total"] == 10500
    assert len(venta["detalles"]) == 1
    assert venta["detalles"][0]["nombre"] == "Cerveza Aguila 330ml"
    assert datos["cerveza"].stock_actual == 97


def test_escanear_dos_veces_suma_en_una_sola_linea(client, datos):
    respuesta = _cobrar(
        client,
        datos["vendedor"].id,
        [
            {"producto_id": datos["cerveza"].id, "cantidad": 1},
            {"producto_id": datos["cerveza"].id, "cantidad": 1},
        ],
    )

    venta = respuesta.json()
    assert len(venta["detalles"]) == 1
    assert venta["detalles"][0]["cantidad"] == 2
    assert venta["total"] == 7000


def test_producto_por_peso_se_cobra_por_kilo(client, datos):
    respuesta = _cobrar(
        client,
        datos["vendedor"].id,
        [{"producto_id": datos["morraja"].id, "cantidad": 0.35}],
    )

    venta = respuesta.json()
    assert venta["detalles"][0]["precio_unitario"] == 18000
    assert venta["detalles"][0]["subtotal"] == 6300
    assert datos["morraja"].stock_actual == 19.65


def test_venta_mixta_de_plato_y_producto(client, datos):
    respuesta = _cobrar(
        client,
        datos["vendedor"].id,
        [
            {"plato_id": datos["picada"].id, "cantidad": 1},
            {"producto_id": datos["cerveza"].id, "cantidad": 2},
        ],
        tipo="restaurante",
        mesa=7,
    )

    venta = respuesta.json()
    assert venta["total"] == 52000
    assert venta["mesa"] == 7
    # El plato no mueve inventario, solo el producto.
    assert datos["cerveza"].stock_actual == 98


def test_anular_devuelve_el_stock_y_deja_rastro(client, datos):
    venta = _cobrar(
        client,
        datos["vendedor"].id,
        [{"producto_id": datos["cerveza"].id, "cantidad": 5}],
    ).json()
    assert datos["cerveza"].stock_actual == 95

    respuesta = client.post(
        f"/ventas/{venta['id']}/anular",
        json={"usuario_id": datos["vendedor"].id, "motivo": "El cliente se arrepintió"},
    )

    assert respuesta.status_code == 200
    anulada = respuesta.json()
    assert anulada["anulada"] is True
    assert anulada["motivo_anulacion"] == "El cliente se arrepintió"
    assert datos["cerveza"].stock_actual == 100


def test_no_se_puede_anular_dos_veces(client, datos):
    venta = _cobrar(
        client,
        datos["vendedor"].id,
        [{"producto_id": datos["cerveza"].id, "cantidad": 1}],
    ).json()
    cuerpo = {"usuario_id": datos["vendedor"].id, "motivo": "error de digitación"}

    client.post(f"/ventas/{venta['id']}/anular", json=cuerpo)
    segunda = client.post(f"/ventas/{venta['id']}/anular", json=cuerpo)

    assert segunda.status_code == 409
    assert datos["cerveza"].stock_actual == 100


def test_venta_vacia_se_rechaza(client, datos):
    assert _cobrar(client, datos["vendedor"].id, []).status_code == 400


def test_item_sin_producto_ni_plato_se_rechaza(client, datos):
    respuesta = _cobrar(client, datos["vendedor"].id, [{"cantidad": 1}])
    assert respuesta.status_code == 422


def test_producto_inexistente_no_deja_venta_a_medias(client, db, datos):
    from app import models

    respuesta = _cobrar(
        client,
        datos["vendedor"].id,
        [
            {"producto_id": datos["cerveza"].id, "cantidad": 1},
            {"producto_id": 9999, "cantidad": 1},
        ],
    )

    assert respuesta.status_code == 404
    assert datos["cerveza"].stock_actual == 100
    assert db.query(models.Venta).count() == 0
