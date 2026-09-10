from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/productos", tags=["productos"])


@router.get("", response_model=list[schemas.ProductoLeer])
def listar_productos(db: Session = Depends(get_db)):
    return db.scalars(select(models.Producto)).all()


@router.get("/{codigo_barras}", response_model=schemas.ProductoLeer)
def buscar_por_codigo_barras(codigo_barras: str, db: Session = Depends(get_db)):
    producto = db.scalar(
        select(models.Producto).where(models.Producto.codigo_barras == codigo_barras)
    )
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.post("", response_model=schemas.ProductoLeer, status_code=201)
def crear_producto(producto: schemas.ProductoCrear, db: Session = Depends(get_db)):
    existente = db.scalar(
        select(models.Producto).where(models.Producto.codigo_barras == producto.codigo_barras)
    )
    if existente is not None:
        raise HTTPException(status_code=409, detail="Ese código de barras ya está registrado")

    nuevo = models.Producto(**producto.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo
