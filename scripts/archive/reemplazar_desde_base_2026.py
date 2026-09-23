"""Reemplaza por completo las colecciones 'retos' y 'actividades' usando
'Base_Completa_Retos_2026.xlsx' (hoja 'Base Retos 2026') como única fuente de verdad.

La hoja trae, por fila, una macroactividad de un reto: Área, Reto, Macroactividad,
Entregable, Indicador, Fecha Inicio, Fecha Fin, % de Avance, Comentario de
seguimiento, Estado. No trae Proceso/Subproceso/Responsable — se derivan del área
según el mismo mapeo institucional ya usado en la app (ver ORDEN_AREAS en
dashboard.html). Las filas del área "GERENCIA DE PLANEACIÓN Y GESTIÓN INSTITUCIONAL"
son un rollup duplicado de los retos de las demás áreas y se excluyen.

Uso:
    python scripts/reemplazar_desde_base_2026.py [ruta_al_excel]

Requiere haber corrido antes scripts/backup_firestore.py (por seguridad).
"""
import os
import sys
import json
from pathlib import Path
from collections import defaultdict

import openpyxl
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

EXCEL_PATH = sys.argv[1] if len(sys.argv) > 1 else "Base_Completa_Retos_2026.xlsx"

AREA_EXCLUIDA = "GERENCIA DE PLANEACIÓN Y GESTIÓN INSTITUCIONAL"

AREA_A_PROCESO = {
    "GERENCIA DE PLANEACIÓN (DIRECCIONAMIENTO ESTRATÉGICO)": ("Direccionamiento Estratégico", "Direccionamiento"),
    "DIRECCIÓN DE ESTUDIOS INTERNOS": ("Direccionamiento Estratégico", "Estudios Internos"),
    "GERENCIA DE PLANEACIÓN (SGC)": ("Planificación y Mejora del SIG", "SGC"),
    "GERENCIA DE PLANEACIÓN (SGA)": ("Gestión Ambiental", None),
    "GERENCIA DE PLANEACIÓN (RIESGOS)": ("Gestión de Riesgos", None),
}

ESTADO_MAP = {
    "Completo": "Completado",
    "Pendiente": "En curso",
    "Sin reporte": "No iniciado",
}


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


def borrar_coleccion(db, nombre, con_subcoleccion=None):
    docs = list(db.collection(nombre).stream())
    for d in docs:
        if con_subcoleccion:
            for s in d.reference.collection(con_subcoleccion).stream():
                s.reference.delete()
        d.reference.delete()
    print(f"Borrados {len(docs)} documentos de '{nombre}'")


def main():
    if not Path(EXCEL_PATH).exists():
        raise SystemExit(f"No se encontró el archivo: {EXCEL_PATH}")

    db = init_firebase()

    print("Borrando colecciones existentes...")
    borrar_coleccion(db, "actividades", con_subcoleccion="seguimientos")
    borrar_coleccion(db, "retos")

    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws = wb["Base Retos 2026"]
    filas = [r for r in ws.iter_rows(values_only=True) if r[0] is not None][1:]

    # Agrupar filas por (area, reto) -> lista de filas (macroactividades)
    grupos = defaultdict(list)
    for fila in filas:
        (_unidad, area, reto, macroact, entregable, indicador,
         f_inicio, f_fin, avance, comentario, estado) = fila
        if not reto or area == AREA_EXCLUIDA:
            continue
        grupos[(area, reto.strip() if isinstance(reto, str) else reto)].append(fila)

    retos_creados = 0
    macros_creadas = 0

    for (area, nombre_reto), fs in grupos.items():
        proceso, subproceso = AREA_A_PROCESO.get(area, (None, None))
        fechas_inicio = [fecha_iso(f[6]) for f in fs if f[6]]
        fechas_fin = [fecha_iso(f[7]) for f in fs if f[7]]

        reto_data = {
            "nombre": nombre_reto,
            "proceso": proceso,
            "subproceso": subproceso,
            "area": area,
            "lider_id": None,
            "es_proyecto": False,
            "indicador_asociado": None,
            "fecha_inicio": min(fechas_inicio) if fechas_inicio else None,
            "fecha_fin": max(fechas_fin) if fechas_fin else None,
            "presupuesto_planeado": 0,
            "observaciones": None,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        _, reto_ref = db.collection("retos").add(reto_data)
        retos_creados += 1

        for fila in fs:
            (_unidad, _area, _reto, macroact, entregable, indicador,
             f_inicio, f_fin, avance, comentario, estado) = fila
            if not macroact:
                continue
            estado_app = ESTADO_MAP.get(estado, "No iniciado")
            avance_actual = avance if avance is not None else 0

            macro_data = {
                "reto_id": reto_ref.id,
                "parent_id": None,
                "es_macroactividad": True,
                "proceso": proceso,
                "subproceso": subproceso,
                "nombre": macroact.strip() if isinstance(macroact, str) else macroact,
                "descripcion": indicador,
                "entregable": entregable,
                "responsable_id": None,
                "fecha_inicio": fecha_iso(f_inicio),
                "fecha_fin": fecha_iso(f_fin),
                "periodicidad": None,
                "prioridad": "media",
                "estado": estado_app,
                "avance_actual": avance_actual,
                "avance_esperado": 100,
                "presupuesto_planeado": 0,
                "presupuesto_ejecutado": 0,
                "evidencia_url": None,
                "observaciones": comentario,
                "comentario_actual": comentario,
                "orden": 0,
                "tags": [],
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
            db.collection("actividades").add(macro_data)
            macros_creadas += 1

    print(f"\nRetos creados: {retos_creados}")
    print(f"Macroactividades creadas: {macros_creadas}")
    print("\nImportación completa.")


if __name__ == "__main__":
    main()
