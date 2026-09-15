"""
Script de Verificación Pre-Despliegue
Ejecuta este script antes de desplegar a producción para verificar
que todo está configurado correctamente.

Uso:
    python check_production.py
"""

import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Cargar variables de entorno
load_dotenv()

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def check_env_var(var_name, is_secret=False, required=True):
    """Verifica que una variable de entorno esté configurada"""
    value = os.getenv(var_name)

    if value is None:
        if required:
            print(f"❌ {var_name}: NO CONFIGURADA (REQUERIDA)")
            return False
        else:
            print(f"⚠️  {var_name}: No configurada (opcional)")
            return True

    # Verificar valores por defecto inseguros
    if var_name == "FIREBASE_WEB_PROJECT_ID" and "tu-proyecto" in value:
        print(f"❌ {var_name}: Usando valor de ejemplo (INVÁLIDO)")
        return False

    if is_secret:
        print(f"✅ {var_name}: Configurada (***)")
    else:
        # Truncar valores largos
        display_value = value[:50] + "..." if len(value) > 50 else value
        print(f"✅ {var_name}: {display_value}")

    return True

def check_files():
    """Verifica que los archivos necesarios existan"""
    print_header("Verificación de Archivos")

    files = {
        "main.py": True,
        "requirements.txt": True,
        "Procfile": True,
        ".gitignore": True,
        "templates/dashboard.html": True,
        "templates/login.html": True,
        ".env": False,  # No debe estar en producción
        "firebase-service-account.json": False,  # No debe estar en producción (usar FIREBASE_SERVICE_ACCOUNT_JSON)
    }

    all_ok = True

    for file_path, should_exist in files.items():
        path = Path(file_path)
        exists = path.exists()

        if should_exist and not exists:
            print(f"❌ {file_path}: NO EXISTE (requerido)")
            all_ok = False
        elif should_exist and exists:
            print(f"✅ {file_path}: Existe")
        elif not should_exist and exists:
            print(f"⚠️  {file_path}: Existe (NO subir a Git)")
        else:
            print(f"✅ {file_path}: No existe (correcto)")

    return all_ok

def check_gitignore():
    """Verifica que .gitignore incluya archivos sensibles"""
    print_header("Verificación de .gitignore")

    required_patterns = [".env", "__pycache__", "*.pyc", "venv/"]

    try:
        with open(".gitignore", "r", encoding="utf-8") as f:
            content = f.read()

        all_ok = True
        for pattern in required_patterns:
            if pattern in content:
                print(f"✅ {pattern}: Incluido")
            else:
                print(f"❌ {pattern}: NO incluido (agregar)")
                all_ok = False

        return all_ok
    except FileNotFoundError:
        print("❌ .gitignore: No existe")
        return False

def check_environment():
    """Verifica variables de entorno"""
    print_header("Verificación de Variables de Entorno")

    checks = [
        check_env_var("FIREBASE_SERVICE_ACCOUNT_JSON", is_secret=True, required=True),
        check_env_var("FIREBASE_STORAGE_BUCKET", is_secret=False, required=True),
        check_env_var("FIREBASE_WEB_API_KEY", is_secret=True, required=True),
        check_env_var("FIREBASE_WEB_AUTH_DOMAIN", is_secret=False, required=True),
        check_env_var("FIREBASE_WEB_PROJECT_ID", is_secret=False, required=True),
        check_env_var("FIREBASE_WEB_STORAGE_BUCKET", is_secret=False, required=True),
        check_env_var("FIREBASE_WEB_MESSAGING_SENDER_ID", is_secret=False, required=True),
        check_env_var("FIREBASE_WEB_APP_ID", is_secret=False, required=True),
        check_env_var("ENVIRONMENT", is_secret=False, required=False),
        check_env_var("ALLOWED_ORIGINS", is_secret=False, required=True),
    ]

    return all(checks)

def check_production_settings():
    """Verifica configuraciones específicas de producción"""
    print_header("Configuración de Producción")

    environment = os.getenv("ENVIRONMENT", "development")
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "")

    checks = []

    # Verificar ENVIRONMENT
    if environment == "production":
        print("✅ ENVIRONMENT: production")
        checks.append(True)
    else:
        print(f"⚠️  ENVIRONMENT: {environment} (debería ser 'production' para despliegue)")
        checks.append(True)  # Warning, no error

    # Verificar ALLOWED_ORIGINS
    if "*" in allowed_origins:
        print("❌ ALLOWED_ORIGINS: Incluye '*' (INSEGURO en producción)")
        checks.append(False)
    elif "localhost" in allowed_origins and environment == "production":
        print("⚠️  ALLOWED_ORIGINS: Incluye localhost (no necesario en producción)")
        checks.append(True)
    elif allowed_origins:
        origins = allowed_origins.split(",")
        print(f"✅ ALLOWED_ORIGINS: {len(origins)} origen(es) configurado(s)")
        for origin in origins[:3]:  # Mostrar máximo 3
            print(f"   - {origin.strip()}")
        checks.append(True)
    else:
        print("❌ ALLOWED_ORIGINS: No configurado")
        checks.append(False)

    return all(checks)

def check_requirements():
    """Verifica que requirements.txt tenga las dependencias necesarias"""
    print_header("Verificación de requirements.txt")

    required_packages = [
        "fastapi",
        "uvicorn",
        "firebase-admin",
        "pydantic",
        "python-multipart",
        "python-dotenv"
    ]

    try:
        with open("requirements.txt", "r", encoding="utf-8") as f:
            content = f.read().lower()

        all_ok = True
        for package in required_packages:
            if package in content:
                print(f"✅ {package}: Incluido")
            else:
                print(f"❌ {package}: NO incluido")
                all_ok = False

        return all_ok
    except FileNotFoundError:
        print("❌ requirements.txt: No existe")
        return False

def main():
    """Función principal de verificación"""
    print("\n" + "="*70)
    print("  VERIFICACIÓN PRE-DESPLIEGUE A PRODUCCIÓN")
    print("  Plan de Desarrollo Profesional")
    print("="*70)

    # Ejecutar todas las verificaciones
    results = {
        "Archivos": check_files(),
        ".gitignore": check_gitignore(),
        "Variables de Entorno": check_environment(),
        "Configuración de Producción": check_production_settings(),
        "Dependencias": check_requirements(),
    }

    # Resumen final
    print_header("RESUMEN DE VERIFICACIÓN")

    all_passed = True
    for check_name, passed in results.items():
        status = "✅ CORRECTO" if passed else "❌ REQUIERE ATENCIÓN"
        print(f"{check_name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "="*70)

    if all_passed:
        print("✅ ¡Todo listo para despliegue a producción!")
        print("\nPróximos pasos:")
        print("1. Hacer commit de los cambios: git add . && git commit -m 'Preparar para producción'")
        print("2. Hacer push a GitHub: git push origin main")
        print("3. Configurar variables de entorno en tu plataforma de hosting")
        print("4. Desplegar desde Railway/Render")
        print("="*70 + "\n")
        return 0
    else:
        print("⚠️  Hay problemas que necesitan ser corregidos antes del despliegue.")
        print("\nRevisa los ❌ arriba y corrígelos antes de continuar.")
        print("="*70 + "\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
