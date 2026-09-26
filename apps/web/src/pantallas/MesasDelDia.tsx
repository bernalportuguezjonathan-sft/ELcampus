import { useEffect, useState } from 'react'

import { api } from '../api/cliente'
import type { MesasDelDia as Reporte } from '../api/tipos'
import { cantidad as formatoCantidad, hora, plata } from '../formato'

const ESTADOS: Record<string, string> = {
  abierto: 'Abierta',
  cuenta_pedida: 'Pidió la cuenta',
  pagado: 'Cobrada',
}

export default function MesasDelDia() {
  const [reporte, setReporte] = useState<Reporte | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [abierta, setAbierta] = useState<number | null>(null)

  useEffect(() => {
    api
      .get<Reporte>('/reportes/mesas')
      .then(setReporte)
      .catch((fallo) =>
        setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar el día.'),
      )
  }, [])

  if (error) return <p className="aviso aviso-error">{error}</p>
  if (!reporte) return <p className="cargando">Cargando…</p>

  const dia = new Date(`${reporte.fecha}T12:00:00`).toLocaleDateString('es-CO', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })

  return (
    <div className="panel-rejilla">
      <section className="tarjeta tarjeta-ancha">
        <div className="admin-hoy">
          <span className="etiqueta">Mesas del día · {dia}</span>
          <span className="admin-total num">{plata(reporte.total)}</span>
        </div>

        <div className="tiles">
          <div className="tile">
            <span className="tile-valor num">{reporte.cuantas}</span>
            <span className="tile-clave">
              {reporte.cuantas === 1 ? 'mesa atendida' : 'mesas atendidas'}
            </span>
          </div>
          <div className="tile">
            <span className="tile-valor num">
              {reporte.mesas.filter((m) => m.estado === 'pagado').length}
            </span>
            <span className="tile-clave">ya cobradas</span>
          </div>
          <div className="tile">
            <span className="tile-valor num">
              {reporte.mesas.filter((m) => m.estado !== 'pagado').length}
            </span>
            <span className="tile-clave">todavía abiertas</span>
          </div>
        </div>
      </section>

      <section className="tarjeta tarjeta-ancha">
        <h2 className="tarjeta-titulo">
          Qué pidió cada mesa
          {reporte.cuantas > 0 && <span className="conteo">{reporte.cuantas}</span>}
        </h2>

        {reporte.cuantas === 0 && (
          <p className="pista">Todavía no se ha atendido ninguna mesa hoy.</p>
        )}

        {reporte.mesas.map((m) => (
          <div key={m.id} className={`mesa-dia ${m.estado === 'pagado' ? 'cobrada' : ''}`}>
            <button
              type="button"
              className="mesa-dia-fila"
              onClick={() => setAbierta(abierta === m.id ? null : m.id)}
              aria-expanded={abierta === m.id}
            >
              <span className="mesa-dia-quien">
                <b>
                  Mesa {m.mesa}
                  <span className="atiende"> · {m.mesero_nombre}</span>
                </b>
                <small>
                  {ESTADOS[m.estado] ?? m.estado} · {hora(m.hora_apertura)} ·{' '}
                  {m.detalles.length} {m.detalles.length === 1 ? 'producto' : 'productos'}
                </small>
              </span>
              <span className="mesa-dia-total num">{plata(m.total)}</span>
            </button>

            {abierta === m.id && (
              <div className="mesa-dia-detalle">
                {m.detalles.map((d) => (
                  <div key={d.id} className="fila-lista">
                    <span>
                      <span className="confirmacion-cantidad num">
                        {formatoCantidad(d.cantidad)}
                      </span>{' '}
                      {d.nombre}
                      {d.notas && <small className="valor-tenue"> · {d.notas}</small>}
                    </span>
                    <span className="valor-tenue num">
                      {plata(d.precio_unitario)} c/u · <b>{plata(d.subtotal)}</b>
                    </span>
                  </div>
                ))}
                <div className="fila-lista total-de-la-mesa">
                  <span className="etiqueta">Total de la mesa</span>
                  <span className="num">{plata(m.total)}</span>
                </div>
              </div>
            )}
          </div>
        ))}
      </section>
    </div>
  )
}
