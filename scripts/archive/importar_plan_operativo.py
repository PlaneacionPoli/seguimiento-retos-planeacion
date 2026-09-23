"""Importa la hoja 'BD_Cronograma' de BD_Planeacion.xlsx (el Plan Operativo) como
actividades independientes (sin reto_id) — complementa los Retos/Macroactividades
ya importados desde Base_Completa_Retos_2026.xlsx, que no traía esta información.

Los Reto_ID de este archivo son legacy (de la importación anterior, ya reemplazada)
y no corresponden a los retos actuales, así que se ignoran: todas las filas se crean
como actividades sueltas, agrupadas por Proceso/Subproceso en la UI.

Uso:
    python scripts/importar_plan_operativo.py [ruta_al_excel]
"""
import os
import sys
import json
import unicodedata
from pathlib import Path

import openpyxl
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

EXCEL_PATH = sys.argv[1] if len(sys.argv) > 1 else "BD_Planeacion.xlsx"


def normalizar(texto):
    if not texto:
        return ""
    texto = str(texto).strip().lower()
    texto = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return " ".join(texto.split())


def init_firebase():
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    service_account_file = os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE", "firebase-service-account.json")
    if service_account_json:
        cred = credentials.Certificate(json.loads(service_account_json))
    elif Path(service_account_file).exists():
        cred = credentials.Certificate(service_account_file)
    else:
        raise SystemExit("No se encontró la service account de Firebase (.env)")
    firebase_admin.initialize_app(cred)
    return firestore.client()


def fecha_iso(valor):
    if valor is None:
        return None
    if hasattr(valor, "date"):
        return valor.date().isoformat()
    return str(valor).split(" ")[0].strip() or None


def main():
    if not Path(EXCEL_PATH).exists():
        raise SystemExit(f"No se encontró el archivo: {EXCEL_PATH}")

    db = init_firebase()

    usuarios_por_nombre = {}
    for d in db.collection("usuarios").stream():
        nombre = normalizar(d.to_dict().get("nombre_completo"))
        if nombre:
            usuarios_por_nombre[nombre] = d.id

    def match_usuario(nombre_hoja):
        palabras = set(normalizar(nombre_hoja).split())
        if not palabras:
            return None
        for nombre_completo, uid in usuarios_por_nombre.items():
            if palabras.issubset(set(nombre_completo.split())):
                return uid
        return None

    # Fallback: líder del proceso/subproceso, tomado de los retos ya existentes.
    lider_por_proceso_sub = {}
    lider_por_proceso = {}
    for d in db.collection("retos").stream():
        r = d.to_dict()
        if not r.get("lider_id"):
            continue
        if r.get("proceso"):
            lider_por_proceso.setdefault(r["proceso"], r["lider_id"])
            if r.get("subproceso"):
                lider_por_proceso_sub.setdefault((r["proceso"], r["subproceso"]), r["lider_id"])

    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws = wb["BD_Cronograma"]
    filas = [r for r in ws.iter_rows(values_only=True) if r[0] is not None][1:]

    creadas = 0
    sin_responsable = 0
    for fila in filas:
        (_id, proceso, subproceso, actividad, fecha_inicio, fecha_fin, _trimestre, _anio,
         responsable, _reto_id_legacy, _reto_nombre_legacy, _score, observaciones,
         _fila_origen, _celdas_origen) = fila

        if not actividad:
            continue

        subproceso = subproceso if subproceso and subproceso != "N/A" else None

        responsable_id = match_usuario(responsable)
        if not responsable_id and subproceso:
            responsable_id = lider_por_proceso_sub.get((proceso, subproceso))
        if not responsable_id:
            responsable_id = lider_por_proceso.get(proceso)
        if not responsable_id:
            sin_responsable += 1

        data = {
            "reto_id": None,
            "parent_id": None,
            "es_macroactividad": False,
            "proceso": proceso,
            "subproceso": subproceso,
            "nombre": actividad.strip() if isinstance(actividad, str) else actividad,
            "descripcion": None,
            "entregable": None,
            "responsable_id": responsable_id,
            "fecha_inicio": fecha_iso(fecha_inicio),
            "fecha_fin": fecha_iso(fecha_fin),
            "periodicidad": None,
            "prioridad": "media",
            "estado": "No iniciado",
            "avance_actual": 0,
            "avance_esperado": 100,
            "presupuesto_planeado": 0,
            "presupuesto_ejecutado": 0,
            "evidencia_url": None,
            "observaciones": observaciones,
            "comentario_actual": None,
            "orden": 0,
            "tags": [],
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        db.collection("actividades").add(data)
        creadas += 1

    print(f"Actividades de Plan Operativo importadas: {creadas}")
    print(f"  - sin responsable (ni por nombre ni por líder de proceso): {sin_responsable}")


if __name__ == "__main__":
    main()
