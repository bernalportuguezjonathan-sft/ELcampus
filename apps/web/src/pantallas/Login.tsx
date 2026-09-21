import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { entrar as pedirSesion } from '../api/cliente'
import { pantallaDe, useSesion } from '../sesion'

export default function Login() {
  const [nombre, setNombre] = useState('')
  const [clave, setClave] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [entrando, setEntrando] = useState(false)
  const { entrar } = useSesion()
  const navegar = useNavigate()

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setEntrando(true)
    try {
      const sesion = await pedirSesion(nombre.trim(), clave)
      entrar(sesion)
      navegar(pantallaDe(sesion.rol), { replace: true })
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo entrar.')
    } finally {
      setEntrando(false)
    }
  }

  return (
    <div className="centrado">
      <form className="login" onSubmit={enviar}>
        <div className="login-marca">
          <span className="login-iconos">🍺 🔥 🛒</span>
          <h1>EL CAMPUS</h1>
          <span className="login-lema">Bar · Grill · Fun &amp; Market</span>
        </div>

        <label className="campo">
          <span className="etiqueta">Tu nombre</span>
          <input
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            autoFocus
            autoComplete="username"
            required
          />
        </label>

        <label className="campo">
          <span className="etiqueta">Clave</span>
          <input
            type="password"
            value={clave}
            onChange={(e) => setClave(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        {error && <p className="aviso aviso-error">{error}</p>}

        <button className="btn-primario" type="submit" disabled={entrando}>
          {entrando ? 'ENTRANDO…' : 'ENTRAR'}
        </button>
      </form>
    </div>
  )
}
