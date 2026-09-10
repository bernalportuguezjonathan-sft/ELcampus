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

## Arquitectura

Servidor central FastAPI + SQLite (modo WAL) corriendo en el PC del vendedor.
Vendedor habla por `localhost` (no depende del WiFi para cobrar). Mesero y
administrador se conectan por WiFi local; el administrador remoto entra por
Tailscale, no por un puerto expuesto a internet.

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

## Estado actual

Fase 0:
- [x] Repo y estructura de carpetas (`backend/`, `apps/vendedor/`, `apps/web/`)
- [x] Modelo de datos en SQLAlchemy con las decisiones del 10 sep
- [x] Servidor FastAPI arrancando, WAL activado

Fase 1 (motor de inventario y ventas):
- [x] Alta y consulta de productos por código de barras
- [x] Cobro (`POST /ventas`) en transacción atómica: calcula el total, arma el
      detalle, descuenta stock y registra el movimiento de inventario
- [x] Escanear el mismo código dos veces suma cantidad en una sola línea
- [x] Anulación de venta (`POST /ventas/{id}/anular`) que devuelve el stock
- [x] 9 pruebas automáticas del camino del dinero (`pytest`)
- [ ] Alembic (migraciones) — pendiente antes de que el esquema se estabilice
- [ ] Cierre de caja (la tabla existe, faltan los endpoints)
- [ ] App de escritorio del vendedor (PySide6)
- [ ] Login / autenticación real — hoy el `vendedor_id` se manda en la
      petición, sin verificar quién es

## Pendiente de decidir

- **Plata como `float`.** Hoy los precios se guardan como decimales y los
  totales se redondean a peso entero al cobrar. Migrar a enteros (pesos)
  sería más exacto y hoy costaría poco; más adelante, con datos reales
  encima, cuesta más.
