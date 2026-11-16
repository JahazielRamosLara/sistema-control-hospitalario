// Tipos y cliente de la API FastAPI (/api, redirigido por el proxy de Vite).

export interface Config {
  turnos: string[]
  triage: string[]
  sexos: string[]
  tipos_sangre: string[]
  estados_paciente: string[]
  semaforos: string[]
}

export interface Servicio {
  id: number
  nombre: string
  ubicacion: string | null
  camas_censables: number
  jefe_id: number | null
  jefe_nombre?: string | null
}

export interface Medico {
  id: number
  nombre: string
  especialidad: string | null
  cedula_profesional: string | null
  turno: string | null
  activo: boolean
}

export interface TipoAtencion {
  id: number
  nombre: string
  categoria: string | null
}

export interface Riesgo {
  eventos_criticos: number
  nivel: string
  semaforo: string
  accion: string | null
  alerta: boolean
}

export interface Paciente {
  id: number
  expediente: string
  nombre: string
  servicio_id: number | null
  servicio: string | null
  medico_tratante_id: number | null
  medico_tratante: string | null
  fecha_nacimiento: string | null
  edad: number | null
  sexo: string | null
  tipo_sangre: string | null
  alergias: string | null
  contacto_emergencia: string | null
  telefono: string | null
  estado: string
  total_atenciones: number
  riesgo: Riesgo
}

export interface Atencion {
  id: number
  paciente_id: number
  expediente: string
  paciente: string
  servicio: string | null
  medico_tratante: string | null
  tipo_atencion_id: number
  tipo_atencion: string
  medico_id: number
  medico: string
  turno: string
  triage: string
  nota_clinica: string | null
  plan_manejo: string | null
  fecha: string
  evento_critico: boolean
  total_eventos_criticos: number
  nivel_riesgo: string
  semaforo: string
}

export interface PacienteDetalle extends Paciente {
  atenciones: Atencion[]
  ultima_atencion: string | null
}

export interface Umbral {
  id?: number
  eventos_minimos: number
  nivel: string
  semaforo: string
  accion: string | null
  alerta: boolean
}

export interface Indicadores {
  pacientes_registrados: number
  atenciones_registradas: number
  eventos_criticos: number
  pacientes_en_alerta: number
  medicos_activos: number
  camas_censables: number
  distribucion_riesgo: { nivel: string; semaforo: string; pacientes: number }[]
  atenciones_por_servicio: { servicio: string; atenciones: number; eventos_criticos: number }[]
  pacientes_prioritarios: Paciente[]
}

export type PacienteIn = Omit<
  Paciente,
  'id' | 'expediente' | 'servicio' | 'medico_tratante' | 'edad' | 'total_atenciones' | 'riesgo'
>

export interface AtencionIn {
  paciente_id: number
  tipo_atencion_id: number
  medico_id: number
  turno: string
  triage: string
  nota_clinica: string | null
  plan_manejo: string | null
  fecha: string | null
  evento_critico: boolean
}

export type Rol = 'admin' | 'jefatura' | 'medico' | 'admision'

export interface UsuarioActual {
  id: number
  usuario: string
  nombre: string
  rol: Rol
  rol_nombre: string
  debe_cambiar_password: boolean
}

export interface Usuario {
  id: number
  usuario: string
  nombre: string
  rol: Rol
  activo: boolean
  debe_cambiar_password: boolean
  bloqueado: boolean
  ultimo_acceso: string | null
}

export interface EventoAcceso {
  fecha: string
  usuario: string
  evento: string
  exito: boolean
  ip: string | null
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function mensaje(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: (string | number)[]; msg?: string }) => {
        const campo = d.loc?.filter((x) => x !== 'body').join('.')
        return `${campo ? campo + ': ' : ''}${(d.msg ?? '').replace(/^Value error, /, '')}`
      })
      .join(' · ')
  }
  return 'Error inesperado'
}

async function request<T>(method: string, url: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'X-Requested-With': 'fetch' } // cabecera anti-CSRF
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const res = await fetch(`/api${url}`, {
    method,
    headers,
    credentials: 'same-origin',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  // Sesión expirada o revocada: la app vuelve a la pantalla de login
  if (res.status === 401 && !url.startsWith('/auth/login')) window.dispatchEvent(new Event('sesion-expirada'))
  if (!res.ok) {
    let detalle: unknown = res.statusText
    try {
      detalle = (await res.json()).detail
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(res.status, mensaje(detalle))
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

function qs(params: Record<string, string | number | boolean | null | undefined>): string {
  const s = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '' && v !== false) s.set(k, String(v))
  }
  const t = s.toString()
  return t ? `?${t}` : ''
}

export const api = {
  login: (usuario: string, password: string) => request<UsuarioActual>('POST', '/auth/login', { usuario, password }),
  logout: () => request<void>('POST', '/auth/logout'),
  yo: () => request<UsuarioActual>('GET', '/auth/me'),
  cambiarPassword: (actual: string, nueva: string) =>
    request<UsuarioActual>('POST', '/auth/cambiar-password', { actual, nueva }),

  usuarios: () => request<Usuario[]>('GET', '/usuarios'),
  roles: () => request<Record<Rol, string>>('GET', '/usuarios/roles'),
  crearUsuario: (u: { usuario: string; nombre: string; rol: Rol }) =>
    request<{ usuario: Usuario; password_temporal: string }>('POST', '/usuarios', u),
  editarUsuario: (id: number, u: { nombre: string; rol: Rol; activo: boolean }) =>
    request<Usuario>('PUT', `/usuarios/${id}`, u),
  restablecerPassword: (id: number) =>
    request<{ usuario: Usuario; password_temporal: string }>('POST', `/usuarios/${id}/restablecer-password`),
  accesos: (limit = 200) => request<EventoAcceso[]>('GET', `/usuarios/accesos?limit=${limit}`),

  config: () => request<Config>('GET', '/config'),
  indicadores: () => request<Indicadores>('GET', '/indicadores'),

  servicios: () => request<Servicio[]>('GET', '/servicios'),
  guardarServicio: (s: Omit<Servicio, 'id'>, id?: number) =>
    id ? request<Servicio>('PUT', `/servicios/${id}`, s) : request<Servicio>('POST', '/servicios', s),
  eliminarServicio: (id: number) => request<void>('DELETE', `/servicios/${id}`),

  medicos: (soloActivos = false) => request<Medico[]>('GET', `/medicos${qs({ solo_activos: soloActivos })}`),
  guardarMedico: (m: Omit<Medico, 'id'>, id?: number) =>
    id ? request<Medico>('PUT', `/medicos/${id}`, m) : request<Medico>('POST', '/medicos', m),
  eliminarMedico: (id: number) => request<void>('DELETE', `/medicos/${id}`),

  tipos: () => request<TipoAtencion[]>('GET', '/tipos-atencion'),
  guardarTipo: (t: Omit<TipoAtencion, 'id'>, id?: number) =>
    id ? request<TipoAtencion>('PUT', `/tipos-atencion/${id}`, t) : request<TipoAtencion>('POST', '/tipos-atencion', t),
  eliminarTipo: (id: number) => request<void>('DELETE', `/tipos-atencion/${id}`),

  pacientes: (f: { q?: string; servicio_id?: number | ''; nivel?: string; solo_alerta?: boolean } = {}) =>
    request<Paciente[]>('GET', `/pacientes${qs(f)}`),
  paciente: (id: number) => request<PacienteDetalle>('GET', `/pacientes/${id}`),
  pacientePorExpediente: (exp: string) =>
    request<PacienteDetalle>('GET', `/pacientes/expediente/${encodeURIComponent(exp)}`),
  siguienteExpediente: () => request<{ expediente: string }>('GET', '/pacientes/siguiente-expediente'),
  guardarPaciente: (p: PacienteIn, id?: number) =>
    id ? request<Paciente>('PUT', `/pacientes/${id}`, p) : request<Paciente>('POST', '/pacientes', p),
  eliminarPaciente: (id: number) => request<void>('DELETE', `/pacientes/${id}`),
  urlExpedientePdf: (id: number) => `/api/pacientes/${id}/expediente.pdf`,

  atenciones: (f: {
    paciente_id?: number
    medico_id?: number | ''
    servicio_id?: number | ''
    turno?: string
    solo_criticos?: boolean
    desde?: string
    hasta?: string
    q?: string
    limit?: number
    offset?: number
  }) => request<{ total: number; items: Atencion[] }>('GET', `/atenciones${qs(f)}`),
  guardarAtencion: (a: AtencionIn, id?: number) =>
    id ? request<Atencion>('PUT', `/atenciones/${id}`, a) : request<Atencion>('POST', '/atenciones', a),
  eliminarAtencion: (id: number) => request<void>('DELETE', `/atenciones/${id}`),

  riesgo: () => request<Umbral[]>('GET', '/riesgo'),
  guardarRiesgo: (u: Umbral[]) => request<Umbral[]>('PUT', '/riesgo', u),
}
