"""Las pruebas usan TEST_DATABASE_URL si está definida (p. ej. un Postgres de pruebas);
en su defecto, SQLite en memoria para poder ejecutarse sin servidor."""
import os

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import database, seguridad  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Usuario  # noqa: E402
from app.seed import cargar  # noqa: E402

PASSWORD = "Clave-de-prueba-2026"
ROLES = ("admin", "jefatura", "medico", "admision")
CSRF = {"X-Requested-With": "fetch"}


@pytest.fixture()
def Session():
    url = os.environ["DATABASE_URL"]
    kwargs = {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    engine = create_engine(url, **kwargs)
    database.engine = engine
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    hash_ = seguridad.hash_password(PASSWORD)
    with Session() as db:
        cargar(db)
        for rol in ROLES:
            db.add(Usuario(usuario=rol, nombre=f"Usuario {rol}", rol=rol, password_hash=hash_,
                           debe_cambiar_password=False))
        db.commit()
    seguridad.reiniciar_limites()

    def _db():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = _db
    yield Session
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def anonimo(Session):
    with TestClient(app, headers=CSRF) as c:
        yield c


def entrar(c: TestClient, usuario: str, password: str = PASSWORD):
    return c.post("/api/auth/login", json={"usuario": usuario, "password": password})


@pytest.fixture()
def client(anonimo):
    """Cliente con sesión de administrador."""
    assert entrar(anonimo, "admin").status_code == 200
    return anonimo


@pytest.fixture()
def como(Session):
    """Fábrica: como('medico') devuelve un cliente nuevo con sesión de ese rol."""
    abiertos = []

    def _como(rol: str) -> TestClient:
        c = TestClient(app, headers=CSRF)
        c.__enter__()
        abiertos.append(c)
        assert entrar(c, rol).status_code == 200
        return c

    yield _como
    for c in abiertos:
        c.__exit__(None, None, None)
