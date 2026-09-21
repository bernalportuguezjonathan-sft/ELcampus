"""Reglas de negocio que usan varios routers.

Vive aparte para que cobrar en el mostrador y cobrar una mesa pasen
exactamente por el mismo camino: mismo cálculo, mismo descuento de stock,
mismo registro de movimientos.
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models


def redondear_pesos(valor: float) -> float:
    # El peso colombiano no maneja centavos en caja.
    return float(round(valor))


def consolidar(items) -> dict[tuple[str, int], float]:
    """Escanear el mismo producto dos veces suma cantidad en una sola línea."""
    consolidados: dict[tuple[str, int], float] = {}
    for item in items:
        clave = ("producto", item.producto_id) if item.producto_id else ("plato", item.plato_id)
        consolidados[clave] = consolidados.get(clave, 0.0) + item.cantidad
    return consolidados


def _resolver(db: Session, consolidados: dict[tuple[str, int], float]) -> list[dict]:
    lineas = []
    for (tipo, id_), cantidad in consolidados.items():
        if tipo == "producto":
            producto = db.get(models.Producto, id_)
            if producto is None:
                raise HTTPException(status_code=404, detail=f"Producto {id_} no encontrado")
            precio_unitario = producto.precio_de_venta
        else:
            plato = db.get(models.Plato, id_)
            if plato is None:
                raise HTTPException(status_code=404, detail=f"Plato {id_} no encontrado")
            producto = None
            precio_unitario = plato.precio

        lineas.append(
            {
                "producto": producto,
                "producto_id": id_ if tipo == "producto" else None,
                "plato_id": id_ if tipo == "plato" else None,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "subtotal": redondear_pesos(cantidad * precio_unitario),
            }
        )
    return lineas


def registrar_venta(
    db: Session,
    *,
    vendedor: models.Usuario,
    tipo: models.TipoCobro,
    metodo_pago: models.MetodoPago,
    mesa: int | None,
    items,
) -> models.Venta:
    """Cobra y devuelve la venta.

    Todo el cálculo y la validación ocurren antes de escribir: si algo falla,
    no queda ni media venta guardada. El commit lo hace quien llama, para que
    cobrar una mesa (venta + cerrar el pedido) sea una sola operación.
    """
    if not items:
        raise HTTPException(status_code=400, detail="La venta no puede ir vacía")

    lineas = _resolver(db, consolidar(items))
    total = redondear_pesos(sum(linea["subtotal"] for linea in lineas))

    venta = models.Venta(
        tipo=tipo,
        mesa=mesa,
        total=total,
        metodo_pago=metodo_pago,
        vendedor_id=vendedor.id,
    )
    db.add(venta)
    db.flush()

    for linea in lineas:
        db.add(
            models.DetalleVenta(
                venta_id=venta.id,
                producto_id=linea["producto_id"],
                plato_id=linea["plato_id"],
                cantidad=linea["cantidad"],
                precio_unitario=linea["precio_unitario"],
                subtotal=linea["subtotal"],
            )
        )
        producto = linea["producto"]
        if producto is not None:
            # El stock puede quedar negativo a propósito: la caja nunca se
            # bloquea por un conteo desactualizado. Se cobra y se corrige
            # el inventario después.
            producto.stock_actual -= linea["cantidad"]
            db.add(
                models.MovimientoInventario(
                    producto_id=producto.id,
                    tipo=models.TipoMovimientoInventario.salida,
                    cantidad=linea["cantidad"],
                    usuario_id=vendedor.id,
                )
            )

    return venta


def productos_en_alerta(db: Session) -> list[models.Producto]:
    return list(
        db.scalars(
            select(models.Producto)
            .where(models.Producto.stock_actual <= models.Producto.alerta_minima)
            .order_by(models.Producto.stock_actual)
        )
    )
