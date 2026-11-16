from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/control_hospitalario"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    nombre_hospital: str = "Sistema de Control Hospitalario"

    # --- Seguridad ---
    # Poner en true cuando la app se sirva por HTTPS (la cookie solo viajará cifrada).
    cookie_secure: bool = False
    sesion_horas: int = 12  # duración máxima de una sesión
    sesion_inactividad_min: int = 30  # cierre por inactividad
    max_intentos_login: int = 5  # intentos fallidos antes de bloquear la cuenta
    bloqueo_min: int = 15
    max_intentos_por_ip: int = 30  # por ventana de bloqueo_min, para frenar fuerza bruta distribuida
    # Administrador inicial: se crea solo si no existe ningún usuario.
    admin_usuario: str = "admin"
    admin_password: str | None = None  # si se omite, se genera una aleatoria y se muestra en el log


settings = Settings()
