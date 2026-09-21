import type { Sesion } from './tipos'

const LLAVE = 'elcampus.sesion'

export function leerSesion(): Sesion | null {
  try {
    const guardada = localStorage.getItem(LLAVE)
    return guardada ? (JSON.parse(guardada) as Sesion) : null
  } catch {
    return null
  }
}

export function guardarSesion(sesion: Sesion) {
  localStorage.setItem(LLAVE, JSON.stringify(sesion))
}

export function borrarSesion() {
  localStorage.removeItem(LLAVE)
}

export class ErrorApi extends Error {}

async function pedir<T>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  const sesion = leerSesion()

  const respuesta = await fetch(`/api${ruta}`, {
    ...opciones,
    headers: {
      'Content-Type': 'application/json',
      ...(sesion ? { Authorization: `Bearer ${sesion.access_token}` } : {}),
      ...opciones.headers,
    },
  })

  if (respuesta.status === 401) {
    borrarSesion()
    window.location.replace('/login')
    throw new ErrorApi('Tu sesión venció.')
  }

  if (!respuesta.ok) {
    // El backend manda mensajes ya escritos para la gente del negocio;
    // se muestran tal cual en vez de inventar uno genérico.
    const cuerpo = await respuesta.json().catch(() => null)
    throw new ErrorApi(cuerpo?.detail ?? 'No se pudo completar. Intenta otra vez.')
  }

  if (respuesta.status === 204) return undefined as T
  return (await respuesta.json()) as T
}

export const api = {
  get: <T>(ruta: string) => pedir<T>(ruta),
  post: <T>(ruta: string, datos?: unknown) =>
    pedir<T>(ruta, { method: 'POST', body: JSON.stringify(datos ?? {}) }),
  patch: <T>(ruta: string, datos: unknown) =>
    pedir<T>(ruta, { method: 'PATCH', body: JSON.stringify(datos) }),
  borrar: <T>(ruta: string) => pedir<T>(ruta, { method: 'DELETE' }),
}

export async function entrar(nombre: string, clave: string): Promise<Sesion> {
  const sesion = await pedir<Sesion>('/auth/entrar', {
    method: 'POST',
    body: JSON.stringify({ nombre, clave }),
  })
  guardarSesion(sesion)
  return sesion
}
