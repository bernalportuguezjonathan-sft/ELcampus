from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas, servicios
from ..auth import caja, usuario_actual
from ..database import get_db

router = APIRouter(prefix="/ventas", tags=["ventas"])


@router.post("", response_model=schemas.VentaLeer, status_code=201)
def cobrar(
    datos: schemas.VentaCrear,
    db: Session = Depends(get_db),
    vendedor: models.Usuario = Depends(caja),
):
    venta = servicios.registrar_venta(
        db,
        vendedor=vendedor,
        tipo=datos.tipo,
        metodo_pago=datos.metodo_pago,
        mesa=datos.mesa,
        items=datos.items,
    )
    db.commit()
    db.refresh(venta)
    return venta


@router.get("", response_model=list[schemas.VentaLeer])
def listar_ventas(
    limite: int = 50,
    dia: date | None = None,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(usuario_actual),
):
    consulta = select(models.Venta).order_by(models.Venta.id.desc())
    if dia is not None:
        consulta = consulta.where(
            models.Venta.fecha_hora >= datetime.combine(dia, datetime.min.time()),
            models.Venta.fecha_hora <= datetime.combine(dia, datetime.max.time()),
        )
    return db.scalars(consulta.limit(limite)).all()


@router.get("/{venta_id}", response_model=schemas.VentaLeer)
def obtener_venta(
    venta_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(usuario_actual),
):
    venta = db.get(models.Venta, venta_id)
    if venta is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return venta


@router.post("/{venta_id}/anular", response_model=schemas.VentaLeer)
def anular_venta(
    venta_id: int,
    datos: schemas.VentaAnular,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(caja),
):
    venta = db.get(models.Venta, venta_id)
    if venta is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if venta.anulada:
        raise HTTPException(status_code=409, detail="Esa venta ya está anulada")

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
                usuario_id=usuario.id,
            )
        )

    venta.anulada = True
    venta.motivo_anulacion = datos.motivo
    venta.anulada_por_id = usuario.id
    venta.anulada_en = datetime.now()

    db.commit()
    db.refresh(venta)
    return venta
