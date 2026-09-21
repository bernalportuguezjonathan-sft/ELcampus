from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import solo_admin, usuario_actual
from ..database import get_db

router = APIRouter(prefix="/platos", tags=["platos"])


@router.get("", response_model=list[schemas.PlatoLeer])
def listar_platos(
    solo_vigentes: bool = True,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(usuario_actual),
):
    """Los fijos siempre; los especiales solo dentro de sus fechas.

    Así el mesero ve el menú del fin de semana sin que nadie tenga que
    acordarse de apagar el especial del sábado pasado.
    """
    consulta = select(models.Plato)
    if solo_vigentes:
        hoy = date.today()
        consulta = consulta.where(
            or_(
                models.Plato.tipo == models.TipoPlato.fijo,
                (
                    or_(models.Plato.activo_desde.is_(None), models.Plato.activo_desde <= hoy)
                    & or_(models.Plato.activo_hasta.is_(None), models.Plato.activo_hasta >= hoy)
                ),
            )
        )
    return db.scalars(consulta.order_by(models.Plato.tipo, models.Plato.nombre)).all()


@router.post("", response_model=schemas.PlatoLeer, status_code=201)
def crear_plato(
    datos: schemas.PlatoCrear,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(solo_admin),
):
    plato = models.Plato(**datos.model_dump())
    db.add(plato)
    db.commit()
    db.refresh(plato)
    return plato


@router.patch("/{plato_id}", response_model=schemas.PlatoLeer)
def actualizar_plato(
    plato_id: int,
    datos: schemas.PlatoActualizar,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(solo_admin),
):
    plato = db.get(models.Plato, plato_id)
    if plato is None:
        raise HTTPException(status_code=404, detail="Plato no encontrado")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(plato, campo, valor)
    db.commit()
    db.refresh(plato)
    return plato


@router.delete("/{plato_id}", status_code=204)
def borrar_plato(
    plato_id: int,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(solo_admin),
):
    plato = db.get(models.Plato, plato_id)
    if plato is None:
        raise HTTPException(status_code=404, detail="Plato no encontrado")

    ya_se_vendio = db.scalar(
        select(models.DetalleVenta.id).where(models.DetalleVenta.plato_id == plato_id).limit(1)
    )
    if ya_se_vendio:
        raise HTTPException(
            status_code=409,
            detail="Este plato ya tiene ventas registradas. Cámbiale las fechas en vez de borrarlo.",
        )

    db.delete(plato)
    db.commit()
