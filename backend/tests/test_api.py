from datetime import date


def test_indicadores_coinciden_con_menu_del_excel(client):
    r = client.get("/api/indicadores").json()
    assert r["pacientes_registrados"] == 31
    assert r["atenciones_registradas"] == 70
    assert r["eventos_criticos"] == 25
    assert r["pacientes_en_alerta"] == 3
    assert r["medicos_activos"] == 12
    assert r["camas_censables"] == 230
    assert sum(n["pacientes"] for n in r["distribucion_riesgo"]) == 31


def test_estratificacion(client):
    from app.models import UmbralRiesgo
    from app.riesgo import clasificar

    umbrales = [UmbralRiesgo(eventos_minimos=m, nivel=n, semaforo="Verde", alerta=False)
                for m, n in [(0, "ESTABLE"), (1, "OBSERVACION"), (3, "RIESGO MODERADO"), (5, "RIESGO ALTO"),
                             (10, "CRITICO")]]
    casos = {0: "ESTABLE", 1: "OBSERVACION", 2: "OBSERVACION", 3: "RIESGO MODERADO", 4: "RIESGO MODERADO",
             5: "RIESGO ALTO", 9: "RIESGO ALTO", 10: "CRITICO", 40: "CRITICO"}
    for eventos, nivel in casos.items():
        assert clasificar(eventos, umbrales).nivel == nivel


def test_busqueda_por_expediente(client):
    r = client.get("/api/pacientes/expediente/exp-0002")
    assert r.status_code == 200
    p = r.json()
    assert p["nombre"] == "Barrera Huerta Jose Manuel"
    assert len(p["atenciones"]) == 8
    assert p["riesgo"]["nivel"] == "RIESGO ALTO"
    assert client.get("/api/pacientes/expediente/EXP-9999").status_code == 404


def test_alta_paciente_genera_consecutivo(client):
    assert client.get("/api/pacientes/siguiente-expediente").json()["expediente"] == "EXP-0032"
    r = client.post("/api/pacientes", json={"nombre": "Prueba Ficticia Uno", "servicio_id": 1,
                                            "medico_tratante_id": 1, "sexo": "F", "fecha_nacimiento": "1990-05-01"})
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["expediente"] == "EXP-0032"
    assert p["servicio"] == "Urgencias"
    assert p["riesgo"]["nivel"] == "ESTABLE"
    assert p["edad"] >= 35


def test_validaciones_paciente(client):
    assert client.post("/api/pacientes", json={"nombre": "Xx Yy", "sexo": "Z"}).status_code == 422
    assert client.post("/api/pacientes", json={"nombre": "Xx Yy", "servicio_id": 999}).status_code == 422


def test_registrar_atencion_recalcula_riesgo(client):
    pid = client.post("/api/pacientes", json={"nombre": "Prueba Ficticia Dos"}).json()["id"]
    base = {"paciente_id": pid, "tipo_atencion_id": 3, "medico_id": 1, "turno": "Nocturno",
            "triage": "I - Rojo (Resucitacion)", "nota_clinica": "x", "evento_critico": True}
    niveles = []
    for _ in range(5):
        r = client.post("/api/atenciones", json=base)
        assert r.status_code == 201, r.text
        niveles.append(r.json()["nivel_riesgo"])
    assert niveles == ["OBSERVACION", "OBSERVACION", "RIESGO MODERADO", "RIESGO MODERADO", "RIESGO ALTO"]
    a = r.json()
    assert a["fecha"] == date.today().isoformat()  # sello automático
    assert a["medico_tratante"] is None
    assert client.get("/api/indicadores").json()["pacientes_en_alerta"] == 4

    # Desmarcar el evento crítico baja el acumulado
    r = client.put(f"/api/atenciones/{a['id']}", json={**base, "evento_critico": False})
    assert r.json()["total_eventos_criticos"] == 4


def test_atencion_con_referencias_invalidas(client):
    base = {"paciente_id": 9999, "tipo_atencion_id": 1, "medico_id": 1, "turno": "Matutino",
            "triage": "V - Azul (No urgente)"}
    assert client.post("/api/atenciones", json=base).status_code == 422
    assert client.post("/api/atenciones", json={**base, "paciente_id": 1, "turno": "Diurno"}).status_code == 422


def test_listado_atenciones_filtros(client):
    r = client.get("/api/atenciones", params={"solo_criticos": True, "limit": 500}).json()
    assert r["total"] == 25
    assert all(a["evento_critico"] for a in r["items"])
    r = client.get("/api/atenciones", params={"paciente_id": 2}).json()
    assert r["total"] == 8


def test_tabla_riesgo_editable(client):
    tabla = client.get("/api/riesgo").json()
    assert [u["eventos_minimos"] for u in tabla] == [0, 1, 3, 5, 10]
    nueva = [{k: u[k] for k in ("eventos_minimos", "nivel", "semaforo", "accion", "alerta")} for u in tabla]
    nueva[2]["alerta"] = True  # RIESGO MODERADO también dispara alerta
    r = client.put("/api/riesgo", json=nueva)
    assert r.status_code == 200
    assert client.get("/api/indicadores").json()["pacientes_en_alerta"] > 3
    nueva[0]["eventos_minimos"] = 2
    assert client.put("/api/riesgo", json=nueva).status_code == 422


def test_no_borrar_medico_con_atenciones(client):
    assert client.delete("/api/medicos/1").status_code == 409
    nuevo = client.post("/api/medicos", json={"nombre": "Dr. Ficticio Prueba", "turno": "Matutino"}).json()
    assert client.delete(f"/api/medicos/{nuevo['id']}").status_code == 204


def test_expediente_pdf(client):
    r = client.get("/api/pacientes/2/expediente.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
