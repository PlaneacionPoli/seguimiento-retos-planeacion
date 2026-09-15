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

Antes de crear el servicio, en **"Environment Variables"** (o después, en
**Environment** del servicio ya creado), agrega cada una con **"Add Environment Variable"**.
Debajo de cada una se explica exactamente de dónde sacar el valor.

### 1. `FIREBASE_SERVICE_ACCOUNT_JSON` (secreta)

Es la credencial del **Admin SDK** — le da al backend acceso total a Firestore/Auth.

**De dónde sale:**
1. Ve a [Firebase Console](https://console.firebase.google.com/) → abre el proyecto **`gerencia-planeacion-y-gestion`**
2. Clic en el ⚙️ (engranaje) junto a "Project Overview", arriba a la izquierda → **"Configuración del proyecto"** ("Project settings")
3. Pestaña **"Cuentas de servicio"** ("Service accounts")
4. Botón **"Generar nueva clave privada"** ("Generate new private key") → confirma → se descarga un `.json`

Ya tienes uno descargado en el proyecto local como `firebase-service-account.json` (lo usamos para correr la app en tu máquina) — puedes reutilizar ese mismo, no hace falta generar uno nuevo salvo que lo hayas perdido.

**Cómo pasarlo a Render** (el valor debe ir en una sola línea, y el archivo tiene varias):
```bash
python -c "import json; print(json.dumps(json.load(open('firebase-service-account.json', encoding='utf-8'))))" > service_account_oneline_NO_SUBIR.txt
```
Abre `service_account_oneline_NO_SUBIR.txt`, copia **todo** su contenido (empieza con `{"type": "service_account", ...}`) y pégalo como valor de esta variable en Render. Ese archivo ya está en `.gitignore`; bórralo localmente cuando termines.

⚠️ Trátalo como una contraseña maestra: quien tenga este valor puede leer y borrar toda la base de datos.

### 2. `FIREBASE_STORAGE_BUCKET`

**De dónde sale:** Firebase Console → menú izquierdo **"Storage"** (no "Firestore Database", son secciones distintas). Si aparece un botón "Comenzar"/"Get started", Storage **no está activado** (requiere plan Blaze) — en ese caso deja esta variable **vacía**; la app sube evidencias a una carpeta local `/uploads` como respaldo automático. Si ya lo activaste, el nombre del bucket aparece arriba, como `gs://gerencia-planeacion-y-gestion.appspot.com` — copia solo la parte después de `gs://`, sin barra al final.

### 3-8. Configuración pública del frontend

**De dónde sale (los 6 valores salen de la misma pantalla):**
1. Firebase Console → ⚙️ → **"Configuración del proyecto"** → pestaña **"General"**
2. Baja hasta **"Tus apps"** ("Your apps") → busca la app web (ícono `</>`, no la de Android/iOS)
3. Si no ves una, créala con **"Agregar app" → Web** (nombre libre, no hace falta Firebase Hosting)
4. Clic en **"Configuración del SDK"** ("SDK setup and configuration") → opción **"Config"** (no "npm")
5. Verás un bloque `const firebaseConfig = { ... }` — cada campo va a esta variable:

| Campo en `firebaseConfig` | Variable de entorno |
|---|---|
| `apiKey` | `FIREBASE_WEB_API_KEY` |
| `authDomain` | `FIREBASE_WEB_AUTH_DOMAIN` |
| `projectId` | `FIREBASE_WEB_PROJECT_ID` |
| `storageBucket` | `FIREBASE_WEB_STORAGE_BUCKET` |
| `messagingSenderId` | `FIREBASE_WEB_MESSAGING_SENDER_ID` |
| `appId` | `FIREBASE_WEB_APP_ID` |

Estos 6 valores **no son secretos** (se inyectan tal cual en el HTML que ve el navegador), así que no hay riesgo en copiarlos directamente. Ya están guardados en tu `.env` local si quieres copiarlos de ahí en vez de volver a la consola.

### 9. `ENVIRONMENT`

**De dónde sale:** no es de Firebase, es una bandera propia de la app. Escribe literalmente:
```
production
```

### 10. `ALLOWED_ORIGINS`

**De dónde sale:** es la URL que Render le asigna a tu servicio (se confirma en el Paso 6, después de crearlo — Render la muestra arriba del todo una vez que el servicio está "Live"). Como todavía no la conoces al crear el servicio, escribe el valor que planeas usar según el **Name** que le pusiste en el Paso 3:
```
https://seguimiento-retos-planeacion.onrender.com
```
⚠️ Si Render te asignó un nombre distinto (por ejemplo, con un sufijo `-xxxx` porque el nombre exacto ya estaba tomado), edita esta variable después con la URL real — sin `/` al final.

### 11. `DEBUG`

**De dónde sale:** tampoco es de Firebase. Escribe literalmente:
```
False
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
