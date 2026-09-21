import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { api } from '../api/cliente'
import type { Pedido, Plato, Producto } from '../api/tipos'
import { cantidad as formatoCantidad, hora, plata } from '../formato'

export default function Mesa() {
  const { id } = useParams()
  const navegar = useNavigate()
  const [pedido, setPedido] = useState<Pedido | null>(null)
  const [platos, setPlatos] = useState<Plato[]>([])
  const [productos, setProductos] = useState<Producto[]>([])
  const [eligiendo, setEligiendo] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ocupado, setOcupado] = useState(false)

  const cargar = useCallback(async () => {
    try {
      setPedido(await api.get<Pedido>(`/pedidos/${id}`))
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar la mesa.')
    }
  }, [id])

  useEffect(() => {
    void cargar()
    void api.get<Plato[]>('/platos').then(setPlatos).catch(() => undefined)
    void api.get<Producto[]>('/productos').then(setProductos).catch(() => undefined)
  }, [cargar])

  async function agregar(cuerpo: { producto_id?: number; plato_id?: number }) {
    setOcupado(true)
    try {
      setPedido(await api.post<Pedido>(`/pedidos/${id}/items`, { ...cuerpo, cantidad: 1 }))
      setError(null)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo agregar.')
    } finally {
      setOcupado(false)
    }
  }

  async function cambiarCantidad(detalleId: number, nueva: number) {
    setOcupado(true)
    try {
      setPedido(
        await api.patch<Pedido>(`/pedidos/${id}/items/${detalleId}`, { cantidad: nueva }),
      )
      setError(null)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cambiar.')
    } finally {
      setOcupado(false)
    }
  }

  async function pedirCuenta() {
    setOcupado(true)
    try {
      setPedido(await api.post<Pedido>(`/pedidos/${id}/pedir-cuenta`))
      setError(null)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo pedir la cuenta.')
    } finally {
      setOcupado(false)
    }
  }

  if (!pedido) {
    return <p className="cargando">{error ?? 'Cargando la mesa…'}</p>
  }

  const cerrada = pedido.estado === 'pagado'

  return (
    <div className="celular-pantalla">
      <header className="barra">
        <button className="btn-peligro" onClick={() => navegar('/mesas')}>
          ← Mesas
        </button>
        <span className="marca">MESA {pedido.mesa}</span>
        <span className="der pista">Abierta {hora(pedido.hora_apertura)}</span>
      </header>

      <div className="celular-cuerpo">
        {error && <p className="aviso aviso-error">{error}</p>}
        {pedido.estado === 'cuenta_pedida' && (
          <p className="aviso aviso-atencion">
            La cuenta ya está en la caja. Puedes seguir agregando si el cliente pide algo más.
          </p>
        )}
        {cerrada && <p className="aviso aviso-ok">Esta mesa ya se cobró.</p>}

        {pedido.detalles.length === 0 && (
          <p className="pista">Todavía no has agregado nada a esta mesa.</p>
        )}

        {pedido.detalles.map((detalle) => (
          <div key={detalle.id} className="item-pedido">
            <span className="item-nombre">
              {detalle.nombre}
              <small className="num">
                {plata(detalle.precio_unitario)}
                {detalle.notas ? ` · ${detalle.notas}` : ''}
              </small>
            </span>
            <span className="stepper">
              <button
                onClick={() => void cambiarCantidad(detalle.id, detalle.cantidad - 1)}
                disabled={ocupado || cerrada}
                aria-label={`Quitar uno de ${detalle.nombre}`}
              >
                −
              </button>
              <span className="stepper-cantidad num">{formatoCantidad(detalle.cantidad)}</span>
              <button
                onClick={() => void cambiarCantidad(detalle.id, detalle.cantidad + 1)}
                disabled={ocupado || cerrada}
                aria-label={`Agregar uno de ${detalle.nombre}`}
              >
                +
              </button>
            </span>
          </div>
        ))}

        <div className="total-mesa">
          <span className="etiqueta">Total</span>
          <span className="total-mesa-valor num">{plata(pedido.total)}</span>
        </div>
      </div>

      {eligiendo && !cerrada && (
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
                onClick={() => void agregar({ plato_id: plato.id })}
                disabled={ocupado}
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
                onClick={() => void agregar({ producto_id: producto.id })}
                disabled={ocupado}
              >
                <b>{producto.nombre}</b>
                <small className="num">{plata(producto.precio_de_venta)}</small>
              </button>
            ))}
          </div>
        </div>
      )}

      {!cerrada && (
        <footer className="celular-pie">
          <button className="btn-secundario" onClick={() => setEligiendo((v) => !v)}>
            {eligiendo ? 'Ocultar el menú' : 'Agregar algo más'}
          </button>
          <button
            className="btn-primario"
            onClick={() => void pedirCuenta()}
            disabled={ocupado || pedido.detalles.length === 0}
          >
            PEDIR LA CUENTA
          </button>
        </footer>
      )}
    </div>
  )
}
