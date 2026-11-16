import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { api, type Atencion, type AtencionIn, type Paciente } from '../api'
import { useCatalogos } from '../catalogos'
import { hoyISO } from '../formato'
import { Campo, ErrorMsg, RiesgoBadge } from './ui'

export function AtencionForm({
  atencion,
  pacienteId,
  onGuardado,
  onCancelar,
}: {
  atencion?: Atencion
  pacienteId?: number
  onGuardado: (a: Atencion) => void
  onCancelar: () => void
}) {
  const { config, medicos, tipos } = useCatalogos()
  const [pacientes, setPacientes] = useState<Paciente[]>([])
  const [expediente, setExpediente] = useState(atencion?.expediente ?? '')
  const [datos, setDatos] = useState<Omit<AtencionIn, 'paciente_id'>>(() => ({
    tipo_atencion_id: atencion?.tipo_atencion_id ?? 0,
    medico_id: atencion?.medico_id ?? 0,
    turno: atencion?.turno ?? '',
    triage: atencion?.triage ?? '',
    nota_clinica: atencion?.nota_clinica ?? '',
    plan_manejo: atencion?.plan_manejo ?? '',
    fecha: atencion?.fecha ?? hoyISO(),
    evento_critico: atencion?.evento_critico ?? false,
  }))
  const [error, setError] = useState<unknown>(null)
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    api.pacientes().then((ps) => {
      setPacientes(ps)
      if (pacienteId && !atencion) setExpediente(ps.find((p) => p.id === pacienteId)?.expediente ?? '')
    })
  }, [pacienteId, atencion])

  // Búsqueda automática: al indicar el expediente se completan nombre, servicio y médico tratante.
  const paciente = useMemo(
    () => pacientes.find((p) => p.expediente.toUpperCase() === expediente.trim().toUpperCase()),
    [pacientes, expediente],
  )
  const noEncontrado = expediente.trim() !== '' && pacientes.length > 0 && !paciente

  const set = <K extends keyof typeof datos>(k: K, v: (typeof datos)[K]) => setDatos((d) => ({ ...d, [k]: v }))

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (!paciente) {
      setError(new Error('Selecciona un expediente válido'))
      return
    }
    setGuardando(true)
    setError(null)
    try {
      const payload: AtencionIn = {
        ...datos,
        paciente_id: paciente.id,
        nota_clinica: datos.nota_clinica?.trim() || null,
        plan_manejo: datos.plan_manejo?.trim() || null,
        fecha: datos.fecha || null,
      }
      onGuardado(await api.guardarAtencion(payload, atencion?.id))
    } catch (err) {
      setError(err)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <form onSubmit={enviar} className="formulario">
      <div className="rejilla">
        <Campo etiqueta="Expediente del paciente *">
          <input
            required
            list="lista-expedientes"
            value={expediente}
            onChange={(e) => setExpediente(e.target.value)}
            placeholder="EXP-0000"
            className={noEncontrado ? 'invalido' : ''}
            disabled={!!pacienteId && !atencion}
            autoFocus={!pacienteId}
          />
          <datalist id="lista-expedientes">
            {pacientes.map((p) => (
              <option key={p.id} value={p.expediente}>
                {p.nombre}
              </option>
            ))}
          </datalist>
        </Campo>
        <Campo etiqueta="Fecha">
          <input type="date" max={hoyISO()} value={datos.fecha ?? ''} onChange={(e) => set('fecha', e.target.value)} />
        </Campo>

        <div className={`ficha-auto campo-completo ${noEncontrado ? 'ficha-error' : ''}`}>
          {paciente ? (
            <>
              <div>
                <span className="campo-etiqueta">Paciente</span>
                <strong>{paciente.nombre}</strong>
              </div>
              <div>
                <span className="campo-etiqueta">Servicio</span>
                {paciente.servicio ?? '—'}
              </div>
              <div>
                <span className="campo-etiqueta">Médico tratante</span>
                {paciente.medico_tratante ?? '—'}
              </div>
              <div>
                <span className="campo-etiqueta">Riesgo actual</span>
                <RiesgoBadge {...paciente.riesgo} eventos={paciente.riesgo.eventos_criticos} />
              </div>
            </>
          ) : noEncontrado ? (
            <span>NO ENCONTRADO — el expediente no existe en el censo de pacientes.</span>
          ) : (
            <span className="tenue">Indica el expediente: nombre, servicio y médico tratante se completan solos.</span>
          )}
        </div>

        <Campo etiqueta="Tipo de atención *">
          <select required value={datos.tipo_atencion_id || ''} onChange={(e) => set('tipo_atencion_id', Number(e.target.value))}>
            <option value="">Selecciona…</option>
            {tipos.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nombre}
              </option>
            ))}
          </select>
        </Campo>
        <Campo etiqueta="Médico que atiende *">
          <select required value={datos.medico_id || ''} onChange={(e) => set('medico_id', Number(e.target.value))}>
            <option value="">Selecciona…</option>
            {medicos
              .filter((m) => m.activo || m.id === datos.medico_id)
              .map((m) => (
                <option key={m.id} value={m.id}>
                  {m.id} · {m.nombre}
                </option>
              ))}
          </select>
        </Campo>
        <Campo etiqueta="Turno *">
          <select required value={datos.turno} onChange={(e) => set('turno', e.target.value)}>
            <option value="">Selecciona…</option>
            {config?.turnos.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </Campo>
        <Campo etiqueta="Triage *">
          <select required value={datos.triage} onChange={(e) => set('triage', e.target.value)}>
            <option value="">Selecciona…</option>
            {config?.triage.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </Campo>
        <Campo etiqueta="Nota clínica / hallazgos" ancho="completo">
          <textarea rows={3} value={datos.nota_clinica ?? ''} onChange={(e) => set('nota_clinica', e.target.value)} />
        </Campo>
        <Campo etiqueta="Plan de manejo" ancho="completo">
          <textarea rows={2} value={datos.plan_manejo ?? ''} onChange={(e) => set('plan_manejo', e.target.value)} />
        </Campo>
        <label className={`check-critico campo-completo ${datos.evento_critico ? 'activo' : ''}`}>
          <input
            type="checkbox"
            checked={datos.evento_critico}
            onChange={(e) => set('evento_critico', e.target.checked)}
          />
          <span>
            <strong>Evento crítico</strong>
            <small>
              Márcalo solo si la atención constituye un evento crítico (descompensación, reingreso, transfusión de
              urgencia, complicación…). Incrementa el nivel de riesgo acumulado del paciente.
            </small>
          </span>
        </label>
      </div>
      <ErrorMsg error={error} />
      <footer className="acciones">
        <button type="button" className="btn" onClick={onCancelar}>
          Cancelar
        </button>
        <button type="submit" className="btn btn-primario" disabled={guardando || noEncontrado}>
          {guardando ? 'Guardando…' : atencion ? 'Guardar cambios' : 'Registrar atención'}
        </button>
      </footer>
    </form>
  )
}
