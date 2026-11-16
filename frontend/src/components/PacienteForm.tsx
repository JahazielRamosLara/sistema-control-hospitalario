import { useEffect, useState, type FormEvent } from 'react'
import { api, type Paciente, type PacienteIn } from '../api'
import { useCatalogos } from '../catalogos'
import { hoyISO } from '../formato'
import { Campo, ErrorMsg } from './ui'

const VACIO: PacienteIn = {
  nombre: '',
  servicio_id: null,
  medico_tratante_id: null,
  fecha_nacimiento: null,
  sexo: null,
  tipo_sangre: null,
  alergias: 'Ninguna conocida',
  contacto_emergencia: null,
  telefono: null,
  estado: 'Activo',
}

export function PacienteForm({
  paciente,
  onGuardado,
  onCancelar,
}: {
  paciente?: Paciente
  onGuardado: (p: Paciente) => void
  onCancelar: () => void
}) {
  const { config, servicios, medicos } = useCatalogos()
  const [datos, setDatos] = useState<PacienteIn>(() =>
    paciente ? { ...VACIO, ...pick(paciente) } : VACIO,
  )
  const [expediente, setExpediente] = useState(paciente?.expediente ?? '…')
  const [error, setError] = useState<unknown>(null)
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    if (!paciente) api.siguienteExpediente().then((r) => setExpediente(r.expediente)).catch(() => {})
  }, [paciente])

  const set = <K extends keyof PacienteIn>(k: K, v: PacienteIn[K]) => setDatos((d) => ({ ...d, [k]: v }))
  const texto = (k: keyof PacienteIn) => (e: { target: { value: string } }) =>
    set(k, (e.target.value.trim() === '' ? null : e.target.value) as never)
  const numero = (k: 'servicio_id' | 'medico_tratante_id') => (e: { target: { value: string } }) =>
    set(k, e.target.value ? Number(e.target.value) : null)

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setGuardando(true)
    setError(null)
    try {
      onGuardado(await api.guardarPaciente({ ...datos, nombre: datos.nombre.trim() }, paciente?.id))
    } catch (err) {
      setError(err)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <form onSubmit={enviar} className="formulario">
      <div className="expediente-asignado">
        Expediente <strong>{expediente}</strong>
        {!paciente && <span> · se asigna automáticamente al guardar</span>}
      </div>
      <div className="rejilla">
        <Campo etiqueta="Nombre completo *" ancho="completo">
          <input
            required
            minLength={3}
            autoFocus
            value={datos.nombre}
            onChange={(e) => set('nombre', e.target.value)}
            placeholder="Apellido paterno, materno y nombre(s)"
          />
        </Campo>
        <Campo etiqueta="Servicio">
          <select value={datos.servicio_id ?? ''} onChange={numero('servicio_id')}>
            <option value="">— Sin asignar —</option>
            {servicios.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nombre}
              </option>
            ))}
          </select>
        </Campo>
        <Campo etiqueta="Médico tratante">
          <select value={datos.medico_tratante_id ?? ''} onChange={numero('medico_tratante_id')}>
            <option value="">— Sin asignar —</option>
            {medicos
              .filter((m) => m.activo || m.id === datos.medico_tratante_id)
              .map((m) => (
                <option key={m.id} value={m.id}>
                  {m.nombre}
                </option>
              ))}
          </select>
        </Campo>
        <Campo etiqueta="Fecha de nacimiento">
          <input type="date" max={hoyISO()} value={datos.fecha_nacimiento ?? ''} onChange={texto('fecha_nacimiento')} />
        </Campo>
        <Campo etiqueta="Sexo">
          <select value={datos.sexo ?? ''} onChange={texto('sexo')}>
            <option value="">—</option>
            {config?.sexos.map((s) => (
              <option key={s} value={s}>
                {s === 'M' ? 'Masculino' : 'Femenino'}
              </option>
            ))}
          </select>
        </Campo>
        <Campo etiqueta="Tipo de sangre">
          <select value={datos.tipo_sangre ?? ''} onChange={texto('tipo_sangre')}>
            <option value="">—</option>
            {config?.tipos_sangre.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </Campo>
        <Campo etiqueta="Estado">
          <select value={datos.estado} onChange={(e) => set('estado', e.target.value)}>
            {config?.estados_paciente.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </Campo>
        <Campo etiqueta="Alergias" ancho="completo">
          <input value={datos.alergias ?? ''} onChange={texto('alergias')} />
        </Campo>
        <Campo etiqueta="Contacto de emergencia">
          <input value={datos.contacto_emergencia ?? ''} onChange={texto('contacto_emergencia')} />
        </Campo>
        <Campo etiqueta="Teléfono">
          <input type="tel" value={datos.telefono ?? ''} onChange={texto('telefono')} />
        </Campo>
      </div>
      <ErrorMsg error={error} />
      <footer className="acciones">
        <button type="button" className="btn" onClick={onCancelar}>
          Cancelar
        </button>
        <button type="submit" className="btn btn-primario" disabled={guardando}>
          {guardando ? 'Guardando…' : paciente ? 'Guardar cambios' : 'Dar de alta'}
        </button>
      </footer>
    </form>
  )
}

function pick(p: Paciente): PacienteIn {
  const { nombre, servicio_id, medico_tratante_id, fecha_nacimiento, sexo, tipo_sangre, alergias, contacto_emergencia, telefono, estado } = p
  return { nombre, servicio_id, medico_tratante_id, fecha_nacimiento, sexo, tipo_sangre, alergias, contacto_emergencia, telefono, estado }
}
