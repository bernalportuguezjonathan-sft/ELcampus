from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/ventas", tags=["ventas"])


def _redondear_pesos(valor: float) -> float:
    # El peso colombiano no maneja centavos en caja.
    return float(round(valor))


def _precio_de_producto(producto: models.Producto) -> float:
    if producto.tipo_venta == models.TipoVenta.peso:
        return producto.precio_por_kg
    return producto.precio


@router.post("", response_model=schemas.VentaLeer, status_code=201)
def crear_venta(datos: schemas.VentaCrear, db: Session = Depends(get_db)):
    if not datos.items:
        raise HTTPException(status_code=400, detail="La venta no puede ir vacía")

    if db.get(models.Usuario, datos.vendedor_id) is None:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado")

    # Escanear el mismo código dos veces suma cantidad en una sola línea,
    # en vez de repetir la línea en el recibo.
    consolidados: dict[tuple[str, int], float] = {}
    for item in datos.items:
        clave = ("producto", item.producto_id) if item.producto_id else ("plato", item.plato_id)
        consolidados[clave] = consolidados.get(clave, 0.0) + item.cantidad

    # Se calcula y valida todo antes de tocar la base: si algo falla, no queda
    # ninguna escritura a medias.
    lineas: list[dict] = []
    total = 0.0
    for (tipo, id_), cantidad in consolidados.items():
        if tipo == "producto":
            producto = db.get(models.Producto, id_)
            if producto is None:
                raise HTTPException(status_code=404, detail=f"Producto {id_} no encontrado")
            precio_unitario = _precio_de_producto(producto)
        else:
            plato = db.get(models.Plato, id_)
            if plato is None:
                raise HTTPException(status_code=404, detail=f"Plato {id_} no encontrado")
            producto = None
            precio_unitario = plato.precio

        subtotal = _redondear_pesos(cantidad * precio_unitario)
        total += subtotal
        lineas.append(
            {
                "producto": producto,
                "producto_id": id_ if tipo == "producto" else None,
                "plato_id": id_ if tipo == "plato" else None,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "subtotal": subtotal,
            }
        )

    venta = models.Venta(
        tipo=datos.tipo,
        mesa=datos.mesa,
        total=_redondear_pesos(total),
        metodo_pago=datos.metodo_pago,
        vendedor_id=datos.vendedor_id,
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
            # bloquea por un conteo desactualizado, se cobra y se corrige el
            # inventario después.
            producto.stock_actual -= linea["cantidad"]
            db.add(
                models.MovimientoInventario(
                    producto_id=producto.id,
                    tipo=models.TipoMovimientoInventario.salida,
                    cantidad=linea["cantidad"],
                    usuario_id=datos.vendedor_id,
                )
            )

    db.commit()
    db.refresh(venta)
    return venta


@router.get("", response_model=list[schemas.VentaLeer])
def listar_ventas(limite: int = 50, db: Session = Depends(get_db)):
    return db.scalars(
        select(models.Venta).order_by(models.Venta.id.desc()).limit(limite)
    ).all()


@router.get("/{venta_id}", response_model=schemas.VentaLeer)
def obtener_venta(venta_id: int, db: Session = Depends(get_db)):
    venta = db.get(models.Venta, venta_id)
    if venta is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return venta


@router.post("/{venta_id}/anular", response_model=schemas.VentaLeer)
def anular_venta(venta_id: int, datos: schemas.VentaAnular, db: Session = Depends(get_db)):
    venta = db.get(models.Venta, venta_id)
    if venta is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if venta.anulada:
        raise HTTPException(status_code=409, detail="Esa venta ya está anulada")
    if db.get(models.Usuario, datos.usuario_id) is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    for detalle in venta.detalles:
        if detalle.producto_id is None:
            continue
        producto = db.get(models.Producto, detalle.producto_id)
        producto.stock_actual += detalle.cantidad
        db.add(
            models.MovimientoInventario(
                producto_id=producto.id,
                tipo=models.TipoMovimientoInventario.entrada,
                cantidad=detalle.cantidad,
                usuario_id=datos.usuario_id,
            )
        )

    venta.anulada = True
    venta.motivo_anulacion = datos.motivo
    venta.anulada_por_id = datos.usuario_id
    venta.anulada_en = datetime.now()

    db.commit()
    db.refresh(venta)
    return venta
