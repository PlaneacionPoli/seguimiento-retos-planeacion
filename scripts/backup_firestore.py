"""Respaldo rápido de las colecciones 'retos' y 'actividades' (con su subcolección
'seguimientos') a un archivo JSON local, antes de un reemplazo destructivo de datos.

Uso:
    python scripts/backup_firestore.py [nombre_salida.json]
"""
import os
import sys
import json
from datetime import datetime, date
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

OUT_PATH = sys.argv[1] if len(sys.argv) > 1 else f"backup_firestore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


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
    return v


def dump_doc(doc):
    data = {k: serializable(v) for k, v in doc.to_dict().items()}
    data["_id"] = doc.id
    return data


def main():
    db = init_firebase()
    backup = {"retos": [], "actividades": []}

    for doc in db.collection("retos").stream():
        backup["retos"].append(dump_doc(doc))

    for doc in db.collection("actividades").stream():
        act = dump_doc(doc)
        act["_seguimientos"] = [dump_doc(s) for s in doc.reference.collection("seguimientos").stream()]
        backup["actividades"].append(act)

    Path(OUT_PATH).write_text(json.dumps(backup, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Respaldo guardado en {OUT_PATH}: {len(backup['retos'])} retos, {len(backup['actividades'])} actividades")


if __name__ == "__main__":
    main()
