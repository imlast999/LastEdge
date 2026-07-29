# 📖 LastEdge v2.0 — Manual de Operaciones de Producción

Este documento especifica los procedimientos estándar de operación (SOP) para el despliegue, mantenimiento, respaldos, recuperaciones ante fallos y gestión diaria de la plataforma cuantitativa **LastEdge v2.0**.

---

## 1. Procedimiento de Arranque (Startup Procedure)

Para iniciar la plataforma completa en producción (Backend Bot, Web Dashboard REST/WebSocket y App Server):

### Opción A: Script de Arranque Automatizado (Windows)
```bash
# Ejecutar desde la raíz del proyecto
start_all.bat
```
*(O en PowerShell: `.\start_all.ps1`)*

### Opción B: Ejecución Manual por Componentes
1. **Iniciar Motor Principal (Trading Bot Engine & REST API):**
   ```bash
   python services/bot_service.py
   ```
2. **Iniciar Servidor Web Dashboard:**
   ```bash
   python services/dashboard.py
   ```
3. **Verificar Estado con Go-Live Checklist (P5.1):**
   ```bash
   python run_go_live_checklist.py
   ```

---

## 2. Procedimiento de Parada Limpia (Shutdown Procedure)

Para detener todos los servicios garantizando la persistencia de datos y el cierre limpio de transacciones en SQLite (WAL Mode):

```bash
# Ejecutar desde la raíz del proyecto
stop_all.bat
```

*El script enviará la señal de detención a los procesos Python y cerrará limpiamente las conexiones de SQLite.*

---

## 3. Recuperación Ante Fallos (Failure Recovery)

Si ocurre una caída inesperada del sistema o un fallo de conexión con MetaTrader 5 / Base de Datos:

1. **Auto-recuperación de Base de Datos SQLite (WAL Checkpoint):**
   ```bash
   python run_operational_readiness.py --failure-recovery
   ```
2. **Verificación de Reconexión MT5:**
   El módulo `ReconnectionSystem` intentará reconectar automáticamente con retroceso exponencial (*exponential backoff*).
3. **Verificación del Sistema de Parada de Emergencia (Circuit Breaker):**
   Si se activa el Circuit Breaker por rachas de pérdidas o fallos severos, el bot pausará la ejecución y enviará una alerta crítica a Discord/Telegram.

---

## 4. Actualización del Bot (Bot Updates)

Procedimiento para actualizar el código fuente de LastEdge en producción:

1. Realizar parada limpia de la plataforma:
   ```bash
   stop_all.bat
   ```
2. Crear una copia de seguridad preventiva antes de actualizar:
   ```bash
   python run_operational_readiness.py --backup
   ```
3. Descargar la última versión desde el repositorio Git:
   ```bash
   git pull origin main
   ```
4. Ejecutar la suite de pruebas unitarias para confirmar integridad:
   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   ```
5. Reiniciar los servicios:
   ```bash
   start_all.bat
   ```

---

## 5. Actualización de Estrategias Cuantitativas (Strategy Updates)

Para modificar o ajustar parámetros de las estrategias en `strategies/`:

1. Editar los parámetros cuantitativos o reglas de entrada/salida.
2. Ejecutar la verificación de investigación para validar el modelo:
   ```bash
   python run_exit_research.py
   ```
3. Recargar la configuración en caliente mediante la API o reiniciar los servicios.

---

## 6. Procedimiento de Copias de Seguridad (Backup Procedure)

Las copias de seguridad de la base de datos `bot_state.db` se realizan utilizando la API de Online Backup de SQLite para garantizar consistencia incluso durante operaciones activas en modo WAL:

### Generar Backup por CLI:
```bash
python run_operational_readiness.py --backup
```

### Listar Backups Almacenados:
```bash
python run_operational_readiness.py --list-backups
```

*(Las copias de seguridad se almacenan automáticamente en la carpeta `backups/`).*

---

## 7. Procedimiento de Restauración (Restore Procedure)

Para restaurar una copia de seguridad previamente guardada:

1. Listar los backups disponibles para obtener el nombre del archivo:
   ```bash
   python run_operational_readiness.py --list-backups
   ```
2. Ejecutar la restauración indicando el archivo deseado:
   ```bash
   python run_operational_readiness.py --restore lastedge_backup_YYYYMMDD_HHMMSS.db
   ```
*El sistema verificará automáticamente la integridad del archivo mediante `PRAGMA integrity_check;` antes de reemplazar la base de datos activa.*

---

## 8. Rotación y Mantenimiento de Logs (Log Rotation)

Para evitar el consumo excesivo de disco por archivos de registro:

```bash
python run_operational_readiness.py --rotate-logs
```
*Los archivos `.log` que superen los 10 MB se rotarán automáticamente y se archivarán con sello de fecha/hora.*
