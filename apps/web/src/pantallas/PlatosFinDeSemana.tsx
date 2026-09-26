import { useEffect, useMemo, useState, type FormEvent } from 'react'

import { api } from '../api/cliente'
import type { Plato } from '../api/tipos'
import { miles, plata, soloDigitos } from '../formato'

/** yyyy-mm-dd en hora local.
 *
 *  A propósito no se usa `toISOString()`: esa fecha es UTC y en Colombia
 *  (UTC-5) un viernes por la noche saldría como sábado, que es justo el día
 *  en que el menú tiene que estar bien.
 */
function aISO(fecha: Date) {
  const mes = String(fecha.getMonth() + 1).padStart(2, '0')
  const dia = String(fecha.getDate()).padStart(2, '0')
  return `${fecha.getFullYear()}-${mes}-${dia}`
}

/** El fin de semana que viene — o el que está corriendo, si hoy ya es
 *  viernes, sábado o domingo. */
function finDeSemana() {
  const hoy = new Date()
  const dia = hoy.getDay() // 0 domingo … 6 sábado
  const viernes = new Date(hoy)
  if (dia === 0) viernes.setDate(hoy.getDate() - 2)
  else if (dia === 6) viernes.setDate(hoy.getDate() - 1)
  else if (dia < 5) viernes.setDate(hoy.getDate() + (5 - dia))

  const domingo = new Date(viernes)
  domingo.setDate(viernes.getDate() + 2)
  return { desde: aISO(viernes), hasta: aISO(domingo) }
}

const dia = (iso: string) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString('es-CO', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })

export default function PlatosFinDeSemana() {
  const [platos, setPlatos] = useState<Plato[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [listo, setListo] = useState<string | null>(null)

  const [elegidos, setElegidos] = useState<Set<number>>(new Set())
  const [desde, setDesde] = useState(finDeSemana().desde)
  const [hasta, setHasta] = useState(finDeSemana().hasta)
  const [publicando, setPublicando] = useState(false)

  const [abierto, setAbierto] = useState<number | null>(null)
  const [precioNuevo, setPrecioNuevo] = useState('')

  const [nombre, setNombre] = useState('')
  const [precio, setPrecio] = useState('')
  const [guardando, setGuardando] = useState(false)

  /** Trae la carta completa, no el menú de hoy: el administrador arma el fin
   *  de semana escogiendo entre todos los platos que existen. */
  function cargar(marcarLoPublicado = false) {
    api
      .get<Plato[]>('/platos?solo_vigentes=false')
      .then((todos) => {
        setPlatos(todos)
        if (!marcarLoPublicado) return
        // Lo que ya está publicado arranca marcado, para que volver a
        // publicar no borre sin querer el menú que ya estaba puesto.
        const puestos = todos.filter((p) => p.tipo === 'especial' && p.activo_desde)
        setElegidos(new Set(puestos.map((p) => p.id)))
        if (puestos[0]?.activo_desde && puestos[0]?.activo_hasta) {
          setDesde(puestos[0].activo_desde)
          setHasta(puestos[0].activo_hasta)
        }
      })
      .catch((f) => setError(f instanceof Error ? f.message : 'No se pudo cargar la carta.'))
  }

  useEffect(() => cargar(true), [])

  useEffect(() => {
    if (!listo) return
    const reloj = setTimeout(() => setListo(null), 4000)
    return () => clearTimeout(reloj)
  }, [listo])

  const especiales = useMemo(
    () => (platos ?? []).filter((p) => p.tipo === 'especial'),
    [platos],
  )
  const fijos = useMemo(() => (platos ?? []).filter((p) => p.tipo === 'fijo'), [platos])

  function marcar(id: number) {
    setElegidos((antes) => {
      const ahora = new Set(antes)
      if (ahora.has(id)) ahora.delete(id)
      else ahora.add(id)
      return ahora
    })
  }

  async function publicar() {
    setError(null)
    setPublicando(true)
    try {
      await api.post<Plato[]>('/platos/menu', {
        desde,
        hasta,
        platos: [...elegidos],
      })
      setListo(
        elegidos.size === 0
          ? 'Menú publicado: este fin de semana van solo los platos fijos.'
          : `Menú publicado: ${elegidos.size} ${elegidos.size === 1 ? 'plato' : 'platos'} del ${dia(desde)} al ${dia(hasta)}.`,
      )
      cargar()
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo publicar el menú.')
    } finally {
      setPublicando(false)
    }
  }

  async function crear(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setGuardando(true)
    try {
      await api.post<Plato>('/platos', {
        nombre: nombre.trim(),
        precio: Number(precio || 0),
        tipo: 'especial',
      })
      setListo(`${nombre.trim()} quedó en la carta. Márcalo cuando vaya a salir.`)
      setNombre('')
      setPrecio('')
      cargar()
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo agregar el plato.')
    } finally {
      setGuardando(false)
    }
  }

  async function cambiarPrecio(plato: Plato) {
    setError(null)
    try {
      await api.patch<Plato>(`/platos/${plato.id}`, { precio: Number(precioNuevo) })
      setListo(`${plato.nombre} ahora vale ${plata(Number(precioNuevo))}.`)
      setPrecioNuevo('')
      cargar()
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cambiar el precio.')
    }
  }

  async function quitar(plato: Plato) {
    if (!window.confirm(`¿Quitar "${plato.nombre}" de la carta? Ya no lo podrás volver a sacar.`)) return
    setError(null)
    try {
      await api.borrar(`/platos/${plato.id}`)
      setElegidos((antes) => {
        const ahora = new Set(antes)
        ahora.delete(plato.id)
        return ahora
      })
      setAbierto(null)
      setListo(`${plato.nombre} salió de la carta.`)
      cargar()
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo quitar el plato.')
    }
  }

  const fechasAlReves = Boolean(desde && hasta && hasta < desde)

  return (
    <section className="tarjeta tarjeta-ancha">
      <h2 className="tarjeta-titulo">
        Platos del fin de semana
        {especiales.length > 0 && <span className="conteo">{especiales.length}</span>}
      </h2>
      <p className="tarjeta-nota">
        Marca los que salen este fin de semana y publícalos. Lo que no marques deja de
        aparecerle al mesero, y el menú se apaga solo cuando pasa la fecha.
      </p>

      {error && <p className="aviso aviso-error">{error}</p>}
      {listo && <p className="aviso aviso-ok">{listo}</p>}

      {platos === null && <p className="cargando">Cargando…</p>}

      {platos !== null && (
        <>
          <div className="fechas-menu">
            <label className="campo">
              <span className="etiqueta">Desde</span>
              <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
            </label>
            <label className="campo">
              <span className="etiqueta">Hasta</span>
              <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
            </label>
          </div>

          {fechasAlReves && (
            <p className="aviso aviso-error">
              La fecha de fin no puede ser anterior a la de inicio.
            </p>
          )}

          {especiales.length === 0 && (
            <p className="pista">
              Todavía no hay platos que roten. Agrega el primero aquí abajo.
            </p>
          )}

          {especiales.map((p) => {
            const puesto = Boolean(p.activo_desde)
            return (
              <div key={p.id} className={`plato ${elegidos.has(p.id) ? 'elegido' : ''}`}>
                <div className="plato-fila">
                  <label className="plato-marca">
                    <input
                      type="checkbox"
                      checked={elegidos.has(p.id)}
                      onChange={() => marcar(p.id)}
                    />
                    <span className="plato-quien">
                      <b>{p.nombre}</b>
                      {puesto && p.activo_desde && p.activo_hasta && (
                        <small>
                          en el menú · {dia(p.activo_desde)} a {dia(p.activo_hasta)}
                        </small>
                      )}
                    </span>
                  </label>
                  <span className="plato-precio num">{plata(p.precio)}</span>
                  <button
                    type="button"
                    className="btn-tenue"
                    onClick={() => {
                      setAbierto(abierto === p.id ? null : p.id)
                      setPrecioNuevo('')
                    }}
                    aria-expanded={abierto === p.id}
                  >
                    Editar
                  </button>
                </div>

                {abierto === p.id && (
                  <div className="plato-editar">
                    <label className="campo">
                      <span className="etiqueta">Cambiar precio</span>
                      <input
                        className="num"
                        value={precioNuevo ? miles(Number(precioNuevo)) : ''}
                        onChange={(e) => setPrecioNuevo(soloDigitos(e.target.value))}
                        inputMode="numeric"
                        placeholder={String(p.precio)}
                      />
                    </label>
                    <button
                      type="button"
                      className="btn-secundario"
                      disabled={!precioNuevo}
                      onClick={() => void cambiarPrecio(p)}
                    >
                      Guardar precio
                    </button>
                    <button
                      type="button"
                      className="btn-peligro"
                      onClick={() => void quitar(p)}
                    >
                      Quitar de la carta
                    </button>
                  </div>
                )}
              </div>
            )
          })}

          {especiales.length > 0 && (
            <button
              className="btn-primario"
              onClick={() => void publicar()}
              disabled={publicando || fechasAlReves || !desde || !hasta}
            >
              {publicando
                ? 'Publicando…'
                : elegidos.size === 0
                  ? 'Publicar: solo los platos fijos'
                  : `Publicar el menú · ${elegidos.size} ${elegidos.size === 1 ? 'plato' : 'platos'}`}
            </button>
          )}

          {fijos.length > 0 && (
            <p className="pista">
              <b>Siempre en la carta:</b> {fijos.map((p) => p.nombre).join(' · ')}. Esos no se
              marcan, van todos los fines de semana.
            </p>
          )}

          <form className="plato-nuevo" onSubmit={crear}>
            <label className="campo">
              <span className="etiqueta">Agregar un plato a la carta</span>
              <input
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder="Nombre del plato"
                autoComplete="off"
                required
              />
            </label>
            <label className="campo">
              <span className="etiqueta">Precio</span>
              <input
                className="num"
                value={precio ? miles(Number(precio)) : ''}
                onChange={(e) => setPrecio(soloDigitos(e.target.value))}
                inputMode="numeric"
                placeholder="0"
                required
              />
            </label>
            <button className="btn-secundario" type="submit" disabled={guardando}>
              {guardando ? 'Guardando…' : 'Agregar'}
            </button>
          </form>
        </>
      )}
    </section>
  )
}
