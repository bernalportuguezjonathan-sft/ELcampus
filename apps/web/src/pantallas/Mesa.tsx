import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { api } from '../api/cliente'
import type { Pedido, Plato, Producto } from '../api/tipos'
import { cantidad as formatoCantidad, hora, plata } from '../formato'
import Fondo from './Fondo'

/** Una línea de lo que el mesero va anotando. Todavía no existe en el
 *  servidor: vive en el teléfono hasta que se confirma el pedido. */
interface Linea {
  clave: string
  producto_id?: number
  plato_id?: number
  nombre: string
  precio: number
  cantidad: number
}

/** El borrador se guarda por mesa. Si al mesero se le bloquea la pantalla o
 *  se sale sin querer, lo que llevaba anotado sigue ahí. */
const llaveBorrador = (mesa: string) => `elcampus.borrador.mesa.${mesa}`

function leerBorrador(mesa: string): Linea[] {
  try {
    const guardado = localStorage.getItem(llaveBorrador(mesa))
    return guardado ? (JSON.parse(guardado) as Linea[]) : []
  } catch {
    return []
  }
}

function guardarBorrador(mesa: string, lineas: Linea[]) {
  try {
    if (lineas.length === 0) localStorage.removeItem(llaveBorrador(mesa))
    else localStorage.setItem(llaveBorrador(mesa), JSON.stringify(lineas))
  } catch {
    // Sin espacio o en modo privado: se sigue trabajando en memoria.
  }
}

export default function Mesa() {
  const { numero = '' } = useParams()
  const navegar = useNavigate()

  const [pedido, setPedido] = useState<Pedido | null>(null)
  const [cargando, setCargando] = useState(true)
  const [platos, setPlatos] = useState<Plato[]>([])
  const [productos, setProductos] = useState<Producto[]>([])
  const [borrador, setBorrador] = useState<Linea[]>(() => leerBorrador(numero))
  const [eligiendo, setEligiendo] = useState(false)
  const [confirmando, setConfirmando] = useState(false)
  const [subiendo, setSubiendo] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [listo, setListo] = useState<string | null>(null)

  const cargar = useCallback(async () => {
    try {
      setPedido(await api.get<Pedido | null>(`/pedidos/mesa/${numero}`))
      setError(null)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar la mesa.')
    } finally {
      setCargando(false)
    }
  }, [numero])

  useEffect(() => {
    void cargar()
    void api.get<Plato[]>('/platos').then(setPlatos).catch(() => undefined)
    void api.get<Producto[]>('/productos').then(setProductos).catch(() => undefined)
  }, [cargar])

  useEffect(() => {
    guardarBorrador(numero, borrador)
  }, [numero, borrador])

  const totalBorrador = useMemo(
    () => borrador.reduce((suma, l) => suma + l.precio * l.cantidad, 0),
    [borrador],
  )

  function anotar(item: { producto_id?: number; plato_id?: number; nombre: string; precio: number }) {
    const clave = item.plato_id ? `plato-${item.plato_id}` : `producto-${item.producto_id}`
    setBorrador((lineas) => {
      const ya = lineas.find((l) => l.clave === clave)
      if (ya) {
        return lineas.map((l) => (l.clave === clave ? { ...l, cantidad: l.cantidad + 1 } : l))
      }
      return [...lineas, { ...item, clave, cantidad: 1 }]
    })
    setListo(null)
  }

  function cambiarCantidad(clave: string, nueva: number) {
    setBorrador((lineas) =>
      nueva <= 0
        ? lineas.filter((l) => l.clave !== clave)
        : lineas.map((l) => (l.clave === clave ? { ...l, cantidad: nueva } : l)),
    )
  }

  async function confirmar() {
    setSubiendo(true)
    setError(null)
    try {
      const resultado = await api.post<Pedido>('/pedidos/enviar', {
        mesa: Number(numero),
        items: borrador.map((l) => ({
          producto_id: l.producto_id ?? null,
          plato_id: l.plato_id ?? null,
          cantidad: l.cantidad,
        })),
      })
      setPedido(resultado)
      setBorrador([])
      setConfirmando(false)
      setEligiendo(false)
      setListo('Pedido enviado a la caja.')
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo subir el pedido.')
      setConfirmando(false)
    } finally {
      setSubiendo(false)
    }
  }

  async function pedirCuenta() {
    if (!pedido) return
    setSubiendo(true)
    try {
      setPedido(await api.post<Pedido>(`/pedidos/${pedido.id}/pedir-cuenta`))
      setError(null)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo pedir la cuenta.')
    } finally {
      setSubiendo(false)
    }
  }

  if (cargando) return <p className="cargando">Cargando la mesa…</p>

  const ocupada = pedido !== null
  const totalMesa = (pedido?.total ?? 0) + totalBorrador

  return (
    <div className="celular-pantalla">
      <Fondo />
      <header className="barra">
        <button className="btn-peligro" onClick={() => navegar('/mesas')}>
          ← Mesas
        </button>
        <span className="marca">MESA {numero}</span>
        <span className="der pista">
          {ocupada ? `Abierta ${hora(pedido!.hora_apertura)}` : 'Libre'}
        </span>
      </header>

      <div className="celular-cuerpo">
        {error && <p className="aviso aviso-error">{error}</p>}
        {listo && <p className="aviso aviso-ok">{listo}</p>}
        {pedido?.estado === 'cuenta_pedida' && (
          <p className="aviso aviso-atencion">
            La cuenta ya está en la caja. Puedes seguir anotando si el cliente pide algo más.
          </p>
        )}

        {/* ---------------------------------------- lo que ya está en la caja */}
        {ocupada && pedido!.detalles.length > 0 && (
          <section className="bloque">
            <span className="etiqueta">Ya enviado a la caja</span>
            {pedido!.detalles.map((detalle) => (
              <div key={detalle.id} className="item-pedido enviado">
                <span className="item-nombre">
                  {detalle.nombre}
                  <small className="num">
                    {plata(detalle.precio_unitario)}
                    {detalle.notas ? ` · ${detalle.notas}` : ''}
                  </small>
                </span>
                <span className="cantidad-fija num">×{formatoCantidad(detalle.cantidad)}</span>
              </div>
            ))}
          </section>
        )}

        {/* ------------------------------------------ lo que se está anotando */}
        <section className="bloque">
          <span className="etiqueta">
            {borrador.length > 0 ? 'Por enviar' : 'Nada anotado todavía'}
          </span>

          {borrador.length === 0 && (
            <p className="pista">
              {ocupada
                ? 'Toca «Agregar algo más» para anotar otra ronda.'
                : 'Esta mesa sigue libre. Se ocupa cuando envíes el primer pedido.'}
            </p>
          )}

          {borrador.map((linea) => (
            <div key={linea.clave} className="item-pedido">
              <span className="item-nombre">
                {linea.nombre}
                <small className="num">{plata(linea.precio)}</small>
              </span>
              <span className="stepper">
                <button
                  onClick={() => cambiarCantidad(linea.clave, linea.cantidad - 1)}
                  aria-label={`Quitar uno de ${linea.nombre}`}
                >
                  −
                </button>
                <span className="stepper-cantidad num">{formatoCantidad(linea.cantidad)}</span>
                <button
                  onClick={() => cambiarCantidad(linea.clave, linea.cantidad + 1)}
                  aria-label={`Agregar uno de ${linea.nombre}`}
                >
                  +
                </button>
              </span>
            </div>
          ))}
        </section>

        <div className="total-mesa">
          <span className="etiqueta">Total de la mesa</span>
          <span className="total-mesa-valor num">{plata(totalMesa)}</span>
        </div>
      </div>

      {/* ------------------------------------------------------ el menú */}
      {eligiendo && (
        <div className="elector">
          <div className="elector-barra">
            <span className="etiqueta">¿Qué pidió?</span>
            <button className="btn-peligro" onClick={() => setEligiendo(false)}>
              Cerrar
            </button>
          </div>
          <div className="elector-lista">
            {platos.map((plato) => (
              <button
                key={`plato-${plato.id}`}
                className={`tarjeta-item ${plato.tipo === 'especial' ? 'especial' : ''}`}
                onClick={() =>
                  anotar({ plato_id: plato.id, nombre: plato.nombre, precio: plato.precio })
                }
              >
                <b>{plato.nombre}</b>
                <small className="num">{plata(plato.precio)}</small>
                {plato.tipo === 'especial' && <span className="marca-especial">Especial</span>}
              </button>
            ))}
            {productos.map((producto) => (
              <button
                key={`producto-${producto.id}`}
                className="tarjeta-item"
                onClick={() =>
                  anotar({
                    producto_id: producto.id,
                    nombre: producto.nombre,
                    precio: producto.precio_de_venta,
                  })
                }
              >
                <b>{producto.nombre}</b>
                <small className="num">{plata(producto.precio_de_venta)}</small>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ------------------------------------------- confirmar el pedido */}
      {confirmando && (
        <div className="velo" role="dialog" aria-modal="true" aria-labelledby="titulo-confirmar">
          <div className="confirmacion">
            <h2 id="titulo-confirmar" className="confirmacion-titulo">
              Confirmar pedido
            </h2>
            <p className="confirmacion-nota">
              Esto es lo que va a subir a la mesa {numero}
              {!ocupada && '. La mesa queda ocupada'}.
            </p>

            <div className="confirmacion-lista">
              {borrador.map((linea) => (
                <div key={linea.clave} className="confirmacion-linea">
                  <span className="confirmacion-cantidad num">{formatoCantidad(linea.cantidad)}</span>
                  <span className="confirmacion-nombre">{linea.nombre}</span>
                  <span className="confirmacion-precio num">
                    {plata(linea.precio * linea.cantidad)}
                  </span>
                </div>
              ))}
            </div>

            <div className="confirmacion-total">
              <span className="etiqueta">Total por enviar</span>
              <span className="num">{plata(totalBorrador)}</span>
            </div>

            <div className="confirmacion-botones">
              <button
                className="btn-secundario"
                onClick={() => setConfirmando(false)}
                disabled={subiendo}
              >
                Corregir pedido
              </button>
              <button className="btn-primario" onClick={() => void confirmar()} disabled={subiendo}>
                {subiendo ? 'Enviando…' : 'Confirmar'}
              </button>
            </div>
          </div>
        </div>
      )}

      <footer className="celular-pie">
        <button className="btn-secundario" onClick={() => setEligiendo((v) => !v)}>
          {eligiendo ? 'Ocultar el menú' : 'Agregar algo más'}
        </button>

        {borrador.length > 0 ? (
          <button className="btn-primario" onClick={() => setConfirmando(true)}>
            SUBIR PEDIDO · {plata(totalBorrador)}
          </button>
        ) : (
          <button
            className="btn-primario"
            onClick={() => void pedirCuenta()}
            disabled={subiendo || !ocupada || pedido!.estado === 'cuenta_pedida'}
          >
            {pedido?.estado === 'cuenta_pedida' ? 'CUENTA YA PEDIDA' : 'PEDIR LA CUENTA'}
          </button>
        )}
      </footer>
    </div>
  )
}
