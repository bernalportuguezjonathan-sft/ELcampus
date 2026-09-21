from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import crear_token, solo_admin, usuario_actual
from ..database import get_db
from ..security import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["sesión"])


def _iniciar(nombre: str, clave: str, db: Session) -> schemas.Sesion:
    usuario = db.scalar(select(models.Usuario).where(models.Usuario.nombre == nombre))
    if usuario is None or not verify_password(clave, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre o clave incorrectos.",
        )
    if not usuario.activo:
        raise HTTPException(status_code=403, detail="Este usuario está desactivado.")

    return schemas.Sesion(
        access_token=crear_token(usuario),
        id=usuario.id,
        nombre=usuario.nombre,
        rol=usuario.rol,
    )


@router.post("/login", response_model=schemas.Sesion)
def login(datos: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Entrada estándar — la usa el botón Authorize de /docs."""
    return _iniciar(datos.username, datos.password, db)


@router.post("/entrar", response_model=schemas.Sesion)
def entrar(datos: schemas.Credenciales, db: Session = Depends(get_db)):
    """Entrada en JSON — la usa la pantalla de login de la app."""
    return _iniciar(datos.nombre, datos.clave, db)


@router.get("/yo", response_model=schemas.UsuarioLeer)
def yo(usuario: models.Usuario = Depends(usuario_actual)):
    return usuario


@router.get("/usuarios", response_model=list[schemas.UsuarioLeer])
def listar_usuarios(
    db: Session = Depends(get_db), _: models.Usuario = Depends(solo_admin)
):
    return db.scalars(select(models.Usuario)).all()


@router.post("/usuarios", response_model=schemas.UsuarioLeer, status_code=201)
def crear_usuario(
    datos: schemas.UsuarioCrear,
    db: Session = Depends(get_db),
    _: models.Usuario = Depends(solo_admin),
):
    if db.scalar(select(models.Usuario).where(models.Usuario.nombre == datos.nombre)):
        raise HTTPException(status_code=409, detail="Ya hay un usuario con ese nombre.")

    usuario = models.Usuario(
        nombre=datos.nombre,
        rol=datos.rol,
        password_hash=hash_password(datos.clave),
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/usuarios/{usuario_id}/desactivar", response_model=schemas.UsuarioLeer)
def desactivar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin: models.Usuario = Depends(solo_admin),
):
    usuario = db.get(models.Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if usuario.id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes desactivarte a ti mismo.")

    usuario.activo = False
    db.commit()
    db.refresh(usuario)
    return usuario
