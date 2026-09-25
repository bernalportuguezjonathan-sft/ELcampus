"""La carta completa vive en el sistema; el menú lo arma el administrador.

El negocio cambia de platos cada fin de semana. Solo tres son fijos. El
resto está en la carta y el administrador elige cuáles salen, para que al
mesero le aparezca únicamente lo que hoy se puede pedir.
"""

from datetime import date, timedelta

import pytest

from app import models


@pytest.fixture
def carta(db, datos):
    """Tres especiales guardados en la carta, ninguno puesto todavía."""
    platos = {
        "sancocho": models.Plato(
            nombre="Sancocho de gallina", precio=28000, tipo=models.TipoPlato.especial
        ),
        "bandeja": models.Plato(
            nombre="Bandeja paisa", precio=32000, tipo=models.TipoPlato.especial
        ),
        "cazuela": models.Plato(
            nombre="Cazuela de mariscos", precio=38000, tipo=models.TipoPlato.especial
        ),
    }
    db.add_all(platos.values())
    db.commit()
    for p in platos.values():
        db.refresh(p)
    return platos


def menu_visible(c):
    return {p["nombre"] for p in c.get("/api/platos").json()}


def carta_completa(c):
    return {p["nombre"] for p in c.get("/api/platos?solo_vigentes=false").json()}


# --------------------------------------------- la carta no es el menú


def test_un_especial_guardado_no_le_sale_al_mesero(como, carta):
    """Está en la carta, pero nadie lo ha sacado para este fin de semana."""
    mesero = como("mesero")
    assert "Sancocho de gallina" not in menu_visible(mesero)
    assert "Sancocho de gallina" in carta_completa(mesero)


def test_los_fijos_salen_siempre(como, carta, datos):
    assert "Picada" in menu_visible(como("mesero"))


# ------------------------------------------------- publicar el menú


def test_el_admin_saca_los_platos_del_fin_de_semana(como, carta):
    hoy = date.today()
    respuesta = como("admin").post(
        "/api/platos/menu",
        json={
            "desde": hoy.isoformat(),
            "hasta": (hoy + timedelta(days=2)).isoformat(),
            "platos": [carta["sancocho"].id, carta["bandeja"].id],
        },
    )

    assert respuesta.status_code == 200
    visible = menu_visible(como("mesero"))
    assert "Sancocho de gallina" in visible
    assert "Bandeja paisa" in visible
    assert "Cazuela de mariscos" not in visible


def test_publicar_de_nuevo_saca_lo_que_ya_no_va(como, carta):
    """El especial de la semana pasada no se queda colgado."""
    admin = como("admin")
    hoy = date.today()
    rango = {"desde": hoy.isoformat(), "hasta": (hoy + timedelta(days=2)).isoformat()}

    admin.post("/api/platos/menu", json={**rango, "platos": [carta["sancocho"].id]})
    assert "Sancocho de gallina" in menu_visible(como("mesero"))

    admin.post("/api/platos/menu", json={**rango, "platos": [carta["cazuela"].id]})
    visible = menu_visible(como("mesero"))
    assert "Sancocho de gallina" not in visible
    assert "Cazuela de mariscos" in visible


def test_publicar_sin_platos_deja_solo_los_fijos(como, carta):
    hoy = date.today()
    como("admin").post(
        "/api/platos/menu",
        json={"desde": hoy.isoformat(), "hasta": hoy.isoformat(), "platos": []},
    )
    # Solo queda lo fijo. En las pruebas el único fijo es la picada.
    assert menu_visible(como("mesero")) == {"Picada"}


def test_lo_sacado_sigue_en_la_carta(como, carta):
    """Sacarlo del menú no lo borra: la próxima semana vuelve a estar."""
    hoy = date.today()
    admin = como("admin")
    admin.post(
        "/api/platos/menu",
        json={"desde": hoy.isoformat(), "hasta": hoy.isoformat(), "platos": []},
    )
    assert "Sancocho de gallina" in carta_completa(admin)


# ------------------------------------------------------ las fechas


def test_el_menu_de_la_semana_pasada_se_apaga_solo(como, db, carta):
    """Nadie tiene que acordarse el lunes de apagar el especial."""
    hoy = date.today()
    carta["sancocho"].activo_desde = hoy - timedelta(days=9)
    carta["sancocho"].activo_hasta = hoy - timedelta(days=7)
    db.commit()

    assert "Sancocho de gallina" not in menu_visible(como("mesero"))


def test_un_menu_programado_para_despues_no_se_adelanta(como, db, carta):
    hoy = date.today()
    carta["bandeja"].activo_desde = hoy + timedelta(days=3)
    carta["bandeja"].activo_hasta = hoy + timedelta(days=5)
    db.commit()

    assert "Bandeja paisa" not in menu_visible(como("mesero"))


def test_las_fechas_al_reves_se_rechazan(como, carta):
    hoy = date.today()
    respuesta = como("admin").post(
        "/api/platos/menu",
        json={
            "desde": hoy.isoformat(),
            "hasta": (hoy - timedelta(days=1)).isoformat(),
            "platos": [carta["sancocho"].id],
        },
    )
    assert respuesta.status_code == 422


def test_no_se_puede_publicar_un_plato_que_no_existe(como, carta):
    hoy = date.today()
    respuesta = como("admin").post(
        "/api/platos/menu",
        json={"desde": hoy.isoformat(), "hasta": hoy.isoformat(), "platos": [99999]},
    )
    assert respuesta.status_code == 404


def test_un_plato_fijo_no_se_maneja_por_aqui(como, carta, datos):
    """Los fijos van siempre; mandarlos aquí es un error, no un apagado."""
    hoy = date.today()
    respuesta = como("admin").post(
        "/api/platos/menu",
        json={
            "desde": hoy.isoformat(),
            "hasta": hoy.isoformat(),
            "platos": [datos["picada"].id],
        },
    )
    assert respuesta.status_code == 404
    assert "Picada" in menu_visible(como("mesero"))


# ------------------------------------------------------- permisos


def test_el_mesero_no_arma_el_menu(como, carta):
    hoy = date.today()
    respuesta = como("mesero").post(
        "/api/platos/menu",
        json={"desde": hoy.isoformat(), "hasta": hoy.isoformat(), "platos": []},
    )
    assert respuesta.status_code == 403


def test_el_vendedor_tampoco(cliente, carta):
    hoy = date.today()
    respuesta = cliente.post(
        "/api/platos/menu",
        json={"desde": hoy.isoformat(), "hasta": hoy.isoformat(), "platos": []},
    )
    assert respuesta.status_code == 403
