import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.tsx'
import { AuthProvider, useAuth } from './auth.tsx'
import { CatalogosProvider } from './catalogos.tsx'
import { Cargando } from './components/ui.tsx'
import { CambiarPassword, Login } from './pages/Login.tsx'
import './index.css'

/** Sin sesión → login; con contraseña temporal → cambio obligatorio; si no, la aplicación. */
function Puerta() {
  const { usuario, cargando } = useAuth()
  if (cargando) return <Cargando />
  if (!usuario) return <Login />
  if (usuario.debe_cambiar_password) return <CambiarPassword obligatorio />
  return (
    <CatalogosProvider key={usuario.id}>
      <App />
    </CatalogosProvider>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Puerta />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
