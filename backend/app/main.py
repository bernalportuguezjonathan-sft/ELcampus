import jwt
from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .auth import leer_token
from .config import WEB_DIST
from .database import Base, engine
from .eventos import tablero
from .routers import auth, caja, inventario, pedidos, platos, productos, reportes, ventas

# Dev: crea las tablas si no existen. Las migraciones de Alembic mandan
# cuando el esquema cambia con datos ya cargados.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="El Campus API", version="0.2.0")

# En producción el mismo servidor entrega la app web, así que no hay origen
# cruzado. Esto es solo para el servidor de desarrollo de Vite.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")
api.include_router(auth.router)
api.include_router(productos.router)
api.include_router(platos.router)
api.include_router(ventas.router)
api.include_router(pedidos.router)
api.include_router(inventario.router)
api.include_router(caja.router)
api.include_router(reportes.router)


@api.get("/salud", tags=["sistema"])
def salud():
    return {"estado": "ok"}


app.include_router(api)


@app.websocket("/api/eventos")
async def eventos(websocket: WebSocket, token: str = ""):
    """Canal en vivo hacia la caja.

    El navegador no puede mandar encabezados al abrir un WebSocket, así que
    el token viaja como parámetro. Va por la red local del negocio.
    """
    try:
        leer_token(token)
    except jwt.PyJWTError:
        await websocket.close(code=1008)
        return

    await tablero.conectar(websocket)
    try:
        while True:
            # No esperamos mensajes del cliente; esto mantiene viva la
            # conexión y detecta cuándo se cierra.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await tablero.desconectar(websocket)


# La app web compilada se sirve desde el mismo servidor: un solo proceso,
# un solo puerto. La caja abre localhost y los celulares la IP del PC.
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
