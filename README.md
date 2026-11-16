# Sistema de Control Hospitalario — Web

Versión web del libro *Sistema de control hospitalario v1.xlsm* (ver `Documentacion_Sistema_Control_Hospitalario`).
Registro de atenciones clínicas, estratificación automática de riesgo por eventos críticos acumulados y expediente en PDF.

| Capa | Tecnología |
|---|---|
| Backend | FastAPI · SQLAlchemy 2 · psycopg 3 · ReportLab (PDF) |
| Base de datos | PostgreSQL 16 |
| Frontend | React 19 + TypeScript · Vite (npm) · React Router |

## Equivalencia con el libro Excel

| Hoja Excel | Web |
|---|---|
| MENU | **Menú principal** (`/`): 6 indicadores, distribución por riesgo, pacientes prioritarios |
| BASE_PACIENTES + BUSCAR_PACIENTE | **Pacientes** (`/pacientes`) y buscador de expediente en la barra superior |
| EXPEDIENTE_PACIENTE | Detalle del paciente (`/pacientes/:id`) + **Generar expediente PDF** |
| SEGUIMIENTO_CLINICO | **Seguimiento clínico** (`/seguimiento`): bitácora con filtros y paginación |
| BASE_MEDICOS / BASE_SERVICIOS / BASE_ATENCIONES | **Catálogos** (`/catalogos`) |
| TABLA_RIESGO | **Tabla de riesgo** (`/riesgo`), editable; el cambio se propaga a todos los pacientes |
| CONFIG | `GET /api/config` (turnos, triage, sexo, tipos de sangre, estados) |

Reglas conservadas: expediente consecutivo `EXP-0000`, autocompletado de nombre/servicio/médico tratante al indicar
el expediente, sello automático de fecha, aviso si el expediente no existe, conteo histórico de eventos críticos
y nivel = último umbral que no supera el conteo. El umbral «riesgo alto» ya no está fijo en 5: cada nivel de la tabla
tiene una casilla **Alerta** que decide si cuenta en el indicador del menú.

## Opción A — Todo con Docker (cualquier equipo)

Requiere Docker Desktop y git (el repositorio es privado: inicia sesión con `gh auth login` o usa tus credenciales de GitHub).

```powershell
git clone https://github.com/JahazielRamosLara/sistema-control-hospitalario.git
cd sistema-control-hospitalario
docker compose up -d --build
```

Para actualizar después: `git pull` y `docker compose up -d --build`.

**Primer acceso:** al arrancar por primera vez se crea el usuario `admin` con una contraseña temporal aleatoria.
Consúltala con `docker compose logs backend` (busca «Usuario administrador creado»); el sistema pedirá cambiarla al
entrar. Para fijarla tú, define `ADMIN_PASSWORD` en el `.env` de la raíz **antes** del primer arranque. Desde
**Usuarios** el administrador da de alta al resto del personal.

| Servicio | URL / puerto |
|---|---|
| Aplicación web | <http://localhost:8080> |
| API + documentación | <http://localhost:8000/docs> (solo desde este equipo) |
| PostgreSQL | `localhost:5433` · usuario `hospital` · contraseña `hospital` · base `control_hospitalario` |

Al primer arranque se crean las tablas y se cargan los datos de ejemplo (si la base está vacía).
Los datos persisten en el volumen `control-hospitalario_pgdata`. Para personalizar puertos o contraseñas,
copia `.env.example` a `.env` en la raíz. Para desactivar los datos de ejemplo: `SEED_DATOS_EJEMPLO=0`.

```powershell
docker compose logs -f backend     # ver logs
docker compose down                # detener (conserva los datos)
docker compose down -v             # detener y BORRAR la base
```

## Opción B — Desarrollo con recarga en caliente

Postgres en Docker; backend y frontend en local.

```powershell
docker compose up -d db

cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
copy .env.example .env                    # ya apunta a localhost:5433
.venv\Scripts\python -m app.seed          # crea tablas y carga datos de ejemplo
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000

cd ..\frontend
npm install
npm run dev                               # http://localhost:5173 (proxy /api → :8000)
```

(Si usas la opción A al mismo tiempo, detén el contenedor `backend` para liberar el puerto 8000.)

## Pruebas

```powershell
cd backend
.venv\Scripts\python -m pytest -q
# contra Postgres (base aparte; se borra y recrea):
docker compose exec db createdb -U hospital control_hospitalario_test
$env:TEST_DATABASE_URL="postgresql+psycopg://hospital:hospital@localhost:5433/control_hospitalario_test"
.venv\Scripts\python -m pytest -q
```

Por defecto usan SQLite en memoria; para probar contra Postgres define `TEST_DATABASE_URL`
(se borra y recrea esa base, no uses la de trabajo).
Las pruebas verifican, entre otras cosas, que los indicadores coinciden con el MENU del Excel
(31 pacientes, 70 atenciones, 25 eventos críticos, 3 en riesgo alto, 12 médicos, 230 camas).

## Datos de ejemplo

`backend/app/seed_data.json` se generó desde el .xlsm con
`python scripts/exportar_excel.py "D:\OneDrive\Sistema de control hospitalario v1.xlsm"`.
Son datos **ficticios**; `python -m app.seed --reset` borra todo y los vuelve a cargar.

## Seguridad

| Aspecto | Implementación |
|---|---|
| Contraseñas | Argon2id; mínimo 10 caracteres con letras y números, distinta del usuario. Las cuentas nuevas y restablecidas reciben una contraseña temporal que debe cambiarse al entrar. |
| Sesiones | Token aleatorio de 256 bits en cookie `HttpOnly`, `SameSite=Strict`, ruta `/api` (inaccesible para JavaScript). En la base solo se guarda su SHA-256. Expiran tras 30 min de inactividad o 12 h, y se revocan al salir, cambiar o restablecer la contraseña o desactivar la cuenta. |
| Fuerza bruta | Bloqueo de la cuenta 15 min tras 5 fallos; límite de intentos por IP; el mensaje de error no revela si el usuario existe. |
| CSRF | Toda petición que modifica datos exige la cabecera `X-Requested-With: fetch`, más la cookie `SameSite=Strict`. |
| Permisos | Por perfil, aplicados en el backend: **admin** (todo, usuarios, catálogos, escala de riesgo, eliminar), **admisión** (alta y edición de pacientes), **médico/enfermería** (registrar y editar atenciones), **jefatura** (consulta y PDF). Todos los perfiles pueden consultar. |
| Auditoría | Bitácora de accesos (inicios correctos y fallidos, bloqueos, cambios de contraseña) en **Usuarios → Bitácora de accesos**. |
| Red | Postgres y la API solo escuchan en `127.0.0.1`; desde fuera solo se expone nginx (:8080), con cabeceras CSP, `X-Frame-Options`, `nosniff`. Las respuestas de la API no se guardan en caché. |

Si la app se publica fuera de la red local, sírvela por **HTTPS** (p. ej. un proxy con certificado delante de nginx)
y define `COOKIE_SECURE=true`. Cambia también `POSTGRES_PASSWORD`.

## Limitaciones (heredadas del documento, §13)

La auditoría cubre los accesos pero aún no registra quién modificó cada registro clínico, y la escala de riesgo es
acumulativa y sin ventana temporal. No es un expediente clínico electrónico certificado (NOM-024-SSA3-2012); con datos reales
aplican NOM-004-SSA3-2012 y la legislación de protección de datos personales sensibles.
