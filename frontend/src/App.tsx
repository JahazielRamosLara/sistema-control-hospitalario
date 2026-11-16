import { useState, type FormEvent } from 'react'
import { NavLink, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { api } from './api'
import { useCatalogos } from './catalogos'
import { ErrorMsg } from './components/ui'
import { Catalogos } from './pages/Catalogos'
import { PacienteDetalle } from './pages/PacienteDetalle'
import { Pacientes } from './pages/Pacientes'
import { Seguimiento } from './pages/Seguimiento'
import { TablaRiesgo } from './pages/TablaRiesgo'
import { Tablero } from './pages/Tablero'

const NAV = [
  { to: '/', etiqueta: 'Menú' },
  { to: '/pacientes', etiqueta: 'Pacientes' },
  { to: '/seguimiento', etiqueta: 'Seguimiento' },
  { to: '/catalogos', etiqueta: 'Catálogos' },
  { to: '/riesgo', etiqueta: 'Tabla de riesgo' },
]

function BuscadorExpediente() {
  const [exp, setExp] = useState('')
  const [error, setError] = useState('')
  const navegar = useNavigate()

  async function buscar(e: FormEvent) {
    e.preventDefault()
    const valor = exp.trim()
    if (!valor) return
    try {
      const p = await api.pacientePorExpediente(valor)
      setExp('')
      setError('')
      navegar(`/pacientes/${p.id}`)
    } catch {
      setError(`${valor.toUpperCase()} no existe`)
      navegar(`/pacientes?q=${encodeURIComponent(valor)}`)
    }
  }

  return (
    <form className="buscador" onSubmit={buscar} role="search">
      <label htmlFor="buscar-exp">Exp.</label>
      <input
        id="buscar-exp"
        value={exp}
        onChange={(e) => {
          setExp(e.target.value)
          setError('')
        }}
        placeholder="EXP-0001"
        aria-label="Buscar paciente por expediente"
      />
      {error && <span className="buscador-error">{error}</span>}
    </form>
  )
}

export default function App() {
  const { error } = useCatalogos()

  return (
    <div className="app">
      <header className="cabecera">
        <div className="cabecera-fila">
          <div className="marca">
            <span className="marca-cruz" aria-hidden />
            <span>
              <strong>Control Hospitalario</strong>
              <small>Seguimiento clínico y riesgo del paciente</small>
            </span>
          </div>
          <BuscadorExpediente />
        </div>
        <nav className="navegacion">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === '/'}>
              {n.etiqueta}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="contenido">
        {!!error && (
          <ErrorMsg error={new Error(`No se pudo conectar con la API: ${(error as Error).message}. ¿Está corriendo el backend?`)} />
        )}
        <Routes>
          <Route path="/" element={<Tablero />} />
          <Route path="/pacientes" element={<Pacientes />} />
          <Route path="/pacientes/:id" element={<PacienteDetalle />} />
          <Route path="/seguimiento" element={<Seguimiento />} />
          <Route path="/catalogos" element={<Catalogos />} />
          <Route path="/riesgo" element={<TablaRiesgo />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      <footer className="pie">
        v1.0 · Datos de ejemplo ficticios · No sustituye al expediente clínico institucional (NOM-004-SSA3-2012)
      </footer>
    </div>
  )
}
