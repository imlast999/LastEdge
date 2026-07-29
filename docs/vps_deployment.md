# 🚀 LastEdge v2.0 — Guía de Despliegue en VPS Privado

Esta guía proporciona instrucciones paso a paso para desplegar y configurar **LastEdge v2.0** desde cero en un servidor virtual privado (VPS) con sistema operativo Windows.

---

## 1. Requisitos del Servidor VPS

- **Sistema Operativo:** Windows Server 2019 / 2022 o Windows 10/11 Pro (64-bit).
- **Recursos Mínimos:** 2 vCPU, 4 GB RAM, 40 GB SSD.
- **Recursos Recomendados:** 4 vCPU, 8 GB RAM, 80 GB NVMe SSD.
- **Ubicación Geográfica:** Londres (Equinix LD4) o Frankfurt (Equinix FR2) para la menor latencia de ejecución con brókers ECN.
- **Conectividad:** Conexión continua a Internet de alta velocidad con 99.9% de uptime garantizado.

---

## 2. Preparación del Sistema Operativo Windows

1. **Configurar Auto-Login de Usuario en Windows:**
   - Para que el terminal de MetaTrader 5 arranque correctamente con interfaz gráfica al reiniciar el VPS, configura el inicio de sesión automático:
   - Presiona `Win + R`, escribe `netplwiz` y desmarca *"Los usuarios deben escribir su nombre de usuario y contraseña"*.
2. **Desactivar Reinicios Automáticos de Windows Update:**
   - Abre `gpedit.msc` $\rightarrow$ `Configuración del equipo` $\rightarrow$ `Plantillas administrativas` $\rightarrow$ `Componentes de Windows` $\rightarrow$ `Windows Update`.
   - Habilita *"No reiniciar automáticamente con usuarios con sesión iniciada para instalaciones de actualizaciones programadas"*.

---

## 3. Instalación de Dependencias de Software

### A. MetaTrader 5
1. Descarga el instalador de MT5 desde la web oficial de tu bróker.
2. Completa la instalación e inicia sesión con tu cuenta de trading (Demo o Real).
3. En MT5, ve a `Herramientas` $\rightarrow$ `Opciones` $\rightarrow$ `Asesores Expertos`:
   - Marca **"Permitir el trading algorítmico"**.
   - Marca **"Permitir solicitudes WebRequest para las URL listadas"**.

### B. Python 3.11 / 3.13
1. Descarga e instala **Python 3.11+** desde [python.org](https://www.python.org/downloads/).
2. Durante la instalación, marca la casilla **"Add Python to PATH"**.

### C. Git para Windows
1. Descarga e instala Git desde [git-scm.com](https://git-scm.com/).

---

## 4. Clonación del Repositorio y Configuración del Entorno

Abre PowerShell o la terminal de comandos (CMD) en el VPS:

```bash
# 1. Clonar el repositorio oficial de LastEdge
git clone https://github.com/imlast999/LastEdge.git C:\LastEdge
cd C:\LastEdge

# 2. Crear y activar un entorno virtual de Python
python -m venv venv
.\venv\Scripts\activate

# 3. Instalar dependencias Python de producción
pip install -r requirements.txt

# 4. Crear archivo de variables de entorno de producción
copy .env.example .env
```

Edita `.env` con un editor de texto e ingresa tus credenciales del bróker:

```env
MT5_LOGIN=12345678
MT5_PASSWORD=tu_contraseña_segura
MT5_SERVER=TuBroker-Servidor
DISCORD_TOKEN=tu_token_de_bot_discord
TELEGRAM_BOT_TOKEN=tu_token_de_bot_telegram
DASHBOARD_PORT=8080
AUTO_EXECUTE_SIGNALS=1
```

---

## 5. Configuración de Inicio Automático (Auto-Startup)

Para que LastEdge arranque automáticamente si el VPS se reinicia:

### Opción A: Programador de Tareas de Windows (Task Scheduler)
1. Abre `taskschd.msc` y selecciona **Crear tarea**.
2. Nombre: `LastEdge Production Engine`.
3. Desencadenador: **Al iniciar el sistema**.
4. Acción: **Iniciar un programa**.
   - Programa/script: `C:\LastEdge\start_all.bat`
   - Iniciar en: `C:\LastEdge`
5. Marca *"Ejecutar con los privilegios más altos"*.

---

## 6. Lista de Comprobación del Primer Despliegue (Go-Live Checklist)

Antes de autorizar la operativa automática, ejecuta el CLI de verificación pre-producción:

```bash
cd C:\LastEdge
python run_go_live_checklist.py
```

Debe devolver: `✅ PLATAFORMA LISTA PARA TRADING REAL EN PRODUCCIÓN`.

---

## 7. Mantenimiento Diario y Rutinas de Producción

| Tarea | Frecuencia | Comando / Acción |
|---|---|---|
| **Verificación de Salud** | Diario | Notificaciones en Discord/Telegram o `python run_production_monitoring.py` |
| **Copias de Seguridad** | Diario | `python run_operational_readiness.py --backup` |
| **Rotación de Logs** | Semanal | `python run_operational_readiness.py --rotate-logs` |
| **Auditoría de Longevidad** | Mensual | `python run_long_forward_validation.py --list` |

---

## 8. Procedimientos de Recuperación Ante Fallos

1. **Reconexión Perdida con MT5:** `ReconnectionSystem` reconectará automáticamente.
2. **Reinicio de Emergencia de la Plataforma:**
   ```bash
   stop_all.bat
   start_all.bat
   ```
3. **Restaurar Copia de Seguridad:**
   ```bash
   python run_operational_readiness.py --restore lastedge_backup_YYYYMMDD_HHMMSS.db
   ```
