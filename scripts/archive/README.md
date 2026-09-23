# Scripts archivados

Scripts de importación de datos **de un solo uso**, ejecutados durante la migración
inicial del contenido de Retos/Plan Operativo a Firestore (septiembre de 2026). Ya
cumplieron su propósito y no se ejecutan en operación normal de la app. Se conservan
aquí — en vez de borrarse — como referencia histórica de cómo se pobló la base de
datos por primera vez y para poder reconstruir el razonamiento de mapeo de datos si
hace falta.

**No ejecutar estos scripts contra el Firestore de producción sin leerlos primero
completos** — `importar_bd_planeacion.py` no hace upsert (duplica si se corre dos
veces) y `reemplazar_desde_base_2026.py` reemplaza por completo las colecciones
`retos` y `actividades`.

## Orden de ejecución histórico

1. **`importar_bd_planeacion.py`** — primera carga de Retos/Macroactividades desde
   `data/BD_Planeacion.xlsx` (hojas `Retos`, `Macroactividades_Retos`,
   `BD_Cronograma`), con matching por score entre macroactividades y retos.
2. **`reemplazar_desde_base_2026.py`** — reemplazo completo de `retos` y
   `actividades` usando `data/Base_Completa_Retos_2026.xlsx` como fuente única de
   verdad, derivando Proceso/Subproceso/Responsable desde el Área de cada fila.
   Requería haber corrido antes `scripts/backup_firestore.py` (ver
   `data/backup_antes_de_reemplazo.json`, el respaldo tomado antes de esa corrida).
3. **`importar_plan_operativo.py`** — importó la hoja `BD_Cronograma` de
   `BD_Planeacion.xlsx` como actividades sueltas (sin `reto_id`) que complementan
   los Retos ya cargados en el paso 2.

## `data/`

Los archivos Excel/JSON de entrada usados por estos scripts. Excluidos de git
(`.gitignore`: `scripts/archive/data/`) por ser datos institucionales, no código.
