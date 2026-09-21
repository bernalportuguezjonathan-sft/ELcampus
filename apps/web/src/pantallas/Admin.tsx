import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../api/cliente'
import type { Comparacion, Producto, ResumenDia } from '../api/tipos'
import { cantidad as formatoCantidad, plata } from '../formato'
import { useSesion } from '../sesion'

export default function Admin() {
  const { sesion, salir } = useSesion()
  const [resumen, setResumen] = useState<ResumenDia | null>(null)
  const [comparacion, setComparacion] = useState<Comparacion | null>(null)
  const [alertas, setAlertas] = useState<Producto[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      api.get<ResumenDia>('/reportes/dia'),
      api.get<Comparacion>('/reportes/comparar'),
      api.get<Producto[]>('/inventario/alertas'),
    ])
      .then(([r, c, a]) => {
        setResumen(r)
        setComparacion(c)
        setAlertas(a)
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
    <div className="celular-pantalla">
      <header className="barra">
        <span className="marca">EL CAMPUS</span>
        <span>{sesion?.nombre}</span>
        <span className="der">
          <Link className="btn-peligro" to="/caja">
            Caja
          </Link>
          <button className="btn-peligro" onClick={salir}>
            Salir
          </button>
        </span>
      </header>

      <div className="celular-cuerpo admin">
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

        {alertas.length > 0 && (
          <section className="bloque">
            <span className="etiqueta">Se está acabando</span>
            {alertas.map((producto) => (
              <div key={producto.id} className="fila-lista">
                <span>{producto.nombre}</span>
                <span className="chip-bajo num">
                  {formatoCantidad(producto.stock_actual)} und
                </span>
              </div>
            ))}
          </section>
        )}

        {resumen.por_metodo.length > 0 && (
          <section className="bloque">
            <span className="etiqueta">Cómo pagaron</span>
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
          <section className="bloque">
            <span className="etiqueta">Lo que más se vendió</span>
            {resumen.mas_vendidos.map((p) => (
              <div key={p.nombre} className="fila-lista">
                <span>{p.nombre}</span>
                <span className="valor-tenue num">{formatoCantidad(p.cantidad)} und</span>
              </div>
            ))}
          </section>
        )}
      </div>
    </div>
  )
}
