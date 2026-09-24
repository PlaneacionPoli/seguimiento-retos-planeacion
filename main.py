"""
Seguimiento de Retos y Plan Operativo - Gerencia de Planeación y Gestión Institucional
Aplicación FastAPI + Firebase (Firestore + Auth + Storage)
"""

from fastapi import FastAPI, Request, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
import os
import json
from dotenv import load_dotenv
from pathlib import Path
import aiofiles

import firebase_admin
from firebase_admin import credentials, firestore, auth as fb_auth, storage as fb_storage

# ============================================
# CONFIGURACIÓN
# ============================================

load_dotenv()

IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"
ALLOWED_ORIGINS_LIST = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")

FIREBASE_SERVICE_ACCOUNT_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
FIREBASE_SERVICE_ACCOUNT_FILE = os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE", "firebase-service-account.json")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")

FIREBASE_WEB_CONFIG = {
    "apiKey": os.getenv("FIREBASE_WEB_API_KEY", ""),
    "authDomain": os.getenv("FIREBASE_WEB_AUTH_DOMAIN", ""),
    "projectId": os.getenv("FIREBASE_WEB_PROJECT_ID", ""),
    "storageBucket": os.getenv("FIREBASE_WEB_STORAGE_BUCKET", ""),
    "messagingSenderId": os.getenv("FIREBASE_WEB_MESSAGING_SENDER_ID", ""),
    "appId": os.getenv("FIREBASE_WEB_APP_ID", ""),
}

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
EVIDENCIAS_PREFIX = os.getenv("EVIDENCIAS_PREFIX", "evidencias")

UPLOAD_DIR.mkdir(exist_ok=True)

ROLES_VALIDOS = ("responsable", "gerencia", "admin")
ESTADOS_VALIDOS = ("No iniciado", "En curso", "Completado", "Atrasado", "Cancelado")

# ============================================
# INICIALIZACIÓN DE FIREBASE
# ============================================

db = None
bucket = None

try:
    if firebase_admin._apps:
        cred_app = firebase_admin.get_app()
    else:
        if FIREBASE_SERVICE_ACCOUNT_JSON:
            cred = credentials.Certificate(json.loads(FIREBASE_SERVICE_ACCOUNT_JSON))
        elif Path(FIREBASE_SERVICE_ACCOUNT_FILE).exists():
            cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_FILE)
        else:
            cred = None

        if cred is None:
            print("\n" + "=" * 70)
            print("ADVERTENCIA: Configuracion de Firebase no encontrada")
            print("=" * 70)
            print("Define FIREBASE_SERVICE_ACCOUNT_JSON (contenido del JSON) o")
            print(f"coloca el archivo de la service account en: {FIREBASE_SERVICE_ACCOUNT_FILE}")
            print("=" * 70 + "\n")
            cred_app = None
        else:
            cred_app = firebase_admin.initialize_app(cred, {
                "storageBucket": FIREBASE_STORAGE_BUCKET,
            } if FIREBASE_STORAGE_BUCKET else None)

    if cred_app:
        db = firestore.client()
        if FIREBASE_STORAGE_BUCKET:
            bucket = fb_storage.bucket()
        print("OK - Conexion a Firebase establecida correctamente")
except Exception as e:
    print(f"\nERROR al conectar con Firebase: {str(e)}")
    db = None
    bucket = None

security = HTTPBearer()

# ============================================
# APLICACIÓN FASTAPI
# ============================================

app = FastAPI(
    title="Avanza",
    description="Gestor de Planeación - Gerencia de Planeación y Gestión Institucional",
    version="3.0.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


def render(request: Request, template_name: str, **extra):
    context = {"request": request, "firebase_config": FIREBASE_WEB_CONFIG}
    context.update(extra)
    return templates.TemplateResponse(template_name, context)

# ============================================
# MODELOS PYDANTIC
# ============================================

class UserCreate(BaseModel):
    email: str
    password: str
    nombre_completo: Optional[str] = None

class RetoCreate(BaseModel):
    nombre: str
    proceso: Optional[str] = None
    subproceso: Optional[str] = None
    area: Optional[str] = None
    lider_id: Optional[str] = None
    es_proyecto: Optional[bool] = False
    indicador_asociado: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    presupuesto_planeado: Optional[float] = 0
    observaciones: Optional[str] = None

class RetoUpdate(BaseModel):
    nombre: Optional[str] = None
    proceso: Optional[str] = None
    subproceso: Optional[str] = None
    area: Optional[str] = None
    lider_id: Optional[str] = None
    es_proyecto: Optional[bool] = None
    indicador_asociado: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    presupuesto_planeado: Optional[float] = None
    observaciones: Optional[str] = None

class ActividadCreate(BaseModel):
    reto_id: Optional[str] = None
    parent_id: Optional[str] = None
    es_macroactividad: Optional[bool] = False
    proceso: Optional[str] = None
    subproceso: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    entregable: Optional[str] = None
    responsable_id: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    periodicidad: Optional[str] = None
    prioridad: Optional[str] = "media"
    estado: Optional[str] = "No iniciado"
    avance_actual: Optional[float] = 0
    avance_esperado: Optional[float] = 100
    presupuesto_planeado: Optional[float] = 0
    presupuesto_ejecutado: Optional[float] = 0
    evidencia_url: Optional[str] = None
    observaciones: Optional[str] = None
    orden: Optional[int] = 0
    tags: Optional[List[str]] = []

class ActividadUpdate(BaseModel):
    reto_id: Optional[str] = None
    parent_id: Optional[str] = None
    es_macroactividad: Optional[bool] = None
    proceso: Optional[str] = None
    subproceso: Optional[str] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    entregable: Optional[str] = None
    responsable_id: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    periodicidad: Optional[str] = None
    prioridad: Optional[str] = None
    estado: Optional[str] = None
    avance_actual: Optional[float] = None
    avance_esperado: Optional[float] = None
    presupuesto_planeado: Optional[float] = None
    presupuesto_ejecutado: Optional[float] = None
    evidencia_url: Optional[str] = None
    observaciones: Optional[str] = None
    orden: Optional[int] = None
    tags: Optional[List[str]] = None

class SeguimientoCreate(BaseModel):
    avance: Optional[float] = None
    estado: Optional[str] = None
    comentario: Optional[str] = None
    evidencia_url: Optional[str] = None
    monto_ejecutado: Optional[float] = None

class CatalogosUpdate(BaseModel):
    procesos: Optional[List[str]] = None
    subprocesos_por_proceso: Optional[dict] = None
    areas: Optional[List[str]] = None
    periodicidades: Optional[List[str]] = None
    prioridades: Optional[List[str]] = None

class RolUpdate(BaseModel):
    rol: str

# ============================================
# AUTENTICACIÓN Y ROLES
# ============================================

class CurrentUser:
    def __init__(self, uid: str, rol: str):
        self.uid = uid
        self.rol = rol

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    try:
        decoded = fb_auth.verify_id_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    uid = decoded["uid"]
    rol = decoded.get("rol")
    if not rol:
        # El custom claim puede no haberse propagado aún al ID token; se resuelve desde Firestore.
        doc = db.collection("usuarios").document(uid).get()
        rol = doc.to_dict().get("rol", "responsable") if doc.exists else "responsable"
    return CurrentUser(uid, rol)

def require_role(*roles: str):
    def checker(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current.rol not in roles:
            raise HTTPException(status_code=403, detail="No tienes permiso para esta acción")
        return current
    return checker

# ============================================
# HELPERS DE FIRESTORE
# ============================================

def doc_to_dict(doc) -> Optional[dict]:
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return data

def create_doc(collection: str, data: dict) -> dict:
    payload = dict(data)
    payload.setdefault("created_at", firestore.SERVER_TIMESTAMP)
    payload.setdefault("updated_at", firestore.SERVER_TIMESTAMP)
    _, doc_ref = db.collection(collection).add(payload)
    return doc_to_dict(doc_ref.get())

def update_doc(collection: str, doc_id: str, data: dict) -> dict:
    payload = dict(data)
    payload["updated_at"] = firestore.SERVER_TIMESTAMP
    ref = db.collection(collection).document(doc_id)
    ref.update(payload)
    return doc_to_dict(ref.get())

def to_iso(value):
    return value.isoformat() if isinstance(value, date) else value

def dates_to_iso(data: dict, fields: List[str]) -> dict:
    for f in fields:
        if f in data and data[f] is not None:
            data[f] = to_iso(data[f])
    return data

def calcular_estado_efectivo(actividad: dict) -> str:
    """El estado guardado es el 'lógico' (No iniciado/En curso/Completado/Cancelado).
    'Atrasado' es un overlay calculado al leer, no se guarda, para no depender de un job."""
    estado = actividad.get("estado") or "No iniciado"
    if estado in ("Completado", "Cancelado"):
        return estado
    fecha_fin = actividad.get("fecha_fin")
    if fecha_fin and fecha_fin < date.today().isoformat():
        return "Atrasado"
    return estado

def get_actividad_autorizada(actividad_id: str, current: CurrentUser) -> dict:
    doc = db.collection("actividades").document(actividad_id).get()
    data = doc_to_dict(doc)
    if not data:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    if current.rol == "responsable" and data.get("responsable_id") != current.uid:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta actividad")
    return data

def retos_permitidos_responsable(current: CurrentUser) -> set:
    """IDs de retos visibles para un responsable: donde es líder o tiene actividades asignadas."""
    ids = {d.id for d in db.collection("retos").where("lider_id", "==", current.uid).stream()}
    for d in db.collection("actividades").where("responsable_id", "==", current.uid).stream():
        reto_id = d.to_dict().get("reto_id")
        if reto_id:
            ids.add(reto_id)
    return ids

# ============================================
# RUTAS - AUTENTICACIÓN
# ============================================

@app.post("/api/auth/register")
async def register(user: UserCreate):
    """Registrar nuevo usuario. El primer usuario del sistema queda como admin."""
    try:
        fb_user = fb_auth.create_user(
            email=user.email,
            password=user.password,
            display_name=user.nombre_completo,
        )

        es_primero = len(list(db.collection("usuarios").limit(1).stream())) == 0
        rol = "admin" if es_primero else "responsable"

        db.collection("usuarios").document(fb_user.uid).set({
            "nombre_completo": user.nombre_completo,
            "email": user.email,
            "rol": rol,
            "created_at": firestore.SERVER_TIMESTAMP,
        })
        fb_auth.set_custom_user_claims(fb_user.uid, {"rol": rol})

        custom_token = fb_auth.create_custom_token(fb_user.uid)
        if isinstance(custom_token, bytes):
            custom_token = custom_token.decode("utf-8")

        return {
            "custom_token": custom_token,
            "user_id": fb_user.uid,
            "email": user.email,
            "rol": rol,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al registrar usuario: {str(e)}")

@app.get("/api/auth/me")
async def get_me(current: CurrentUser = Depends(get_current_user)):
    doc = db.collection("usuarios").document(current.uid).get()
    data = doc_to_dict(doc)
    if data:
        data["rol"] = current.rol
        return data
    return {"id": current.uid, "rol": current.rol, "nombre_completo": None}

# ============================================
# RUTAS - RETOS (nivel 1)
# ============================================

@app.get("/api/retos")
async def listar_retos(current: CurrentUser = Depends(get_current_user)):
    retos = [doc_to_dict(d) for d in db.collection("retos").stream()]
    if current.rol == "responsable":
        permitidos = retos_permitidos_responsable(current)
        retos = [r for r in retos if r["id"] in permitidos]
    top_level = [doc_to_dict(d) for d in db.collection("actividades").where("parent_id", "==", None).stream()]

    for r in retos:
        hijas = [m for m in top_level if m.get("reto_id") == r["id"]]
        r["num_macroactividades"] = len(hijas)
        r["cumplimiento_promedio"] = round(sum(m.get("avance_actual", 0) or 0 for m in hijas) / len(hijas), 1) if hijas else 0

    retos.sort(key=lambda r: r.get("nombre") or "")
    return retos

@app.get("/api/retos/{reto_id}")
async def obtener_reto(reto_id: str, current: CurrentUser = Depends(get_current_user)):
    data = doc_to_dict(db.collection("retos").document(reto_id).get())
    if not data:
        raise HTTPException(404, "Reto no encontrado")
    if current.rol == "responsable" and reto_id not in retos_permitidos_responsable(current):
        raise HTTPException(status_code=403, detail="No tienes acceso a este reto")
    return data

@app.get("/api/retos/{reto_id}/macroactividades")
async def listar_macroactividades(reto_id: str, current: CurrentUser = Depends(get_current_user)):
    if current.rol == "responsable" and reto_id not in retos_permitidos_responsable(current):
        raise HTTPException(status_code=403, detail="No tienes acceso a este reto")
    docs = db.collection("actividades").where("reto_id", "==", reto_id).where("parent_id", "==", None).stream()
    macros = [doc_to_dict(d) for d in docs]
    for m in macros:
        m["estado_efectivo"] = calcular_estado_efectivo(m)
    macros.sort(key=lambda m: m.get("fecha_inicio") or "")
    return macros

@app.post("/api/retos")
async def crear_reto(payload: RetoCreate, current: CurrentUser = Depends(require_role("gerencia", "admin"))):
    data = payload.dict()
    dates_to_iso(data, ["fecha_inicio", "fecha_fin"])
    return create_doc("retos", data)

@app.put("/api/retos/{reto_id}")
async def actualizar_reto(reto_id: str, payload: RetoUpdate, current: CurrentUser = Depends(require_role("gerencia", "admin"))):
    data = payload.dict(exclude_unset=True)
    dates_to_iso(data, ["fecha_inicio", "fecha_fin"])
    return update_doc("retos", reto_id, data)

@app.delete("/api/retos/{reto_id}")
async def eliminar_reto(reto_id: str, current: CurrentUser = Depends(require_role("gerencia", "admin"))):
    db.collection("retos").document(reto_id).delete()
    return {"message": "Reto eliminado"}

# ============================================
# RUTAS - ACTIVIDADES (Macroactividades + Plan Operativo)
# ============================================

@app.get("/api/actividades")
async def listar_actividades(
    current: CurrentUser = Depends(get_current_user),
    proceso: Optional[str] = None,
    subproceso: Optional[str] = None,
    estado: Optional[str] = None,
    reto_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    responsable_id: Optional[str] = None,
    es_macroactividad: Optional[bool] = None,
):
    if current.rol == "responsable":
        docs = [doc_to_dict(d) for d in db.collection("actividades").where("responsable_id", "==", current.uid).stream()]
        # Si tiene actividades hijas cuya macroactividad padre pertenece a otro responsable,
        # se incluye esa macro (solo lectura) para que la hija tenga dónde anidarse en la UI.
        ids_presentes = {d["id"] for d in docs}
        parent_ids = {d.get("parent_id") for d in docs if d.get("parent_id")} - ids_presentes
        for pid in parent_ids:
            padre = doc_to_dict(db.collection("actividades").document(pid).get())
            if padre:
                docs.append(padre)
    else:
        docs = [doc_to_dict(d) for d in db.collection("actividades").stream()]
        if responsable_id:
            docs = [d for d in docs if d.get("responsable_id") == responsable_id]

    if proceso:
        docs = [d for d in docs if d.get("proceso") == proceso]
    if subproceso:
        docs = [d for d in docs if d.get("subproceso") == subproceso]
    if reto_id:
        docs = [d for d in docs if d.get("reto_id") == reto_id]
    if parent_id:
        docs = [d for d in docs if d.get("parent_id") == parent_id]
    if es_macroactividad is not None:
        docs = [d for d in docs if bool(d.get("es_macroactividad")) == es_macroactividad]

    for d in docs:
        d["estado_efectivo"] = calcular_estado_efectivo(d)
    if estado:
        docs = [d for d in docs if d["estado_efectivo"] == estado]

    docs.sort(key=lambda d: d.get("fecha_inicio") or "")
    return docs

@app.get("/api/actividades/{actividad_id}")
async def obtener_actividad(actividad_id: str, current: CurrentUser = Depends(get_current_user)):
    data = get_actividad_autorizada(actividad_id, current)
    data["estado_efectivo"] = calcular_estado_efectivo(data)
    return data

@app.post("/api/actividades")
async def crear_actividad(payload: ActividadCreate, current: CurrentUser = Depends(get_current_user)):
    data = payload.dict()
    if current.rol == "responsable":
        if data.get("responsable_id") and data["responsable_id"] != current.uid:
            raise HTTPException(status_code=403, detail="Solo puedes crear actividades asignadas a ti mismo")
        data["responsable_id"] = current.uid
    dates_to_iso(data, ["fecha_inicio", "fecha_fin"])
    return create_doc("actividades", data)

@app.put("/api/actividades/{actividad_id}")
async def actualizar_actividad(actividad_id: str, payload: ActividadUpdate, current: CurrentUser = Depends(get_current_user)):
    get_actividad_autorizada(actividad_id, current)
    data = payload.dict(exclude_unset=True)
    if current.rol == "responsable" and "responsable_id" in data and data["responsable_id"] != current.uid:
        raise HTTPException(status_code=403, detail="No puedes reasignar el responsable de la actividad")
    dates_to_iso(data, ["fecha_inicio", "fecha_fin"])
    return update_doc("actividades", actividad_id, data)

@app.delete("/api/actividades/{actividad_id}")
async def eliminar_actividad(actividad_id: str, current: CurrentUser = Depends(require_role("gerencia", "admin"))):
    db.collection("actividades").document(actividad_id).delete()
    return {"message": "Actividad eliminada"}

@app.post("/api/actividades/{actividad_id}/seguimientos")
async def crear_seguimiento(actividad_id: str, payload: SeguimientoCreate, current: CurrentUser = Depends(get_current_user)):
    actividad = get_actividad_autorizada(actividad_id, current)

    avance = payload.avance if payload.avance is not None else actividad.get("avance_actual", 0)
    if payload.estado == "Cancelado":
        nuevo_estado = "Cancelado"
    elif avance >= 100:
        nuevo_estado = "Completado"
    elif avance > 0:
        nuevo_estado = "En curso"
    else:
        nuevo_estado = "No iniciado"

    seguimiento_data = {
        "avance": avance,
        "estado": nuevo_estado,
        "comentario": payload.comentario,
        "evidencia_url": payload.evidencia_url,
        "monto_ejecutado": payload.monto_ejecutado or 0,
        "registrado_por": current.uid,
        "created_at": firestore.SERVER_TIMESTAMP,
    }

    actividad_ref = db.collection("actividades").document(actividad_id)
    transaction = db.transaction()

    @firestore.transactional
    def _aplicar(tx):
        seguimiento_ref = actividad_ref.collection("seguimientos").document()
        tx.set(seguimiento_ref, seguimiento_data)
        updates = {
            "avance_actual": avance,
            "estado": nuevo_estado,
            "comentario_actual": payload.comentario,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        if payload.evidencia_url:
            updates["evidencia_url"] = payload.evidencia_url
        if payload.monto_ejecutado:
            updates["presupuesto_ejecutado"] = firestore.Increment(payload.monto_ejecutado)
        tx.update(actividad_ref, updates)

    _aplicar(transaction)

    data = doc_to_dict(actividad_ref.get())
    data["estado_efectivo"] = calcular_estado_efectivo(data)
    return data

@app.get("/api/actividades/{actividad_id}/seguimientos")
async def historial_actividad(actividad_id: str, current: CurrentUser = Depends(get_current_user)):
    get_actividad_autorizada(actividad_id, current)
    docs = db.collection("actividades").document(actividad_id).collection("seguimientos") \
        .order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    return [doc_to_dict(d) for d in docs]

@app.post("/api/actividades/{actividad_id}/evidencia")
async def subir_evidencia(actividad_id: str, file: UploadFile = File(...), current: CurrentUser = Depends(get_current_user)):
    """Sube un archivo de evidencia y devuelve su URL; el cliente la incluye luego al crear el seguimiento."""
    get_actividad_autorizada(actividad_id, current)

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"Archivo muy grande. Máximo {MAX_FILE_SIZE_MB}MB")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"

    url = None
    if bucket:
        try:
            blob = bucket.blob(f"{EVIDENCIAS_PREFIX}/{actividad_id}/{filename}")
            blob.upload_from_string(contents, content_type=file.content_type)
            blob.make_public()
            url = blob.public_url
        except Exception:
            url = None

    if not url:
        path = UPLOAD_DIR / filename
        async with aiofiles.open(path, "wb") as f:
            await f.write(contents)
        url = f"/uploads/{filename}"

    return {"evidencia_url": url}

# ============================================
# RUTAS - DASHBOARD / KPIs / PRESUPUESTO
# ============================================

@app.get("/api/dashboard/kpis")
async def dashboard_kpis(current: CurrentUser = Depends(get_current_user)):
    if current.rol == "responsable":
        docs = [doc_to_dict(d) for d in db.collection("actividades").where("responsable_id", "==", current.uid).stream()]
    else:
        docs = [doc_to_dict(d) for d in db.collection("actividades").stream()]

    docs = [d for d in docs if not d.get("parent_id")]
    for d in docs:
        d["estado_efectivo"] = calcular_estado_efectivo(d)

    total = len(docs)
    completadas = len([d for d in docs if d["estado_efectivo"] == "Completado"])
    atrasadas = len([d for d in docs if d["estado_efectivo"] == "Atrasado"])
    en_curso = len([d for d in docs if d["estado_efectivo"] == "En curso"])
    avance_promedio = round(sum(d.get("avance_actual", 0) or 0 for d in docs) / total, 1) if total else 0

    return {
        "total": total,
        "completadas": completadas,
        "atrasadas": atrasadas,
        "en_curso": en_curso,
        "avance_promedio": avance_promedio,
        "presupuesto_planeado": sum(d.get("presupuesto_planeado", 0) or 0 for d in docs),
        "presupuesto_ejecutado": sum(d.get("presupuesto_ejecutado", 0) or 0 for d in docs),
    }

@app.get("/api/dashboard/presupuesto")
async def dashboard_presupuesto(current: CurrentUser = Depends(require_role("gerencia", "admin"))):
    docs = [doc_to_dict(d) for d in db.collection("actividades").stream()]
    docs = [d for d in docs if not d.get("parent_id")]
    agregados: dict = {}

    for d in docs:
        key = (d.get("proceso") or "Sin proceso", d.get("subproceso") or "Sin subproceso")
        item = agregados.setdefault(key, {"proceso": key[0], "subproceso": key[1], "planeado": 0, "ejecutado": 0})
        item["planeado"] += d.get("presupuesto_planeado", 0) or 0
        item["ejecutado"] += d.get("presupuesto_ejecutado", 0) or 0

    resultado = list(agregados.values())
    resultado.sort(key=lambda r: (r["proceso"], r["subproceso"]))
    return resultado

# ============================================
# RUTAS - CATÁLOGOS (proceso/subproceso/prioridad)
# ============================================

@app.get("/api/config/catalogos")
async def obtener_catalogos(current: CurrentUser = Depends(get_current_user)):
    ref = db.collection("config").document("catalogos")
    doc = ref.get()
    if doc.exists:
        return doc_to_dict(doc)

    default = {
        "procesos": [],
        "subprocesos_por_proceso": {},
        "areas": [],
        "periodicidades": ["Semanal", "Mensual", "Trimestral", "Semestral", "Anual"],
        "prioridades": ["alta", "media", "baja"],
    }
    ref.set(default)
    default["id"] = "catalogos"
    return default

@app.put("/api/config/catalogos")
async def actualizar_catalogos(payload: CatalogosUpdate, current: CurrentUser = Depends(require_role("gerencia", "admin"))):
    data = payload.dict(exclude_unset=True)
    ref = db.collection("config").document("catalogos")
    ref.set(data, merge=True)
    return doc_to_dict(ref.get())

# ============================================
# RUTAS - ADMINISTRACIÓN (usuarios y roles)
# ============================================

@app.get("/api/admin/usuarios")
async def listar_usuarios(current: CurrentUser = Depends(get_current_user)):
    usuarios = [doc_to_dict(d) for d in db.collection("usuarios").stream()]
    usuarios.sort(key=lambda u: u.get("nombre_completo") or u.get("email") or "")
    return usuarios

@app.put("/api/admin/usuarios/{uid}/rol")
async def actualizar_rol(uid: str, payload: RolUpdate, current: CurrentUser = Depends(require_role("admin"))):
    if payload.rol not in ROLES_VALIDOS:
        raise HTTPException(400, "Rol inválido")

    fb_auth.set_custom_user_claims(uid, {"rol": payload.rol})
    db.collection("usuarios").document(uid).set({"rol": payload.rol}, merge=True)
    return {"message": "Rol actualizado. El usuario debe volver a iniciar sesión para que el cambio surta efecto.", "uid": uid, "rol": payload.rol}

# ============================================
# RUTAS - PÁGINAS HTML
# ============================================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return render(request, "index.html")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return render(request, "login.html")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return render(request, "dashboard.html")

# ============================================
# HEALTH CHECK
# ============================================

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "3.0.0",
        "firebase": db is not None,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
