import { useEffect, useRef, type ReactNode } from 'react'

const SEMAFORO_CLASE: Record<string, string> = {
  Verde: 'verde',
  Amarillo: 'amarillo',
  Naranja: 'naranja',
  Rojo: 'rojo',
  Vino: 'vino',
}

export function RiesgoBadge({ nivel, semaforo, eventos }: { nivel: string; semaforo: string; eventos?: number }) {
  return (
    <span className={`badge sem-${SEMAFORO_CLASE[semaforo] ?? 'gris'}`} title={`Semáforo ${semaforo}`}>
      <span className="dot" />
      {nivel}
      {eventos !== undefined && <span className="badge-num">{eventos}</span>}
    </span>
  )
}

export function TriageBadge({ triage }: { triage: string }) {
  const nivel = triage.split(' ')[0] // I, II, III, IV, V
  const nombre = triage.match(/\((.*)\)/)?.[1] ?? triage
  return (
    <span className={`triage triage-${nivel}`} title={triage}>
      <span className="mono">{nivel}</span> {nombre}
    </span>
  )
}

export function Cargando({ texto = 'Cargando…' }: { texto?: string }) {
  return <div className="estado-vacio">{texto}</div>
}

export function ErrorMsg({ error }: { error: unknown }) {
  if (!error) return null
  return <div className="alerta-error">{error instanceof Error ? error.message : String(error)}</div>
}

export function Modal({
  titulo,
  abierto,
  onCerrar,
  children,
  ancho = 640,
}: {
  titulo: string
  abierto: boolean
  onCerrar: () => void
  children: ReactNode
  ancho?: number
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (abierto && !d.open) d.showModal()
    if (!abierto && d.open) d.close()
  }, [abierto])
  return (
    <dialog ref={ref} className="modal" style={{ maxWidth: ancho }} onClose={onCerrar}>
      <header className="modal-header">
        <h2>{titulo}</h2>
        <button type="button" className="btn-icono" onClick={onCerrar} aria-label="Cerrar">
          ×
        </button>
      </header>
      <div className="modal-body">{abierto && children}</div>
    </dialog>
  )
}

export function Campo({
  etiqueta,
  children,
  ancho,
  ayuda,
}: {
  etiqueta: string
  children: ReactNode
  ancho?: 'completo' | 'medio'
  ayuda?: string
}) {
  return (
    <label className={`campo ${ancho === 'completo' ? 'campo-completo' : ''}`}>
      <span className="campo-etiqueta">{etiqueta}</span>
      {children}
      {ayuda && <span className="campo-ayuda">{ayuda}</span>}
    </label>
  )
}

export function Kpi({ etiqueta, valor, tono }: { etiqueta: string; valor: number | string; tono?: string }) {
  return (
    <div className={`kpi ${tono ? 'kpi-' + tono : ''}`}>
      <span className="kpi-valor">{valor}</span>
      <span className="kpi-etiqueta">{etiqueta}</span>
    </div>
  )
}
