# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Unreleased]

### Added
- Inicio de este changelog.
- `docs/` como directorio de documentación técnica (arquitectura, API, base de
  datos, seguridad, despliegue, testing, contribución) — en construcción como
  parte de la iniciativa de modernización técnica.
- `scripts/README.md` y `scripts/archive/README.md` documentando qué scripts
  operativos siguen vigentes y cuáles fueron usados una sola vez para la carga
  inicial de datos.

### Changed
- `.gitignore`: corregida una regla (`Scripts/`) que en Windows coincidía por
  error, sin distinguir mayúsculas/minúsculas, con la carpeta `scripts/` del
  proyecto, dejándola fuera de git desde su creación.

### Removed
- Scripts SQL heredados de la etapa Supabase/PostgreSQL del proyecto
  (`database_setup.sql`, `add_actividades_lograr.sql`, `delete_duplicate.sql`,
  `migration_monthly_plans.sql`, `migrations/002_financial_control.sql`) — el
  modelo de datos actual es Firestore, sin esquema SQL.
- `GUIA_PRODUCCION.md` — describía un despliegue sobre Supabase, superado por
  la guía de despliegue en `docs/DEPLOYMENT.md` (Firebase + Render).

### Archived
- Scripts de importación de datos de un solo uso (`importar_bd_planeacion.py`,
  `reemplazar_desde_base_2026.py`, `importar_plan_operativo.py`) y sus datos de
  entrada movidos a `scripts/archive/` — ya cumplieron su propósito de poblar
  Firestore y no se ejecutan en operación normal.
