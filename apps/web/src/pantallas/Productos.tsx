import { useEffect, useMemo, useState, type FormEvent } from 'react'

import { api } from '../api/cliente'
import type { Producto } from '../api/tipos'
import { cantidad as formatoCantidad, miles, plata, soloDigitos } from '../formato'
import PlatosFinDeSemana from './PlatosFinDeSemana'

/** Un producto recién creado arranca con estos valores. */
const EN_BLANCO = {
  codigo_barras: '',
  nombre: '',
  precio: '',
  categoria: '',
  stock_actual: '',
  en_carta: false,
}

export default function Productos() {
  const [productos, setProductos] = useState<Producto[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [listo, setListo] = useState<string | null>(null)
  const [busqueda, setBusqueda] = useState('')

  const [nuevo, setNuevo] = useState({ ...EN_BLANCO })
  const [guardando, setGuardando] = useState(false)

  const [abierto, setAbierto] = useState<number | null>(null)
  const [precioNuevo, setPrecioNuevo] = useState('')
  const [stockReal, setStockReal] = useState('')

  function cargar() {
    api
      .get<Producto[]>('/productos')
      .then(setProductos)
      .catch((f) => setError(f instanceof Error ? f.message : 'No se pudo cargar el catálogo.'))
  }

  useEffect(cargar, [])

  useEffect(() => {
    if (!listo) return
    const reloj = setTimeout(() => setListo(null), 4000)
    return () => clearTimeout(reloj)
  }, [listo])

  const visibles = useMemo(() => {
    if (!productos) return []
    const buscado = busqueda.trim().toLowerCase()
    if (!buscado) return productos
    return productos.filter(
      (p) =>
        p.nombre.toLowerCase().includes(buscado) ||
        p.codigo_barras.toLowerCase().includes(buscado),
    )
  }, [productos, busqueda])

  const enCarta = useMemo(
    () => (productos ?? []).filter((p) => p.en_carta).length,
    [productos],
  )

  async function crear(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setGuardando(true)
    try {
      await api.post<Producto>('/productos', {
        codigo_barras: nuevo.codigo_barras.trim(),
        nombre: nuevo.nombre.trim(),
        precio: Number(nuevo.precio || 0),
        categoria: nuevo.categoria.trim() || null,
        stock_actual: Number(nuevo.stock_actual || 0),
        en_carta: nuevo.en_carta,
      })
      setListo(`${nuevo.nombre.trim()} quedó en el catálogo.`)
      setNuevo({ ...EN_BLANCO })
      cargar()
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo crear el producto.')
    } finally {
      setGuardando(false)
    }
  }

  async function cambiar(p: Producto, cambios: Record<string, unknown>, aviso: string) {
    setError(null)
    try {
      await api.patch<Producto>(`/productos/${p.id}`, cambios)
      setListo(aviso)
      cargar()
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo guardar el cambio.')
    }
  }

  /** El stock no se edita a mano: se ajusta, y queda el rastro de quién y por qué. */
  async function ajustarStock(p: Producto) {
    const real = Number(stockReal || 0)
    setError(null)
    try {
      await api.post('/inventario/ajuste', {
        producto_id: p.id,
        stock_real: real,
        motivo: 'Conteo desde el panel de administración',
      })
      setListo(`${p.nombre}: stock ajustado a ${formatoCantidad(real)}.`)
      setStockReal('')
      cargar()
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo ajustar el stock.')
    }
  }

  function abrir(p: Producto) {
    const mismo = abierto === p.id
    setAbierto(mismo ? null : p.id)
    setPrecioNuevo('')
    setStockReal('')
    setError(null)
  }

  return (
    <div className="panel-rejilla">
      {/* Va de primero porque es la tarea de cada semana: los productos se
          cargan una vez, el menú del fin de semana se arma cada viernes. */}
      <PlatosFinDeSemana />

      {/* ------------------------------------------------- crear */}
      <section className="tarjeta">
        <h2 className="tarjeta-titulo">Agregar producto</h2>
        <p className="tarjeta-nota">
          Lo que marques como «se pide en la mesa» le aparece al mesero en el celular. El
          mercado de entre semana déjalo sin marcar: se vende escaneándolo en la caja.
        </p>

        <form className="forma" onSubmit={crear}>
          <label className="campo">
            <span className="etiqueta">Código de barras</span>
            <input
              value={nuevo.codigo_barras}
              onChange={(e) => setNuevo({ ...nuevo, codigo_barras: e.target.value })}
              placeholder="Escanéalo o escríbelo"
              autoComplete="off"
              required
            />
          </label>

          <label className="campo">
            <span className="etiqueta">Nombre</span>
            <input
              value={nuevo.nombre}
              onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })}
              placeholder="Cerveza Aguila 330ml"
              autoComplete="off"
              required
            />
          </label>

          <div className="dos-columnas">
            <label className="campo">
              <span className="etiqueta">Precio</span>
              <input
                className="num"
                value={nuevo.precio ? miles(Number(nuevo.precio)) : ''}
                onChange={(e) => setNuevo({ ...nuevo, precio: soloDigitos(e.target.value) })}
                inputMode="numeric"
                placeholder="0"
                required
              />
            </label>

            <label className="campo">
              <span className="etiqueta">Cuántos hay</span>
              <input
                className="num"
                value={nuevo.stock_actual ? miles(Number(nuevo.stock_actual)) : ''}
                onChange={(e) =>
                  setNuevo({ ...nuevo, stock_actual: soloDigitos(e.target.value) })
                }
                inputMode="numeric"
                placeholder="0"
              />
            </label>
          </div>

          <label className="campo">
            <span className="etiqueta">Categoría (opcional)</span>
            <input
              value={nuevo.categoria}
              onChange={(e) => setNuevo({ ...nuevo, categoria: e.target.value })}
              placeholder="cerveza, gaseosa, snacks…"
              autoComplete="off"
            />
          </label>

          <label className="casilla">
            <input
              type="checkbox"
              checked={nuevo.en_carta}
              onChange={(e) => setNuevo({ ...nuevo, en_carta: e.target.checked })}
            />
            <span>
              <b>Se pide en la mesa</b>
              <small>Márcalo en las bebidas: así el mesero las puede anotar.</small>
            </span>
          </label>

          <button className="btn-primario" type="submit" disabled={guardando}>
            {guardando ? 'Guardando…' : 'Agregar al catálogo'}
          </button>
        </form>
      </section>

      {/* ------------------------------------------------- lista */}
      <section className="tarjeta">
        <h2 className="tarjeta-titulo">
          Catálogo
          {productos && <span className="conteo">{productos.length}</span>}
        </h2>
        <p className="tarjeta-nota">
          {enCarta === 0
            ? 'Todavía no hay nada marcado para pedir en la mesa.'
            : `${enCarta} ${enCarta === 1 ? 'producto se pide' : 'productos se piden'} en la mesa.`}
        </p>

        {error && <p className="aviso aviso-error">{error}</p>}
        {listo && <p className="aviso aviso-ok">{listo}</p>}

        {productos === null && <p className="cargando">Cargando…</p>}

        {productos !== null && productos.length > 0 && (
          <label className="campo">
            <input
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder="Buscar por nombre o código"
              autoComplete="off"
            />
          </label>
        )}

        {productos?.length === 0 && (
          <p className="pista">El catálogo está vacío. Agrega el primero al lado.</p>
        )}

        {visibles.map((p) => (
          <div key={p.id} className="producto">
            <button type="button" className="producto-fila" onClick={() => abrir(p)}>
              <span className="producto-quien">
                <b>{p.nombre}</b>
                <small>
                  {p.codigo_barras}
                  {p.categoria ? ` · ${p.categoria}` : ''}
                  {' · quedan '}
                  {formatoCantidad(p.stock_actual)}
                </small>
              </span>
              {p.en_carta && <span className="chip-carta">mesa</span>}
              <span className="producto-precio num">{plata(p.precio_de_venta)}</span>
            </button>

            {abierto === p.id && (
              <div className="producto-editar">
                <label className="casilla">
                  <input
                    type="checkbox"
                    checked={p.en_carta}
                    onChange={(e) =>
                      cambiar(
                        p,
                        { en_carta: e.target.checked },
                        e.target.checked
                          ? `${p.nombre} ya se puede pedir en la mesa.`
                          : `${p.nombre} salió del menú del mesero.`,
                      )
                    }
                  />
                  <span>
                    <b>Se pide en la mesa</b>
                  </span>
                </label>

                <div className="campo">
                  <span className="etiqueta">Cambiar precio</span>
                  <input
                    className="num"
                    value={precioNuevo ? miles(Number(precioNuevo)) : ''}
                    onChange={(e) => setPrecioNuevo(soloDigitos(e.target.value))}
                    inputMode="numeric"
                    placeholder={String(p.precio_de_venta)}
                  />
                  <button
                    type="button"
                    className="btn-secundario"
                    disabled={!precioNuevo}
                    onClick={() => {
                      cambiar(
                        p,
                        { precio: Number(precioNuevo) },
                        `${p.nombre} ahora vale ${plata(Number(precioNuevo))}.`,
                      )
                      setPrecioNuevo('')
                    }}
                  >
                    Guardar precio
                  </button>
                </div>

                <div className="campo">
                  <span className="etiqueta">Corregir el conteo</span>
                  <input
                    className="num"
                    value={stockReal ? miles(Number(stockReal)) : ''}
                    onChange={(e) => setStockReal(soloDigitos(e.target.value))}
                    inputMode="numeric"
                    placeholder={String(p.stock_actual)}
                  />
                  <button
                    type="button"
                    className="btn-secundario"
                    disabled={!stockReal}
                    onClick={() => void ajustarStock(p)}
                  >
                    Ajustar a lo contado
                  </button>
                  <small className="pista">
                    Queda registrado como ajuste de inventario, con fecha y responsable.
                  </small>
                </div>
              </div>
            )}
          </div>
        ))}
      </section>
    </div>
  )
}
