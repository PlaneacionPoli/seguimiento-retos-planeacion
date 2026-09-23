"""Exporta las colecciones de Firestore (retos, actividades, usuarios) a un
único archivo Excel con una hoja por colección, para respaldo/consulta manual.

Uso:
    python scripts/exportar_bd_excel.py [nombre_salida.xlsx]
"""
import os
import sys
import json
from datetime import datetime, date
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

OUT_PATH = sys.argv[1] if len(sys.argv) > 1 else f"backup_bd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"


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


def serializable(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False, default=str)
    return v


def dump_doc(doc):
    data = {k: serializable(v) for k, v in doc.to_dict().items()}
    data["id"] = doc.id
    return data


def main():
    db = init_firebase()

    print("Leyendo 'retos'...")
    retos = [dump_doc(d) for d in db.collection("retos").stream()]

    print("Leyendo 'actividades'...")
    actividades = [dump_doc(d) for d in db.collection("actividades").stream()]

    print("Leyendo 'usuarios'...")
    usuarios = [dump_doc(d) for d in db.collection("usuarios").stream()]

    with pd.ExcelWriter(OUT_PATH, engine="openpyxl") as writer:
        pd.DataFrame(retos).to_excel(writer, sheet_name="retos", index=False)
        pd.DataFrame(actividades).to_excel(writer, sheet_name="actividades", index=False)
        pd.DataFrame(usuarios).to_excel(writer, sheet_name="usuarios", index=False)

    print(f"Exportado a {OUT_PATH}: {len(retos)} retos, {len(actividades)} actividades, {len(usuarios)} usuarios")


if __name__ == "__main__":
    main()
