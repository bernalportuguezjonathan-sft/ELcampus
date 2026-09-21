# El Campus — Plan técnico (documento vivo)

Basado en "El Campus - Plan del proyecto.docx" (7 sep 2026), actualizado con las
decisiones tomadas el 10 sep 2026. Este archivo es más fácil de mantener al día
que el .docx a medida que avanza el proyecto — el .docx queda como versión
original de referencia.

## Decisiones tomadas (10 sep 2026)

| Tema | Decisión |
|---|---|
| Acceso remoto del administrador | VPN con Tailscale — el servidor nunca se expone directo a internet |
| Facturación electrónica DIAN | Sin confirmar todavía. Se dejó un campo `factura_electronica_id` abierto en `ventas` para no bloquear el modelo, pero no se construye la integración en el MVP |
| Métodos de pago | Efectivo + Nequi + Daviplata + tarjeta desde el inicio (`metodo_pago` en `ventas`) |
| Venta por peso | Sí aplica (ej. morraja). `productos.tipo_venta` (unidad/peso) + `precio_por_kg` |

## Decisión del 21 sep 2026: se descarta PySide6

La caja del vendedor **no** es una app de escritorio aparte. Es la misma app
web de React abierta en modo kiosco en el PC del mostrador.

**Por qué:** el lector de código de barras se comporta como un teclado, así
que el navegador lo maneja igual de bien que Qt. A cambio se gana un solo
código para las tres pantallas, una sola estética, actualizaciones instantáneas
y la mitad del trabajo de mantenimiento. Los mockups ya eran HTML, así que se
reutilizaron tal cual.

**Lo que hay que vigilar:** si más adelante hace falta imprimir recibos en una
impresora térmica, el navegador es más incómodo que una app nativa. Se
resolvería con un pequeño servicio local de impresión, no volviendo a Qt.

## Arquitectura

Un solo proceso sirve todo: FastAPI entrega la API en `/api` y, ya compilada,
también la app web. La caja abre `localhost` (no depende del WiFi para cobrar),
los celulares del salón entran por la IP del PC, y el administrador remoto
entra por Tailscale — nunca por un puerto abierto a internet.

```
apps/web (React)  ──HTTP /api──►  backend (FastAPI)  ──►  SQLite (WAL)
     │                                  ▲
     └──────WebSocket /api/eventos──────┘
            (mesa pide la cuenta → salta sola a la caja)
```

## Modelo de datos (9 tablas)

Las 8 tablas originales del plan, más `cierres_caja` (cuadre de caja diario,
gap detectado en la revisión del 10 sep). Detalle en
[`backend/app/models.py`](../backend/app/models.py).

Decisiones de diseño resueltas al implementar:

- `detalle_venta` y `detalle_pedido_mesa` usan **dos FK nullable**
  (`producto_id`, `plato_id`) con un `CHECK` que obliga a que exactamente una
  esté llena, en vez de una referencia polimórfica sin tipar.
- Las ventas **nunca se borran**: se marcan `anulada=True` con
  `motivo_anulacion`, `anulada_por_id` y `anulada_en`, para que el historial
  de auditoría y el cuadre de caja siempre cuadren.
- `usuarios.password_hash` — nunca contraseña en texto plano.

## Pendiente de confirmar con el negocio

1. Lista completa de productos del supermercado (para categorías).
2. Menú fijo con precios actuales + cómo se anuncian los especiales.
3. Si el local tiene WiFi estable y cuántos celulares se usan como mesero.
4. Si aplica facturación electrónica DIAN (tamaño/régimen del negocio).
5. Si se van a imprimir recibos físicos (impresora térmica ESC/POS) — no
   estaba en el plan original, hay que confirmar si aplica.

## Fases

Ver plan original — 12 semanas desde el 7 sep 2026, con todo probado antes de
diciembre (temporada alta). Fase 0 (7–13 sep): entorno, modelo de datos,
listas de productos y platos.

## Decisiones tomadas al construir el motor de ventas

- **La caja nunca se bloquea por falta de stock.** Si el conteo dice 0 y el
  producto está en la mano del cliente, se cobra igual y el stock queda
  negativo. Un stock negativo es una señal de que hay que corregir el
  inventario, no una razón para no vender.
- **Hora local, no UTC.** Una venta del sábado 8pm en Colombia (UTC-5) caería
  en el domingo si se guardara en UTC, y el reporte del día no cuadraría.
- **Los precios los pone el servidor, no el cliente.** La app del vendedor
  manda qué se vendió y cuánto, nunca a qué precio — así nadie puede cobrar
  un precio distinto al registrado manipulando la app.
- **Los totales se redondean a pesos enteros** (el peso colombiano no maneja
  centavos en caja).
- **`passlib` quedó descartado** — está abandonado y rompe con bcrypt 5.
  Se usa `bcrypt` directo.

## Estado actual (21 sep 2026)

Backend — 34 pruebas automáticas pasando:
- [x] Sesiones reales con JWT, claves con bcrypt, permisos por rol
- [x] Productos (alta por código de barras, búsqueda, cambio de precio)
- [x] Platos, con los especiales filtrados por sus fechas
- [x] Cobro en transacción atómica, anulación con devolución de stock
- [x] Pedidos de mesa + WebSocket: la cuenta salta sola a la caja
- [x] Cobrar una mesa cierra el pedido y crea la venta en una sola operación
- [x] Inventario: entradas que suman, ajustes de conteo con rastro, alertas
- [x] Cierre de caja con cuadre de efectivo
- [x] Reportes del día, comparación contra la semana pasada, más vendidos

Frontend — las tres pantallas funcionando y probadas en el navegador:
- [x] Login
- [x] Caja: escaneo con foco permanente, suma de repetidos, flujo de peso
      en kilos, vuelto, cobro, anulación, avisos de mesa en vivo
- [x] Mesero: cuadrícula de mesas con estado, detalle con +/−, pedir la cuenta
- [x] Admin: ventas del día, cómo pagaron, se está acabando, más vendidos

Pendiente:
- [ ] Alembic (migraciones) — antes de cargar datos reales
- [ ] Comanda a cocina: hoy el mesero agrega platos y **la cocina no se entera**
- [ ] Costo por producto (sin costo solo se ve venta, nunca utilidad)
- [ ] Modo offline del mesero (si se cae el WiFi no puede tomar pedidos)
- [ ] Carga masiva del catálogo + autocompletado con Open Food Facts
- [ ] Backups automáticos
- [ ] Decidir si se imprimen recibos térmicos

## Pendiente de decidir

- **Plata como `float`.** Hoy los precios se guardan como decimales y los
  totales se redondean a peso entero al cobrar. Migrar a enteros (pesos)
  sería más exacto y hoy costaría poco; más adelante, con datos reales
  encima, cuesta más.
- **Un pago por venta.** Si un cliente paga mitad en efectivo y mitad por
  Nequi, hoy no se puede registrar así.
- **No hay descuentos ni cortesías.** Una invitación al cliente frecuente
  hoy tocaría registrarla como anulación, que ensucia el historial.
