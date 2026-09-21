from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, schemas, servicios
from ..auth import caja as rol_caja
from ..database import get_db

router = APIRouter(prefix="/caja", tags=["caja"])


def _turno_abierto(db: Session) -> models.CierreCaja | None:
    return db.scalar(
        select(models.CierreCaja).where(
            models.CierreCaja.estado == models.EstadoCierreCaja.abierto
        )
    )


def _efectivo_del_turno(db: Session, desde: datetime) -> float:
    total = db.scalar(
        select(func.coalesce(func.sum(models.Venta.total), 0.0)).where(
            models.Venta.fecha_hora >= desde,
            models.Venta.metodo_pago == models.MetodoPago.efectivo,
            models.Venta.anulada.is_(False),
        )
    )
    return float(total or 0.0)


@router.get("/actual", response_model=schemas.CierreCajaLeer | None)
def turno_actual(db: Session = Depends(get_db), _: models.Usuario = Depends(rol_caja)):
    return _turno_abierto(db)


@router.post("/abrir", response_model=schemas.CierreCajaLeer, status_code=201)
def abrir_caja(
    datos: schemas.AbrirCaja,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(rol_caja),
):
    if _turno_abierto(db) is not None:
        raise HTTPException(
            status_code=409, detail="Ya hay una caja abierta. Ciérrala antes de abrir otra."
        )

    turno = models.CierreCaja(
        fecha=date.today(),
        base_inicial=datos.base_inicial,
        usuario_id=usuario.id,
    )
    db.add(turno)
    db.commit()
    db.refresh(turno)
    return turno


@router.post("/cerrar", response_model=schemas.CierreCajaLeer)
def cerrar_caja(
    datos: schemas.CerrarCaja,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(rol_caja),
):
    """Cuadre del día: lo que debería haber en el cajón contra lo contado.

    La diferencia se guarda tal cual, sin corregirla: un descuadre que se
    esconde es un descuadre que se repite.
    """
    turno = _turno_abierto(db)
    if turno is None:
        raise HTTPException(status_code=409, detail="No hay ninguna caja abierta.")

    esperado = servicios.redondear_pesos(
        turno.base_inicial + _efectivo_del_turno(db, turno.hora_apertura)
    )
    turno.efectivo_esperado = esperado
    turno.efectivo_contado = datos.efectivo_contado
    turno.diferencia = servicios.redondear_pesos(datos.efectivo_contado - esperado)
    turno.hora_cierre = datetime.now()
    turno.estado = models.EstadoCierreCaja.cerrado

    db.commit()
    db.refresh(turno)
    return turno


@router.get("", response_model=list[schemas.CierreCajaLeer])
def historial(
    limite: int = 30,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(rol_caja),
):
    return db.scalars(
        select(models.CierreCaja).order_by(models.CierreCaja.id.desc()).limit(limite)
    ).all()
