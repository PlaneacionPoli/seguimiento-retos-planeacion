# Scripts operativos

Herramientas de mantenimiento vigentes, pensadas para correrse manualmente contra
Firestore cuando haga falta (no forman parte del flujo de la app ni de CI). Ambas
leen las credenciales de Firebase del `.env` igual que `main.py`
(`FIREBASE_SERVICE_ACCOUNT_FILE`).

## `backup_firestore.py`

Respalda las colecciones `retos` y `actividades` (con su subcolección
`seguimientos`) a un JSON local. Correr **antes** de cualquier operación
destructiva sobre esos datos (reemplazos masivos, migraciones manuales).

```bash
python scripts/backup_firestore.py [nombre_salida.json]
```

## `exportar_bd_excel.py`

Exporta `retos`, `actividades` y `usuarios` a un único Excel (una hoja por
colección), útil para consulta manual o compartir un snapshot con alguien sin
acceso a la consola de Firebase.

```bash
python scripts/exportar_bd_excel.py [nombre_salida.xlsx]
```

## `archive/`

Scripts de importación de datos de un solo uso, ya ejecutados durante la carga
inicial de datos. Ver [`archive/README.md`](archive/README.md).
