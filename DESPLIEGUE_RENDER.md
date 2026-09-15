# 🚀 Despliegue en Render - Guía Paso a Paso

> Actualizado para la versión institucional (Firebase Auth + Firestore).
> El código vive en: **https://github.com/PlaneacionPoli/seguimiento-retos-planeacion**

## ✅ Pre-requisitos Verificados

Corre `python check_production.py` antes de desplegar. Verifica:
- ✅ `main.py`, `requirements.txt`, `Procfile`, `runtime.txt`, `.gitignore`
- ✅ `templates/dashboard.html`, `templates/login.html`
- ✅ Que `.env` y `firebase-service-account.json` NO estén trackeados en git

---

## 📤 Paso 1: Confirmar que el código está en GitHub

El repositorio ya existe y el código ya fue subido:

```bash
git remote -v   # debe mostrar origin -> PlaneacionPoli/seguimiento-retos-planeacion
git push origin main
```

---

## 🌐 Paso 2: Crear cuenta en Render

1. Ve a [render.com](https://render.com)
2. **"Get Started for Free"** → Recomendado: "Sign up with GitHub" (autoriza la cuenta **PlaneacionPoli**)
3. No se requiere tarjeta de crédito para el plan Free

---

## 🆕 Paso 3: Crear el Web Service

1. Dashboard de Render → **"New +"** → **"Web Service"**
2. Conecta GitHub y selecciona el repositorio **`seguimiento-retos-planeacion`**

### Información Básica

| Campo | Valor |
|-------|-------|
| **Name** | `seguimiento-retos-planeacion` |
| **Region** | Oregon (US West) u otra cercana |
| **Branch** | `main` |
| **Root Directory** | (vacío) |
| **Runtime** | Python 3 |

### Build & Deploy

| Campo | Valor |
|-------|-------|
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Plan** | Free |

---

## 🔐 Paso 4: Variables de Entorno

Antes de crear el servicio, en **"Environment Variables"**, agrega cada una:

### 1. FIREBASE_SERVICE_ACCOUNT_JSON (secreta)
Pega el **contenido completo del JSON de la service account en una sola línea**.
No lo escribas a mano: genera el valor localmente y cópialo desde el archivo
(nunca lo compartas ni lo subas a git):

```bash
python -c "import json; print(json.dumps(json.load(open('firebase-service-account.json', encoding='utf-8'))))" > service_account_oneline_NO_SUBIR.txt
```

Abre `service_account_oneline_NO_SUBIR.txt`, copia todo su contenido y pégalo como
valor de esta variable en Render. Ese archivo ya está en `.gitignore` — bórralo
localmente cuando termines si quieres.

### 2. FIREBASE_STORAGE_BUCKET
```
Value: (dejar vacío mientras no actives Firebase Storage — la app usa /uploads local como respaldo)
```

### 3-8. Configuración pública del frontend (copia los valores de tu `.env` local)
```
FIREBASE_WEB_API_KEY=...
FIREBASE_WEB_AUTH_DOMAIN=gerencia-planeacion-y-gestion.firebaseapp.com
FIREBASE_WEB_PROJECT_ID=gerencia-planeacion-y-gestion
FIREBASE_WEB_STORAGE_BUCKET=gerencia-planeacion-y-gestion.firebasestorage.app
FIREBASE_WEB_MESSAGING_SENDER_ID=...
FIREBASE_WEB_APP_ID=...
```

### 9. ENVIRONMENT
```
Value: production
```

### 10. ALLOWED_ORIGINS
```
Value: https://seguimiento-retos-planeacion.onrender.com
```
⚠️ Ajusta el dominio si Render te asigna uno distinto (lo confirmas en el Paso 6).

### 11. DEBUG
```
Value: False
```

> Ya **no** se usan `SUPABASE_*`, `SECRET_KEY`, `ALGORITHM` ni
> `ACCESS_TOKEN_EXPIRE_MINUTES` — esas variables eran de la versión anterior
> (Supabase). Todo el login ahora es Firebase Authentication.

---

## 🔒 Paso 5: Autorizar el dominio en Firebase Authentication

Firebase bloquea el login desde dominios no autorizados. Antes de probar:

1. Ve a [Firebase Console](https://console.firebase.google.com/) → proyecto `gerencia-planeacion-y-gestion`
2. **Authentication → Settings → Authorized domains**
3. Agrega tu dominio de Render: `seguimiento-retos-planeacion.onrender.com`

---

## 🚀 Paso 6: Desplegar

1. Revisa las variables y clic en **"Create Web Service"**
2. Render clona, instala dependencias y arranca el servicio (3-5 min)
3. Cuando veas **"Live"** ✅, copia la URL real que te asignó
4. Si difiere de la que pusiste en `ALLOWED_ORIGINS`, actualízala (Environment → editar → Save, redespliega solo)
5. Repite el dominio real en Firebase Authentication → Authorized domains (Paso 5)

---

## 🧪 Paso 7: Probar la Aplicación

1. **Login**: abre la URL, debe verse la pantalla "Centro de Mando" (no la de tareas personales)
2. **Registro**: solo si necesitas una cuenta nueva de prueba (recuerda: el primer usuario que se registre queda como `admin` — si ya tienes admin, no vuelvas a probar el registro sin querer)
3. **Dashboard**: KPIs, Retos, Actividades (agrupadas por reto/proceso), Presupuesto
4. **Administración** (si tu rol es admin): usuarios, roles y catálogos

---

## 📊 Ver Logs (si hay problemas)

Render → menú izquierdo → **"Logs"**. Errores típicos de Firestore (cuota
agotada del plan gratuito `429 Quota exceeded`, o `PERMISSION_DENIED` si el
service account está mal pegado) aparecen ahí explícitamente.

---

## ❌ Troubleshooting

### "Application failed to respond" / "502 Bad Gateway"
Verifica el Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT` (con `$PORT`, no un puerto fijo).

### Error de CORS al hacer login
`ALLOWED_ORIGINS` no coincide con la URL real de Render. Corrígela sin `/` al final.

### "auth/unauthorized-domain" en el login
Falta agregar el dominio de Render en Firebase Authentication → Authorized domains (Paso 5).

### 500 Internal Server Error / "Quota exceeded" en los logs
Se agotó la cuota diaria gratuita de Firestore (plan Spark). Opciones:
- Esperar el reinicio diario (medianoche hora Pacífico, EE.UU.)
- Actualizar el proyecto de Firebase al plan **Blaze** (pago por uso, con umbral gratuito generoso)

### La app tarda 30-60s en la primera carga
Normal en el plan Free de Render: el servicio "duerme" tras 15 min sin tráfico.
Para evitarlo, usa [UptimeRobot](https://uptimerobot.com) (gratis) con un ping
cada 14 minutos a tu URL.

---

## 🔄 Actualizar la Aplicación

```bash
git add .
git commit -m "Descripción de cambios"
git push origin main
# Render redespliega automáticamente
```

---

## 🎉 Resumen

- 🌐 **Repo**: https://github.com/PlaneacionPoli/seguimiento-retos-planeacion
- 🔐 **Auth/BD**: Firebase (Authentication + Firestore)
- 💰 **Costo Render**: $0/mes en plan Free (750 h/mes)
- 📄 Detalles adicionales: [GUIA_PRODUCCION.md](./GUIA_PRODUCCION.md) *(nota: aún referencia la versión anterior en algunas secciones — pide una actualización si la necesitas)*
