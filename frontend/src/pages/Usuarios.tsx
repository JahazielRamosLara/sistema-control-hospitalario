import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, type EventoAcceso, type Rol, type Usuario } from '../api'
import { useAuth } from '../auth'
import { Campo, Cargando, ErrorMsg, Modal } from '../components/ui'

const EVENTOS: Record<string, string> = {
  login: 'Inicio de sesión',
  logout: 'Cierre de sesión',
  login_fallido: 'Contraseña incorrecta',
  login_bloqueado: 'Intento con cuenta bloqueada',
  cuenta_bloqueada: 'Cuenta bloqueada',
  login_ip_limitada: 'Demasiados intentos (IP)',
  cambio_password: 'Cambio de contraseña',
}

function fechaHora(iso: string | null) {
  return iso ? new Date(iso).toLocaleString('es-MX', { dateStyle: 'short', timeStyle: 'short' }) : '—'
}

export function Usuarios() {
  const [pestana, setPestana] = useState<'usuarios' | 'accesos'>('usuarios')
  return (
    <>
      <header className="pagina-header">
        <div>
          <h1>Usuarios</h1>
          <p className="subtitulo">Cuentas de acceso, perfiles y bitácora de accesos</p>
        </div>
      </header>
      <div className="pestanas" role="tablist">
        <button role="tab" aria-selected={pestana === 'usuarios'} className={pestana === 'usuarios' ? 'activa' : ''} onClick={() => setPestana('usuarios')}>
          Cuentas
        </button>
        <button role="tab" aria-selected={pestana === 'accesos'} className={pestana === 'accesos' ? 'activa' : ''} onClick={() => setPestana('accesos')}>
          Bitácora de accesos
        </button>
      </div>
      {pestana === 'usuarios' ? <Cuentas /> : <Accesos />}
    </>
  )
}

function Cuentas() {
  const { usuario: yo } = useAuth()
  const [lista, setLista] = useState<Usuario[] | null>(null)
  const [roles, setRoles] = useState<Record<string, string>>({})
  const [error, setError] = useState<unknown>(null)
  const [editando, setEditando] = useState<Usuario | 'nuevo' | null>(null)
  const [temporal, setTemporal] = useState<{ usuario: string; password: string } | null>(null)

  const cargar = useCallback(() => {
    api.usuarios().then(setLista).catch(setError)
  }, [])
  useEffect(() => {
    cargar()
    api.roles().then(setRoles).catch(() => {})
  }, [cargar])

  async function restablecer(u: Usuario) {
    if (!confirm(`¿Generar una contraseña temporal para ${u.usuario}? Se cerrarán sus sesiones abiertas.`)) return
    try {
      const r = await api.restablecerPassword(u.id)
      setTemporal({ usuario: u.usuario, password: r.password_temporal })
      cargar()
    } catch (e) {
      setError(e)
    }
  }

  if (!lista) return error ? <ErrorMsg error={error} /> : <Cargando />

  return (
    <section className="bloque">
      <div className="barra-tabla">
        <span>{lista.length} cuentas</span>
        <button className="btn btn-primario" onClick={() => setEditando('nuevo')}>Agregar usuario</button>
      </div>
      <ErrorMsg error={error} />
      <div className="tabla-scroll">
        <table className="tabla">
          <thead>
            <tr><th>Usuario</th><th>Nombre</th><th>Perfil</th><th>Estado</th><th>Último acceso</th><th /></tr>
          </thead>
          <tbody>
            {lista.map((u) => (
              <tr key={u.id} className={u.activo ? '' : 'inactivo'}>
                <td className="mono">{u.usuario}{u.id === yo?.id && <span className="etiqueta">tú</span>}</td>
                <td>{u.nombre}</td>
                <td>{roles[u.rol] ?? u.rol}</td>
                <td>
                  {!u.activo ? 'Inactivo' : u.bloqueado ? <span className="marca-critica">Bloqueado</span> : u.debe_cambiar_password ? 'Contraseña temporal' : 'Activo'}
                </td>
                <td className="nowrap">{fechaHora(u.ultimo_acceso)}</td>
                <td className="nowrap">
                  <button className="btn-texto" onClick={() => setEditando(u)}>Editar</button>
                  <button className="btn-texto" onClick={() => restablecer(u)}>Restablecer contraseña</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal titulo={editando === 'nuevo' ? 'Nuevo usuario' : 'Editar usuario'} abierto={editando !== null} onCerrar={() => setEditando(null)} ancho={520}>
        <FormUsuario
          usuario={editando && editando !== 'nuevo' ? editando : undefined}
          esYo={editando !== 'nuevo' && editando?.id === yo?.id}
          roles={roles}
          onCancelar={() => setEditando(null)}
          onListo={(t) => {
            setEditando(null)
            if (t) setTemporal(t)
            cargar()
          }}
        />
      </Modal>

      <Modal titulo="Contraseña temporal" abierto={temporal !== null} onCerrar={() => setTemporal(null)} ancho={480}>
        {temporal && (
          <div className="formulario">
            <p>
              Entrega esta contraseña a <strong className="mono">{temporal.usuario}</strong> por un medio seguro. Solo se
              muestra esta vez; el sistema pedirá cambiarla en el primer inicio de sesión.
            </p>
            <code className="password-temporal">{temporal.password}</code>
            <footer className="acciones">
              <button className="btn" onClick={() => void navigator.clipboard?.writeText(temporal.password)}>Copiar</button>
              <button className="btn btn-primario" onClick={() => setTemporal(null)}>Listo</button>
            </footer>
          </div>
        )}
      </Modal>
    </section>
  )
}

function FormUsuario({
  usuario,
  esYo,
  roles,
  onCancelar,
  onListo,
}: {
  usuario?: Usuario
  esYo: boolean
  roles: Record<string, string>
  onCancelar: () => void
  onListo: (temporal?: { usuario: string; password: string }) => void
}) {
  const [d, setD] = useState({
    usuario: usuario?.usuario ?? '',
    nombre: usuario?.nombre ?? '',
    rol: (usuario?.rol ?? 'medico') as Rol,
    activo: usuario?.activo ?? true,
  })
  const [error, setError] = useState<unknown>(null)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    try {
      if (usuario) {
        await api.editarUsuario(usuario.id, { nombre: d.nombre, rol: d.rol, activo: d.activo })
        onListo()
      } else {
        const r = await api.crearUsuario({ usuario: d.usuario, nombre: d.nombre, rol: d.rol })
        onListo({ usuario: r.usuario.usuario, password: r.password_temporal })
      }
    } catch (err) {
      setError(err)
    }
  }

  return (
    <form onSubmit={enviar} className="formulario">
      <div className="rejilla">
        <Campo etiqueta="Usuario *" ayuda={usuario ? 'No se puede cambiar' : 'Minúsculas, números, punto o guion'}>
          <input required minLength={3} maxLength={40} pattern="[A-Za-z0-9._\-]+" autoCapitalize="none" disabled={!!usuario}
            value={d.usuario} onChange={(e) => setD({ ...d, usuario: e.target.value })} autoFocus={!usuario} />
        </Campo>
        <Campo etiqueta="Perfil *">
          <select value={d.rol} disabled={esYo} onChange={(e) => setD({ ...d, rol: e.target.value as Rol })}>
            {Object.entries(roles).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </Campo>
        <Campo etiqueta="Nombre completo *" ancho="completo">
          <input required minLength={3} value={d.nombre} onChange={(e) => setD({ ...d, nombre: e.target.value })} />
        </Campo>
        {usuario && (
          <label className="filtro-check campo-completo">
            <input type="checkbox" checked={d.activo} disabled={esYo} onChange={(e) => setD({ ...d, activo: e.target.checked })} />
            Cuenta activa (al desactivarla se cierran sus sesiones)
          </label>
        )}
      </div>
      {!usuario && <p className="nota">Se generará una contraseña temporal que el usuario deberá cambiar al entrar.</p>}
      <ErrorMsg error={error} />
      <footer className="acciones">
        <button type="button" className="btn" onClick={onCancelar}>Cancelar</button>
        <button type="submit" className="btn btn-primario">Guardar</button>
      </footer>
    </form>
  )
}

function Accesos() {
  const [eventos, setEventos] = useState<EventoAcceso[] | null>(null)
  const [error, setError] = useState<unknown>(null)
  useEffect(() => {
    api.accesos().then(setEventos).catch(setError)
  }, [])
  if (!eventos) return error ? <ErrorMsg error={error} /> : <Cargando />
  return (
    <section className="bloque">
      <div className="tabla-scroll">
        <table className="tabla tabla-densa">
          <thead><tr><th>Fecha</th><th>Usuario</th><th>Evento</th><th>Resultado</th><th>IP</th></tr></thead>
          <tbody>
            {eventos.map((e, i) => (
              <tr key={i} className={e.exito ? '' : 'fila-critica'}>
                <td className="nowrap">{fechaHora(e.fecha)}</td>
                <td className="mono">{e.usuario}</td>
                <td>{EVENTOS[e.evento] ?? e.evento.replace(/_/g, ' ').replace(':', ': ')}</td>
                <td>{e.exito ? 'Correcto' : <span className="marca-critica">Fallido</span>}</td>
                <td className="mono tenue">{e.ip ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="nota">Últimos {eventos.length} eventos.</p>
    </section>
  )
}
