const pesos = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 0,
})

/** $59.200 — el peso colombiano no maneja centavos en caja. */
export const plata = (valor: number) => pesos.format(Math.round(valor))

/** 0,4 kg se muestra con coma; 2 unidades sin decimales sobrantes. */
export const cantidad = (valor: number) =>
  Number.isInteger(valor) ? String(valor) : valor.toFixed(3).replace(/\.?0+$/, '').replace('.', ',')

export const hora = (iso: string) =>
  new Date(iso).toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' })

const agrupado = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 0 })

/** 12000 → "12.000". Sin el signo de pesos: para campos donde se escribe. */
export const miles = (valor: number) => agrupado.format(valor)

/** Deja solo los dígitos de lo que la persona alcanzó a escribir.
 *  Así el campo aguanta que peguen "$ 12.000" o que se les escape una letra. */
export const soloDigitos = (texto: string) => texto.replace(/\D/g, '').slice(0, 12)
