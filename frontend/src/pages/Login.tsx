import { useState, type FormEvent } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { Campo, ErrorMsg } from '../components/ui'

export function Login() {
  const { entrar, aviso } = useAuth()
  const [usuario, setUsuario] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setEnviando(true)
    setError(null)
    try {
      await entrar(usuario, password)
    } catch (err) {
      setError(err)
      setPassword('')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="acceso">
      <form className="acceso-hoja" onSubmit={enviar}>
        <div className="marca">
          <span className="marca-cruz" aria-hidden />
          <span>
            <strong>Control Hospitalario</strong>
            <small>Acceso para personal autorizado</small>
          </span>
        </div>
        {aviso && <div className="alerta-aviso">{aviso}</div>}
        <Campo etiqueta="Usuario">
          <input
            autoFocus
            required
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            maxLength={40}
            value={usuario}
            onChange={(e) => setUsuario(e.target.value)}
          />
        </Campo>
        <Campo etiqueta="Contraseña">
          <input
            type="password"
            required
            autoComplete="current-password"
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Campo>
        <ErrorMsg error={error} />
        <button type="submit" className="btn btn-primario btn-bloque" disabled={enviando}>
          {enviando ? 'Verificando…' : 'Iniciar sesión'}
        </button>
        <p className="nota">
          La sesión se cierra tras 30 minutos sin actividad. Si olvidaste tu contraseña, pide al administrador que la
          restablezca.
        </p>
      </form>
    </div>
  )
}

export function CambiarPassword({ obligatorio, onListo }: { obligatorio?: boolean; onListo?: () => void }) {
  const { usuario, actualizar, salir } = useAuth()
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [confirmar, setConfirmar] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [enviando, setEnviando] = useState(false)

  const reglas = [
    { ok: nueva.length >= 10, texto: 'Al menos 10 caracteres' },
    { ok: /[a-zA-Z]/.test(nueva) && /\d/.test(nueva), texto: 'Letras y números' },
    { ok: !!nueva && !nueva.toLowerCase().includes(usuario?.usuario ?? '\u0000'), texto: 'No contiene tu usuario' },
    { ok: !!nueva && nueva === confirmar, texto: 'Las dos contraseñas coinciden' },
  ]

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (!reglas.every((r) => r.ok)) {
      setError(new Error('La nueva contraseña no cumple los requisitos'))
      return
    }
    setEnviando(true)
    setError(null)
    try {
      actualizar(await api.cambiarPassword(actual, nueva))
      onListo?.()
    } catch (err) {
      setError(err)
    } finally {
      setEnviando(false)
    }
  }

  const formulario = (
    <form className="formulario" onSubmit={enviar}>
      {obligatorio && (
        <p className="alerta-aviso">
          Hola, {usuario?.nombre}. Estás usando una contraseña temporal: define una propia para continuar.
        </p>
      )}
      <Campo etiqueta={obligatorio ? 'Contraseña temporal' : 'Contraseña actual'}>
        <input type="password" required autoComplete="current-password" value={actual} onChange={(e) => setActual(e.target.value)} autoFocus />
      </Campo>
      <Campo etiqueta="Nueva contraseña">
        <input type="password" required autoComplete="new-password" maxLength={128} value={nueva} onChange={(e) => setNueva(e.target.value)} />
      </Campo>
      <Campo etiqueta="Confirmar nueva contraseña">
        <input type="password" required autoComplete="new-password" maxLength={128} value={confirmar} onChange={(e) => setConfirmar(e.target.value)} />
      </Campo>
      <ul className="reglas">
        {reglas.map((r) => (
          <li key={r.texto} className={r.ok ? 'ok' : ''}>
            {r.texto}
          </li>
        ))}
      </ul>
      <ErrorMsg error={error} />
      <footer className="acciones">
        {obligatorio ? (
          <button type="button" className="btn" onClick={() => void salir()}>
            Salir
          </button>
        ) : (
          <button type="button" className="btn" onClick={onListo}>
            Cancelar
          </button>
        )}
        <button type="submit" className="btn btn-primario" disabled={enviando}>
          {enviando ? 'Guardando…' : 'Guardar contraseña'}
        </button>
      </footer>
      {!obligatorio && <p className="nota">Al cambiarla se cerrarán tus sesiones abiertas en otros equipos.</p>}
    </form>
  )

  if (!obligatorio) return formulario
  return (
    <div className="acceso">
      <div className="acceso-hoja">
        <h2>Cambiar contraseña</h2>
        {formulario}
      </div>
    </div>
  )
}
