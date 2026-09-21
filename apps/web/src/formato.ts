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
