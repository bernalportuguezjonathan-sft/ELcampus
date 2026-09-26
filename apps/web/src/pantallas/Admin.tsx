import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../api/cliente'
import type { Comparacion, Pedido, Producto, ResumenDia } from '../api/tipos'
import { cantidad as formatoCantidad, hora, plata } from '../formato'
import { useSesion } from '../sesion'
import MesasDelDia from './MesasDelDia'
import Productos from './Productos'
import Usuarios from './Usuarios'
import Fondo from './Fondo'

type Pestana = 'resumen' | 'mesas' | 'productos' | 'usuarios'

function Resumen() {
  const [resumen, setResumen] = useState<ResumenDia | null>(null)
  const [comparacion, setComparacion] = useState<Comparacion | null>(null)
  const [alertas, setAlertas] = useState<Producto[]>([])
  const [mesas, setMesas] = useState<Pedido[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      api.get<ResumenDia>('/reportes/dia'),
      api.get<Comparacion>('/reportes/comparar'),
      api.get<Producto[]>('/inventario/alertas'),
      api.get<Pedido[]>('/pedidos'),
    ])
      .then(([r, c, a, m]) => {
        setResumen(r)
        setComparacion(c)
        setAlertas(a)
        // Las que ya pidieron la cuenta van de primeras: son las que están
        // por pagar. El resto, por número de mesa.
        setMesas(
          [...m].sort((x, y) => {
            const urgencia = (p: Pedido) => (p.estado === 'cuenta_pedida' ? 0 : 1)
            return urgencia(x) - urgencia(y) || x.mesa - y.mesa
          }),
        )
      })
      .catch((fallo) =>
        setError(fallo instanceof Error ? fallo.message : 'No se pudieron cargar los datos.'),
      )
  }, [])

  if (error) return <p className="aviso aviso-error">{error}</p>
  if (!resumen) return <p className="cargando">Cargando…</p>

  const variacion = comparacion?.variacion_porcentaje ?? null
  const hoy = new Date(`${resumen.fecha}T12:00:00`).toLocaleDateString('es-CO', {
    weekday: 'long',
    day: 'numeric',
    month: 'short',
  })

  return (
    <div className="panel-rejilla">
      <section className="tarjeta tarjeta-ancha">
        <div className="admin-hoy">
          <span className="etiqueta">Ventas de hoy · {hoy}</span>
          <span className="admin-total num">{plata(resumen.total)}</span>
          {variacion !== null && (
            <span className={`delta ${variacion >= 0 ? 'sube' : 'baja'}`}>
              {variacion >= 0 ? '▲' : '▼'} {Math.abs(variacion)}% vs. hace una semana
            </span>
          )}
        </div>

        <div className="tiles">
          <div className="tile">
            <span className="tile-valor num">{resumen.cantidad_ventas}</span>
            <span className="tile-clave">ventas</span>
          </div>
          <div className="tile">
            <span className="tile-valor num">{plata(resumen.ticket_promedio)}</span>
            <span className="tile-clave">promedio</span>
          </div>
          <div className="tile">
            <span className="tile-valor num">{resumen.mesas_atendidas}</span>
            <span className="tile-clave">mesas</span>
          </div>
        </div>
      </section>

      {mesas.length > 0 && (
        <section className="tarjeta">
          <h2 className="tarjeta-titulo">
            Qué hay en el salón
            <span className="conteo">{mesas.length}</span>
          </h2>
          {mesas.map((pedido) => (
            <div key={pedido.id} className="fila-lista">
              <span>
                Mesa {pedido.mesa}
                <span className="atiende"> · {pedido.mesero_nombre}</span>
                {pedido.estado === 'cuenta_pedida' && (
                  <span className="marca-cuenta"> pidió la cuenta</span>
                )}
                <small className="valor-tenue">
                  {' · '}
                  {pedido.detalles.length}{' '}
                  {pedido.detalles.length === 1 ? 'producto' : 'productos'}
                  {' · desde '}
                  {hora(pedido.hora_apertura)}
                </small>
              </span>
              <span className="valor-tenue num">{plata(pedido.total)}</span>
            </div>
          ))}
        </section>
      )}

      {alertas.length > 0 && (
        <section className="tarjeta">
          <h2 className="tarjeta-titulo">Se está acabando</h2>
          {alertas.map((producto) => (
            <div key={producto.id} className="fila-lista">
              <span>{producto.nombre}</span>
              <span className="chip-bajo num">{formatoCantidad(producto.stock_actual)} und</span>
            </div>
          ))}
        </section>
      )}

      {resumen.por_metodo.length > 0 && (
        <section className="tarjeta">
          <h2 className="tarjeta-titulo">Cómo pagaron</h2>
          {resumen.por_metodo.map((m) => (
            <div key={m.metodo_pago} className="fila-lista">
              <span className="capitalizado">{m.metodo_pago}</span>
              <span className="valor-tenue num">
                {plata(m.total)} · {m.cantidad}
              </span>
            </div>
          ))}
        </section>
      )}

      {resumen.mas_vendidos.length > 0 && (
        <section className="tarjeta">
          <h2 className="tarjeta-titulo">Lo que más se vendió</h2>
          {resumen.mas_vendidos.map((p) => (
            <div key={p.nombre} className="fila-lista">
              <span>{p.nombre}</span>
              <span className="valor-tenue num">{formatoCantidad(p.cantidad)} und</span>
            </div>
          ))}
        </section>
      )}
    </div>
  )
}

export default function Admin() {
  const { sesion, salir } = useSesion()
  const [pestana, setPestana] = useState<Pestana>('resumen')

  return (
    <div className="panel">
      <Fondo />
      <header className="barra">
        <span className="marca">EL CAMPUS</span>
        <nav className="pestanas">
          <button
            className={`pestana ${pestana === 'resumen' ? 'activa' : ''}`}
            onClick={() => setPestana('resumen')}
          >
            Resumen
          </button>
          <button
            className={`pestana ${pestana === 'mesas' ? 'activa' : ''}`}
            onClick={() => setPestana('mesas')}
          >
            Mesas del día
          </button>
          <button
            className={`pestana ${pestana === 'productos' ? 'activa' : ''}`}
            onClick={() => setPestana('productos')}
          >
            Productos
          </button>
          <button
            className={`pestana ${pestana === 'usuarios' ? 'activa' : ''}`}
            onClick={() => setPestana('usuarios')}
          >
            Usuarios
          </button>
        </nav>
        <span className="der">
          <span className="quien">{sesion?.nombre}</span>
          <Link className="btn-peligro" to="/caja">
            Caja
          </Link>
          <button className="btn-peligro" onClick={salir}>
            Salir
          </button>
        </span>
      </header>

      <div className="panel-cuerpo">
        {pestana === 'resumen' && <Resumen />}
        {pestana === 'mesas' && <MesasDelDia />}
        {pestana === 'productos' && <Productos />}
        {pestana === 'usuarios' && <Usuarios />}
      </div>
    </div>
  )
}
