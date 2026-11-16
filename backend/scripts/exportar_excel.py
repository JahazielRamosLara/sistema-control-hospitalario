"""Exporta los datos de ejemplo del libro Excel original a app/seed_data.json.

Uso: python scripts/exportar_excel.py "ruta/Sistema de control hospitalario v1.xlsm"
"""
import json
import sys
import warnings
from datetime import date, datetime
from pathlib import Path

import openpyxl

warnings.filterwarnings("ignore")


def filas(ws):
    rows = ws.iter_rows(values_only=True)
    encabezado = next(rows)
    for r in rows:
        if r and r[0] not in (None, ""):
            yield dict(zip(encabezado, r))


def fecha(v):
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    return v


def main(ruta: str):
    wb = openpyxl.load_workbook(ruta, data_only=True)
    datos = {
        "servicios": [
            {"nombre": r["SERVICIO"], "ubicacion": r["UBICACION"], "camas_censables": r["CAMAS CENSABLES"] or 0,
             "jefe": r["JEFE DE SERVICIO"]}
            for r in filas(wb["BASE_SERVICIOS"])
        ],
        "medicos": [
            {"id": r["ID"], "nombre": r["MEDICO"], "especialidad": r["ESPECIALIDAD"],
             "cedula_profesional": str(r["CEDULA PROFESIONAL"]), "turno": r["TURNO"]}
            for r in filas(wb["BASE_MEDICOS"])
        ],
        "tipos_atencion": [
            {"nombre": r["TIPO DE ATENCION"], "categoria": r["CATEGORIA"]}
            for r in filas(wb["BASE_ATENCIONES"])
        ],
        "riesgo": [
            {"eventos_minimos": r["EVENTOS_CRITICOS"], "nivel": r["NIVEL_RIESGO"], "semaforo": r["SEMAFORO"],
             "accion": r["ACCION_REQUERIDA"]}
            for r in filas(wb["TABLA_RIESGO"]) if isinstance(r["EVENTOS_CRITICOS"], int)
        ],
        "pacientes": [
            {"expediente": r["ID"], "nombre": r["PACIENTE"], "servicio": r["SERVICIO"],
             "medico_tratante": r["MEDICO TRATANTE"], "fecha_nacimiento": fecha(r["FECHA NACIMIENTO"]),
             "sexo": r["SEXO"], "tipo_sangre": r["TIPO DE SANGRE"], "alergias": r["ALERGIAS"],
             "contacto_emergencia": r["CONTACTO DE EMERGENCIA"], "telefono": r["TELEFONO"]}
            for r in filas(wb["BASE_PACIENTES"])
        ],
        "atenciones": [
            {"expediente": r["ID PACIENTE"], "tipo_atencion": r["TIPO DE ATENCION"], "medico_id": r["ID MEDICO"],
             "turno": r["TURNO"], "triage": r["TRIAGE"], "nota_clinica": r["NOTA CLINICA / HALLAZGOS"],
             "plan_manejo": r["PLAN DE MANEJO"], "fecha": fecha(r["FECHA"]),
             "evento_critico": r["EVENTO CRITICO"] == "SI"}
            for r in filas(wb["SEGUIMIENTO_CLINICO"]) if r.get("ID PACIENTE")
        ],
    }
    destino = Path(__file__).resolve().parent.parent / "app" / "seed_data.json"
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print({k: len(v) for k, v in datos.items()}, "->", destino)


if __name__ == "__main__":
    main(sys.argv[1])
