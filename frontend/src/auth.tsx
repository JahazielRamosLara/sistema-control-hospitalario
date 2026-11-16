import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, type Rol, type UsuarioActual } from './api'

// Qué puede hacer cada perfil (el backend aplica las mismas reglas; aquí solo se ocultan botones).
const PERMISOS = {
  pacientes: ['admin', 'admision'], // alta y edición de pacientes
  atenciones: ['admin', 'medico'], // registrar y editar atenciones
  eliminar: ['admin'],
  catalogos: ['admin'],
  usuarios: ['admin'],
} satisfies Record<string, Rol[]>

export type Permiso = keyof typeof PERMISOS

interface Auth {
  usuario: UsuarioActual | null
  cargando: boolean
  aviso: string
  entrar: (usuario: string, password: string) => Promise<void>
  salir: () => Promise<void>
  actualizar: (u: UsuarioActual) => void
  puede: (p: Permiso) => boolean
}

const Ctx = createContext<Auth | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<UsuarioActual | null>(null)
  const [cargando, setCargando] = useState(true)
  const [aviso, setAviso] = useState('')

  useEffect(() => {
    api
      .yo()
      .then(setUsuario)
      .catch(() => setUsuario(null))
      .finally(() => setCargando(false))
    const expirada = () => {
      setUsuario((u) => {
        if (u) setAviso('Tu sesión expiró o fue cerrada. Vuelve a iniciar sesión.')
        return null
      })
    }
    window.addEventListener('sesion-expirada', expirada)
    return () => window.removeEventListener('sesion-expirada', expirada)
  }, [])

  const entrar = useCallback(async (u: string, p: string) => {
    setUsuario(await api.login(u, p))
    setAviso('')
  }, [])

  const salir = useCallback(async () => {
    try {
      await api.logout()
    } finally {
      setUsuario(null)
      setAviso('')
    }
  }, [])

  const puede = useCallback(
    (p: Permiso) => !!usuario && (PERMISOS[p] as readonly string[]).includes(usuario.rol),
    [usuario],
  )

  return (
    <Ctx.Provider value={{ usuario, cargando, aviso, entrar, salir, actualizar: setUsuario, puede }}>
      {children}
    </Ctx.Provider>
  )
}

export function useAuth(): Auth {
  const c = useContext(Ctx)
  if (!c) throw new Error('useAuth fuera de AuthProvider')
  return c
}
