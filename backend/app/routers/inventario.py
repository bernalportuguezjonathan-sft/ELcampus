from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas, servicios
from ..auth import caja, solo_admin, usuario_actual
from ..database import get_db

router = APIRouter(prefix="/inventario", tags=["inventario"])


@router.post("/entrada", response_model=schemas.ProductoLeer, status_code=201)
def registrar_entrada(
    datos: schemas.EntradaMercancia,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(caja),
):
    """Llegó mercancía: la cantidad SUMA al stock, nunca lo reemplaza."""
    producto = db.get(models.Producto, datos.producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if datos.cantidad <= 0:
        raise HTTPException(status_code=400, detail="La cantidad debe ser mayor que cero")

    producto.stock_actual += datos.cantidad
    db.add(
        models.MovimientoInventario(
            producto_id=producto.id,
            tipo=models.TipoMovimientoInventario.entrada,
            cantidad=datos.cantidad,
            usuario_id=usuario.id,
        )
    )
    db.commit()
    db.refresh(producto)
    return producto


@router.post("/ajuste", response_model=schemas.ProductoLeer)
def ajustar_stock(
    datos: schemas.AjusteStock,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(solo_admin),
):
    """Corrección de conteo físico: aquí sí se fija el número exacto.

    Queda registrada la diferencia como movimiento, para que un faltante
    siempre tenga rastro de quién lo ajustó y cuándo.
    """
    producto = db.get(models.Producto, datos.producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    diferencia = datos.stock_real - producto.stock_actual
    if diferencia != 0:
        db.add(
            models.MovimientoInventario(
                producto_id=producto.id,
                tipo=(
                    models.TipoMovimientoInventario.entrada
                    if diferencia > 0
                    else models.TipoMovimientoInventario.salida
                ),
                cantidad=abs(diferencia),
                usuario_id=usuario.id,
            )
        )
    producto.stock_actual = datos.stock_real
    db.commit()
    db.refresh(producto)
    return producto


@router.get("/alertas", response_model=list[schemas.ProductoLeer])
def productos_por_acabarse(
    db: Session = Depends(get_db), _: models.Usuario = Depends(usuario_actual)
):
    return servicios.productos_en_alerta(db)


@router.get("/movimientos", response_model=list[schemas.MovimientoLeer])
def listar_movimientos(
    producto_id: int | None = None,
    limite: int = 100,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(usuario_actual),
):
    consulta = select(models.MovimientoInventario).order_by(
        models.MovimientoInventario.id.desc()
    )
    if producto_id is not None:
        consulta = consulta.where(models.MovimientoInventario.producto_id == producto_id)
    return db.scalars(consulta.limit(limite)).all()
