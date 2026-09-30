"""Pone la base al día sin borrar lo que ya tiene dentro.

Uso:  .venv\\Scripts\\python.exe migrar.py

Se puede correr las veces que haga falta: cada paso mira primero si ya está
hecho. El proyecto todavía no usa Alembic, y `create_all` crea tablas nuevas
pero no agrega columnas a las que ya existen — de ahí este archivo.
"""

import sys

from sqlalchemy import text

from app.database import engine


def columnas(con, tabla: str) -> set[str]:
    return {fila[1] for fila in con.execute(text(f"PRAGMA table_info({tabla})"))}


def main() -> int:
    hechos = []

    with engine.begin() as con:
        # --- correo de usuario (opcional, único) ---
        if "correo" not in columnas(con, "usuarios"):
            con.execute(text("ALTER TABLE usuarios ADD COLUMN correo VARCHAR(180)"))
            hechos.append("usuarios.correo agregada")

        # El índice único va aparte: SQLite no deja añadir la restricción en
        # el ALTER, pero un índice único hace exactamente lo mismo. Y es
        # parcial para que varios usuarios sin correo no choquen entre sí.
        indices = {fila[1] for fila in con.execute(text("PRAGMA index_list(usuarios)"))}
        if "ix_usuarios_correo" not in indices:
            con.execute(
                text(
                    "CREATE UNIQUE INDEX ix_usuarios_correo ON usuarios(correo) "
                    "WHERE correo IS NOT NULL"
                )
            )
            hechos.append("índice único de correo creado")

        if "ix_usuarios_nombre" not in indices:
            con.execute(
                text("CREATE UNIQUE INDEX ix_usuarios_nombre ON usuarios(nombre)")
            )
            hechos.append("índice único de nombre creado")

        # --- platos: qué trae y si el precio lo pone quien toma el pedido ---
        if "descripcion" not in columnas(con, "platos"):
            con.execute(text("ALTER TABLE platos ADD COLUMN descripcion VARCHAR(300)"))
            hechos.append("platos.descripcion agregada")

        if "precio_libre" not in columnas(con, "platos"):
            con.execute(
                text(
                    "ALTER TABLE platos ADD COLUMN precio_libre BOOLEAN "
                    "NOT NULL DEFAULT 0"
                )
            )
            hechos.append("platos.precio_libre agregada")

        # --- qué productos se pueden pedir desde una mesa ---
        if "en_carta" not in columnas(con, "productos"):
            con.execute(
                text(
                    "ALTER TABLE productos ADD COLUMN en_carta BOOLEAN "
                    "NOT NULL DEFAULT 0"
                )
            )
            hechos.append("productos.en_carta agregada")

        # --- el precio de un ítem de mesa se congela al pedirlo ---
        if "precio_fijado" not in columnas(con, "detalle_pedido_mesa"):
            con.execute(
                text("ALTER TABLE detalle_pedido_mesa ADD COLUMN precio_fijado FLOAT")
            )
            hechos.append("detalle_pedido_mesa.precio_fijado agregada")

        # --- una venta puede pagarse con varias cosas a la vez ---
        tablas = {
            fila[0]
            for fila in con.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        if "pagos_venta" not in tablas:
            con.execute(
                text(
                    """
                    CREATE TABLE pagos_venta (
                        id INTEGER NOT NULL PRIMARY KEY,
                        venta_id INTEGER NOT NULL REFERENCES ventas(id),
                        metodo_pago VARCHAR(10) NOT NULL,
                        monto FLOAT NOT NULL,
                        CONSTRAINT ck_pago_venta_monto_positivo CHECK (monto > 0)
                    )
                    """
                )
            )
            con.execute(
                text("CREATE INDEX ix_pagos_venta_venta_id ON pagos_venta(venta_id)")
            )
            hechos.append("tabla pagos_venta creada")

        # Las ventas que ya existían se pasan a la tabla nueva con su método y
        # su total: así los reportes y el cierre de caja siguen cuadrando desde
        # el primer día y no hay que tratar aparte a las viejas.
        faltantes = con.execute(
            text(
                "SELECT COUNT(*) FROM ventas v "
                "WHERE NOT EXISTS (SELECT 1 FROM pagos_venta p WHERE p.venta_id = v.id)"
            )
        ).scalar_one()
        if faltantes:
            con.execute(
                text(
                    "INSERT INTO pagos_venta (venta_id, metodo_pago, monto) "
                    "SELECT v.id, v.metodo_pago, v.total FROM ventas v "
                    "WHERE v.total > 0 AND NOT EXISTS "
                    "(SELECT 1 FROM pagos_venta p WHERE p.venta_id = v.id)"
                )
            )
            hechos.append(f"{faltantes} ventas anteriores pasadas a pagos_venta")

    if hechos:
        for h in hechos:
            print(f"  · {h}")
        print("\nBase actualizada.")
    else:
        print("La base ya estaba al día. No se cambió nada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
