import { useState, type FormEvent } from 'react'
import { api, type Medico, type Servicio, type TipoAtencion } from '../api'
import { useCatalogos } from '../catalogos'
import { Campo, ErrorMsg, Modal } from '../components/ui'

type Pestana = 'medicos' | 'servicios' | 'tipos'

export function Catalogos() {
  const [pestana, setPestana] = useState<Pestana>('medicos')
  return (
    <>
      <header className="pagina-header">
        <div>
          <h1>Catálogos</h1>
          <p className="subtitulo">Fuente de verdad de las listas desplegables y búsquedas automáticas</p>
        </div>
      </header>
      <div className="pestanas" role="tablist">
        {(
          [
            ['medicos', 'Médicos'],
            ['servicios', 'Servicios'],
            ['tipos', 'Tipos de atención'],
          ] as const
        ).map(([k, t]) => (
          <button key={k} role="tab" aria-selected={pestana === k} className={pestana === k ? 'activa' : ''} onClick={() => setPestana(k)}>
            {t}
          </button>
        ))}
      </div>
      {pestana === 'medicos' && <Medicos />}
      {pestana === 'servicios' && <Servicios />}
      {pestana === 'tipos' && <Tipos />}
    </>
  )
}

function useEdicion<T>() {
  const [editando, setEditando] = useState<T | 'nuevo' | null>(null)
  const [error, setError] = useState<unknown>(null)
  return { editando, setEditando, error, setError }
}

function Medicos() {
  const { medicos, config, recargar } = useCatalogos()
  const { editando, setEditando, error, setError } = useEdicion<Medico>()

  async function eliminar(m: Medico) {
    if (!confirm(`¿Eliminar a ${m.nombre}?`)) return
    try {
      await api.eliminarMedico(m.id)
      await recargar()
      setError(null)
    } catch (e) {
      setError(e)
    }
  }

  return (
    <section className="tarjeta sin-relleno">
      <div className="barra-tabla">
        <span>{medicos.length} médicos</span>
        <button className="btn btn-primario" onClick={() => setEditando('nuevo')}>Agregar médico</button>
      </div>
      <ErrorMsg error={error} />
      <div className="tabla-scroll">
        <table className="tabla">
          <thead>
            <tr><th className="num">ID</th><th>Médico</th><th>Especialidad</th><th>Cédula profesional</th><th>Turno</th><th>Estado</th><th /></tr>
          </thead>
          <tbody>
            {medicos.map((m) => (
              <tr key={m.id} className={m.activo ? '' : 'inactivo'}>
                <td className="num mono">{m.id}</td>
                <td>{m.nombre}</td>
                <td>{m.especialidad}</td>
                <td className="mono">{m.cedula_profesional}</td>
                <td>{m.turno}</td>
                <td>{m.activo ? 'Activo' : 'Inactivo'}</td>
                <td className="nowrap">
                  <button className="btn-texto" onClick={() => setEditando(m)}>Editar</button>
                  <button className="btn-texto peligro" onClick={() => eliminar(m)}>Eliminar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal titulo={editando === 'nuevo' ? 'Nuevo médico' : 'Editar médico'} abierto={editando !== null} onCerrar={() => setEditando(null)}>
        <FormMedico
          medico={editando && editando !== 'nuevo' ? editando : undefined}
          turnos={config?.turnos ?? []}
          onListo={async () => {
            setEditando(null)
            await recargar()
          }}
          onCancelar={() => setEditando(null)}
        />
      </Modal>
    </section>
  )
}

function FormMedico({ medico, turnos, onListo, onCancelar }: { medico?: Medico; turnos: string[]; onListo: () => void; onCancelar: () => void }) {
  const [d, setD] = useState<Omit<Medico, 'id'>>({
    nombre: medico?.nombre ?? '',
    especialidad: medico?.especialidad ?? '',
    cedula_profesional: medico?.cedula_profesional ?? '',
    turno: medico?.turno ?? null,
    activo: medico?.activo ?? true,
  })
  const [error, setError] = useState<unknown>(null)
  async function enviar(e: FormEvent) {
    e.preventDefault()
    try {
      await api.guardarMedico({ ...d, especialidad: d.especialidad || null, cedula_profesional: d.cedula_profesional || null }, medico?.id)
      onListo()
    } catch (err) {
      setError(err)
    }
  }
  return (
    <form onSubmit={enviar} className="formulario">
      <div className="rejilla">
        <Campo etiqueta="Nombre *" ancho="completo">
          <input required minLength={3} autoFocus value={d.nombre} onChange={(e) => setD({ ...d, nombre: e.target.value })} placeholder="Dr./Dra. Nombre Apellidos" />
        </Campo>
        <Campo etiqueta="Especialidad">
          <input value={d.especialidad ?? ''} onChange={(e) => setD({ ...d, especialidad: e.target.value })} />
        </Campo>
        <Campo etiqueta="Cédula profesional">
          <input inputMode="numeric" value={d.cedula_profesional ?? ''} onChange={(e) => setD({ ...d, cedula_profesional: e.target.value })} />
        </Campo>
        <Campo etiqueta="Turno">
          <select value={d.turno ?? ''} onChange={(e) => setD({ ...d, turno: e.target.value || null })}>
            <option value="">—</option>
            {turnos.map((t) => <option key={t}>{t}</option>)}
          </select>
        </Campo>
        <label className="filtro-check">
          <input type="checkbox" checked={d.activo} onChange={(e) => setD({ ...d, activo: e.target.checked })} /> Activo
        </label>
      </div>
      <ErrorMsg error={error} />
      <footer className="acciones">
        <button type="button" className="btn" onClick={onCancelar}>Cancelar</button>
        <button type="submit" className="btn btn-primario">Guardar</button>
      </footer>
    </form>
  )
}

function Servicios() {
  const { servicios, medicos, recargar } = useCatalogos()
  const { editando, setEditando, error, setError } = useEdicion<Servicio>()
  const totalCamas = servicios.reduce((s, x) => s + x.camas_censables, 0)

  async function eliminar(s: Servicio) {
    if (!confirm(`¿Eliminar el servicio ${s.nombre}?`)) return
    try {
      await api.eliminarServicio(s.id)
      await recargar()
      setError(null)
    } catch (e) {
      setError(e)
    }
  }

  return (
    <section className="tarjeta sin-relleno">
      <div className="barra-tabla">
        <span>{servicios.length} servicios · {totalCamas} camas censables</span>
        <button className="btn btn-primario" onClick={() => setEditando('nuevo')}>Agregar servicio</button>
      </div>
      <ErrorMsg error={error} />
      <div className="tabla-scroll">
        <table className="tabla">
          <thead>
            <tr><th className="num">ID</th><th>Servicio</th><th>Ubicación</th><th className="num">Camas censables</th><th>Jefe de servicio</th><th /></tr>
          </thead>
          <tbody>
            {servicios.map((s) => (
              <tr key={s.id}>
                <td className="num mono">{s.id}</td>
                <td>{s.nombre}</td>
                <td>{s.ubicacion}</td>
                <td className="num">{s.camas_censables}</td>
                <td>{s.jefe_nombre ?? '—'}</td>
                <td className="nowrap">
                  <button className="btn-texto" onClick={() => setEditando(s)}>Editar</button>
                  <button className="btn-texto peligro" onClick={() => eliminar(s)}>Eliminar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal titulo={editando === 'nuevo' ? 'Nuevo servicio' : 'Editar servicio'} abierto={editando !== null} onCerrar={() => setEditando(null)}>
        <FormServicio
          servicio={editando && editando !== 'nuevo' ? editando : undefined}
          medicos={medicos}
          onListo={async () => {
            setEditando(null)
            await recargar()
          }}
          onCancelar={() => setEditando(null)}
        />
      </Modal>
    </section>
  )
}

function FormServicio({ servicio, medicos, onListo, onCancelar }: { servicio?: Servicio; medicos: Medico[]; onListo: () => void; onCancelar: () => void }) {
  const [d, setD] = useState({
    nombre: servicio?.nombre ?? '',
    ubicacion: servicio?.ubicacion ?? '',
    camas_censables: servicio?.camas_censables ?? 0,
    jefe_id: servicio?.jefe_id ?? null,
  })
  const [error, setError] = useState<unknown>(null)
  async function enviar(e: FormEvent) {
    e.preventDefault()
    try {
      await api.guardarServicio({ ...d, ubicacion: d.ubicacion || null }, servicio?.id)
      onListo()
    } catch (err) {
      setError(err)
    }
  }
  return (
    <form onSubmit={enviar} className="formulario">
      <div className="rejilla">
        <Campo etiqueta="Nombre del servicio *" ancho="completo">
          <input required minLength={2} autoFocus value={d.nombre} onChange={(e) => setD({ ...d, nombre: e.target.value })} />
        </Campo>
        <Campo etiqueta="Ubicación">
          <input value={d.ubicacion} onChange={(e) => setD({ ...d, ubicacion: e.target.value })} placeholder="Piso 2 - Ala B" />
        </Campo>
        <Campo etiqueta="Camas censables">
          <input type="number" min={0} value={d.camas_censables} onChange={(e) => setD({ ...d, camas_censables: Number(e.target.value) })} />
        </Campo>
        <Campo etiqueta="Jefe de servicio" ancho="completo">
          <select value={d.jefe_id ?? ''} onChange={(e) => setD({ ...d, jefe_id: e.target.value ? Number(e.target.value) : null })}>
            <option value="">— Sin asignar —</option>
            {medicos.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}
          </select>
        </Campo>
      </div>
      <ErrorMsg error={error} />
      <footer className="acciones">
        <button type="button" className="btn" onClick={onCancelar}>Cancelar</button>
        <button type="submit" className="btn btn-primario">Guardar</button>
      </footer>
    </form>
  )
}

function Tipos() {
  const { tipos, recargar } = useCatalogos()
  const { editando, setEditando, error, setError } = useEdicion<TipoAtencion>()

  async function eliminar(t: TipoAtencion) {
    if (!confirm(`¿Eliminar el tipo de atención "${t.nombre}"?`)) return
    try {
      await api.eliminarTipo(t.id)
      await recargar()
      setError(null)
    } catch (e) {
      setError(e)
    }
  }

  return (
    <section className="tarjeta sin-relleno">
      <div className="barra-tabla">
        <span>{tipos.length} tipos de atención</span>
        <button className="btn btn-primario" onClick={() => setEditando('nuevo')}>Agregar tipo</button>
      </div>
      <ErrorMsg error={error} />
      <div className="tabla-scroll">
        <table className="tabla">
          <thead><tr><th className="num">ID</th><th>Tipo de atención</th><th>Categoría</th><th /></tr></thead>
          <tbody>
            {tipos.map((t) => (
              <tr key={t.id}>
                <td className="num mono">{t.id}</td>
                <td>{t.nombre}</td>
                <td>{t.categoria}</td>
                <td className="nowrap">
                  <button className="btn-texto" onClick={() => setEditando(t)}>Editar</button>
                  <button className="btn-texto peligro" onClick={() => eliminar(t)}>Eliminar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal titulo={editando === 'nuevo' ? 'Nuevo tipo de atención' : 'Editar tipo de atención'} abierto={editando !== null} onCerrar={() => setEditando(null)} ancho={480}>
        <FormTipo
          tipo={editando && editando !== 'nuevo' ? editando : undefined}
          categorias={[...new Set(tipos.map((t) => t.categoria).filter(Boolean) as string[])]}
          onListo={async () => {
            setEditando(null)
            await recargar()
          }}
          onCancelar={() => setEditando(null)}
        />
      </Modal>
    </section>
  )
}

function FormTipo({ tipo, categorias, onListo, onCancelar }: { tipo?: TipoAtencion; categorias: string[]; onListo: () => void; onCancelar: () => void }) {
  const [d, setD] = useState({ nombre: tipo?.nombre ?? '', categoria: tipo?.categoria ?? '' })
  const [error, setError] = useState<unknown>(null)
  async function enviar(e: FormEvent) {
    e.preventDefault()
    try {
      await api.guardarTipo({ nombre: d.nombre, categoria: d.categoria || null }, tipo?.id)
      onListo()
    } catch (err) {
      setError(err)
    }
  }
  return (
    <form onSubmit={enviar} className="formulario">
      <div className="rejilla">
        <Campo etiqueta="Tipo de atención *" ancho="completo">
          <input required minLength={2} autoFocus value={d.nombre} onChange={(e) => setD({ ...d, nombre: e.target.value })} />
        </Campo>
        <Campo etiqueta="Categoría" ancho="completo">
          <input list="categorias" value={d.categoria} onChange={(e) => setD({ ...d, categoria: e.target.value })} />
          <datalist id="categorias">{categorias.map((c) => <option key={c} value={c} />)}</datalist>
        </Campo>
      </div>
      <ErrorMsg error={error} />
      <footer className="acciones">
        <button type="button" className="btn" onClick={onCancelar}>Cancelar</button>
        <button type="submit" className="btn btn-primario">Guardar</button>
      </footer>
    </form>
  )
}
