import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, type Config, type Medico, type Servicio, type TipoAtencion } from './api'

interface Catalogos {
  config: Config | null
  servicios: Servicio[]
  medicos: Medico[]
  tipos: TipoAtencion[]
  error: unknown
  recargar: () => Promise<void>
}

const Ctx = createContext<Catalogos | null>(null)

export function CatalogosProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<Config | null>(null)
  const [servicios, setServicios] = useState<Servicio[]>([])
  const [medicos, setMedicos] = useState<Medico[]>([])
  const [tipos, setTipos] = useState<TipoAtencion[]>([])
  const [error, setError] = useState<unknown>(null)

  const recargar = useCallback(async () => {
    try {
      const [c, s, m, t] = await Promise.all([api.config(), api.servicios(), api.medicos(), api.tipos()])
      setConfig(c)
      setServicios(s)
      setMedicos(m)
      setTipos(t)
      setError(null)
    } catch (e) {
      setError(e)
    }
  }, [])

  useEffect(() => {
    void recargar()
  }, [recargar])

  return <Ctx.Provider value={{ config, servicios, medicos, tipos, error, recargar }}>{children}</Ctx.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useCatalogos(): Catalogos {
  const c = useContext(Ctx)
  if (!c) throw new Error('useCatalogos fuera de CatalogosProvider')
  return c
}
