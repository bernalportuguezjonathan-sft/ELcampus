import asyncio

from fastapi import WebSocket


class Tablero:
    """Reparte avisos en vivo a las pantallas conectadas.

    Lo usa el mesero para que un pedido aparezca solo en la caja, sin que
    nadie tenga que refrescar nada.
    """

    def __init__(self) -> None:
        self._conexiones: set[WebSocket] = set()
        self._candado = asyncio.Lock()

    async def conectar(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._candado:
            self._conexiones.add(ws)

    async def desconectar(self, ws: WebSocket) -> None:
        async with self._candado:
            self._conexiones.discard(ws)

    async def avisar(self, evento: str, datos: dict) -> None:
        mensaje = {"evento": evento, "datos": datos}
        async with self._candado:
            destinatarios = list(self._conexiones)

        caidas = []
        for ws in destinatarios:
            try:
                await ws.send_json(mensaje)
            except Exception:
                caidas.append(ws)

        for ws in caidas:
            await self.desconectar(ws)


tablero = Tablero()
