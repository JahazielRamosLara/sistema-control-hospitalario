from datetime import timedelta

from fastapi.testclient import TestClient

from app import seguridad
from app.config import settings
from app.main import app
from app.models import Sesion, Usuario

from .conftest import PASSWORD, entrar


def test_sin_sesion_no_hay_datos(anonimo):
    for url in ("/api/pacientes", "/api/indicadores", "/api/atenciones", "/api/medicos", "/api/usuarios",
                "/api/pacientes/1/expediente.pdf"):
        assert anonimo.get(url).status_code == 401, url
    assert anonimo.get("/api/salud").status_code == 200


def test_login_correcto_pone_cookie_segura(anonimo):
    r = entrar(anonimo, "medico")
    assert r.status_code == 200
    assert r.json()["rol"] == "medico"
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/api" in cookie
    assert "password" not in r.text.lower() or "debe_cambiar_password" in r.text
    assert anonimo.get("/api/auth/me").json()["usuario"] == "medico"


def test_mismo_mensaje_para_usuario_inexistente(anonimo):
    a = entrar(anonimo, "admin", "incorrecta-123")
    b = entrar(anonimo, "no-existe", "incorrecta-123")
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_bloqueo_tras_intentos_fallidos(anonimo):
    for _ in range(settings.max_intentos_login):
        assert entrar(anonimo, "jefatura", "mal-mal-123").status_code == 401
    # Aun con la contraseña correcta, la cuenta está bloqueada
    assert entrar(anonimo, "jefatura").status_code == 401


def test_limite_por_ip(anonimo, monkeypatch):
    monkeypatch.setattr(settings, "max_intentos_por_ip", 3)
    for i in range(3):
        entrar(anonimo, f"x{i}", "mal-mal-123")
    assert entrar(anonimo, "admin").status_code == 429


def test_logout_invalida_la_sesion(client, Session):
    token = client.cookies.get(seguridad.COOKIE)
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/pacientes").status_code == 401
    # Reusar el token robado tampoco funciona: ya no existe en la base
    with TestClient(app, headers={"X-Requested-With": "fetch"}) as otro:
        otro.cookies.set(seguridad.COOKIE, token, path="/api")
        assert otro.get("/api/pacientes").status_code == 401


def test_token_no_se_guarda_en_claro(client, Session):
    token = client.cookies.get(seguridad.COOKIE)
    with Session() as db:
        hashes = [s.token_hash for s in db.query(Sesion)]
    assert token not in hashes and len(hashes) == 1 and len(hashes[0]) == 64


def test_sesion_inactiva_expira(client, Session):
    with Session() as db:
        s = db.query(Sesion).one()
        s.ultimo_uso = seguridad.ahora() - timedelta(minutes=settings.sesion_inactividad_min + 1)
        db.commit()
    r = client.get("/api/pacientes")
    assert r.status_code == 401 and "expiró" in r.json()["detail"]


def test_csrf_sin_cabecera_rechazado(client):
    r = client.post("/api/auth/logout", headers={"X-Requested-With": ""})
    assert r.status_code == 403
    r = client.post("/api/pacientes", json={"nombre": "Ataque Csrf"}, headers={"X-Requested-With": ""})
    assert r.status_code == 403


def test_permisos_por_rol(como):
    medico, admision, jefatura = como("medico"), como("admision"), como("jefatura")
    atencion = {"paciente_id": 1, "tipo_atencion_id": 1, "medico_id": 1, "turno": "Matutino",
                "triage": "V - Azul (No urgente)"}
    # Todos pueden consultar
    for c in (medico, admision, jefatura):
        assert c.get("/api/indicadores").status_code == 200
        assert c.get("/api/pacientes/2/expediente.pdf").status_code == 200
    # Médico registra atenciones, pero no da de alta pacientes ni toca catálogos
    assert medico.post("/api/atenciones", json=atencion).status_code == 201
    assert medico.post("/api/pacientes", json={"nombre": "Paciente Ficticio"}).status_code == 403
    assert medico.put("/api/riesgo", json=[]).status_code == 403
    # Admisión da de alta pacientes, pero no registra atenciones
    assert admision.post("/api/pacientes", json={"nombre": "Paciente Ficticio"}).status_code == 201
    assert admision.post("/api/atenciones", json=atencion).status_code == 403
    # Jefatura solo consulta
    assert jefatura.post("/api/atenciones", json=atencion).status_code == 403
    assert jefatura.delete("/api/pacientes/1").status_code == 403
    # Nadie salvo admin administra usuarios
    for c in (medico, admision, jefatura):
        assert c.get("/api/usuarios").status_code == 403


def test_alta_usuario_y_primer_ingreso(client, anonimo):
    r = client.post("/api/usuarios", json={"usuario": "Enf.Lopez", "nombre": "Enf. María López", "rol": "medico"})
    assert r.status_code == 201
    temporal = r.json()["password_temporal"]
    assert r.json()["usuario"]["usuario"] == "enf.lopez"

    with TestClient(app, headers={"X-Requested-With": "fetch"}) as nuevo:
        assert entrar(nuevo, "enf.lopez", temporal).json()["debe_cambiar_password"] is True
        # Mientras no cambie la contraseña no puede ver datos
        assert nuevo.get("/api/pacientes").status_code == 403
        # Política de contraseñas
        assert nuevo.post("/api/auth/cambiar-password", json={"actual": temporal, "nueva": "corta1"}).status_code == 422
        assert nuevo.post("/api/auth/cambiar-password",
                          json={"actual": temporal, "nueva": "enf.lopez12345"}).status_code == 422
        r = nuevo.post("/api/auth/cambiar-password", json={"actual": temporal, "nueva": "Guardia-Nocturna-77"})
        assert r.status_code == 200 and r.json()["debe_cambiar_password"] is False
        assert nuevo.get("/api/pacientes").status_code == 200


def test_restablecer_password_cierra_sesiones(client, como, Session):
    medico = como("medico")
    with Session() as db:
        uid = db.query(Usuario).filter_by(usuario="medico").one().id
    r = client.post(f"/api/usuarios/{uid}/restablecer-password")
    assert r.status_code == 200
    assert medico.get("/api/pacientes").status_code == 401  # su sesión fue revocada
    with TestClient(app, headers={"X-Requested-With": "fetch"}) as c:
        assert entrar(c, "medico", PASSWORD).status_code == 401
        assert entrar(c, "medico", r.json()["password_temporal"]).status_code == 200


def test_desactivar_usuario_revoca_sesion(client, como, Session):
    jef = como("jefatura")
    with Session() as db:
        uid = db.query(Usuario).filter_by(usuario="jefatura").one().id
    client.put(f"/api/usuarios/{uid}", json={"nombre": "Usuario jefatura", "rol": "jefatura", "activo": False})
    assert jef.get("/api/pacientes").status_code == 401
    assert entrar(jef, "jefatura").status_code == 401


def test_admin_no_puede_quitarse_admin(client):
    yo = client.get("/api/auth/me").json()
    r = client.put(f"/api/usuarios/{yo['id']}", json={"nombre": "x admin", "rol": "medico", "activo": True})
    assert r.status_code == 409


def test_bitacora_de_accesos(client, anonimo):
    entrar(anonimo, "admin", "mal-mal-123")
    eventos = client.get("/api/usuarios/accesos").json()
    tipos = {(e["usuario"], e["evento"], e["exito"]) for e in eventos}
    assert ("admin", "login", True) in tipos
    assert ("admin", "login_fallido", False) in tipos


def test_password_hash_es_argon2(Session):
    with Session() as db:
        h = db.query(Usuario).first().password_hash
    assert h.startswith("$argon2id$")
