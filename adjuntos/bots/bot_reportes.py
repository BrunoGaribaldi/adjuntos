# bots/bot_reportes.py
import os
import sys
import time
import threading
import json
from datetime import datetime, timedelta, timezone
import requests
from statistics import mean

# --- Ajuste de path para imports locales ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from mail.mail_data_handler import handler
from mail.lector_mail import MonitorearCorreo
from utils.logger import log_operation, log_error


# ================== CONFIG ==================
BOT_TOKEN = "8550005676:AAESIJ_NIS0k-4Px9UNcGjTN69peH8KzHHI"
URL_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}/"
REPORT_CHAT_ID = -1003022364244

# Hora de envío diario (formato 24h)
#REPORT_HOUR = 21
#REPORT_MINUTE = 0
now = datetime.now()
REPORT_HOUR = (now + timedelta(minutes=20)).hour
REPORT_MINUTE = (now + timedelta(minutes=20)).minute

# Guardar backup del día (True/False)
SAVE_BACKUP = True


# ================== HELPERS ==================
def send_message(text: str):
    """Envía mensaje de texto al grupo de reportes."""
    url = f"{URL_BASE}sendMessage"
    data = {"chat_id": REPORT_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=data, timeout=10)
        r.raise_for_status()
    except Exception as e:
        log_error("[BotReportes] Error al enviar mensaje", error=str(e))


def start_mail_monitor():
    """Inicia el monitoreo de correos si el cliente no está corriendo."""
    log_operation("[BotReportes] Iniciando monitoreo de correos (modo autónomo)…")
    monitor = MonitorearCorreo()
    t = threading.Thread(target=monitor.ejecutar, kwargs={"intervalo": 60}, daemon=True)
    t.start()


def get_today_events():
    """Filtra eventos del handler correspondientes al día actual."""
    all_events = handler.obtenerTodosLosEventos()
    today = datetime.now(timezone.utc).date()

    today_events = [e for e in all_events if "event_timestamp" in e]
    today_events = [
        e for e in today_events
        if datetime.fromisoformat(e["event_timestamp"]).date() == today
    ]
    return today_events


def generate_daily_report():
    """Crea el texto del reporte diario con lista de misiones lanzadas."""
    events = get_today_events()

    if not events:
        return "📅 No se registraron misiones en el día de hoy."

    takeoffs = [e for e in events if "take" in (e.get("drone_normalizado","") + e.get("message","")).lower()]
    landings = [e for e in events if "land" in (e.get("drone_normalizado","") + e.get("message","")).lower()]


    if not takeoffs and not landings:
        return "📅 No hubo actividad de vuelo registrada hoy."

    # Promedio de batería (solo en aterrizajes)
    avg_battery = (
        mean(
            [
                int(e.get("drone_battery", "0").replace("%", ""))
                for e in landings
                if e.get("drone_battery")
            ]
        )
        if landings
        else 0
    )

    # Lista de misiones (únicas, ordenadas por hora)
    seen = set()
    missions = []
    for e in events:
        name = e.get("flight_details", "").strip()
        if name and name not in seen:
            seen.add(name)
            missions.append(name)

    missions_text = "\n".join([f"{i+1}. {m}" for i, m in enumerate(missions)]) if missions else "—"

    msg = (
        f"📊 *Reporte Diario — {datetime.now().strftime('%d/%m/%Y')}*\n"
        f"🛫 Despegues detectados: {len(takeoffs)}\n"
        f"🛬 Aterrizajes completados: {len(landings)}\n"
        f"🔋 Batería promedio final: {avg_battery:.1f}%\n\n"
        f"🗂️ *Misiones lanzadas:*\n{missions_text}"
    )

    return msg


def flush_daily_events():
    """Guarda los eventos del día (si SAVE_BACKUP=True) y limpia el handler."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        all_events = handler.obtenerTodosLosEventos()

        if SAVE_BACKUP and all_events:
            backup_dir = os.path.join(BASE_DIR, "logs", "reportes")
            os.makedirs(backup_dir, exist_ok=True)
            backup_file = os.path.join(backup_dir, f"{today}.json")

            with open(backup_file, "w") as f:
                json.dump(all_events, f, indent=2)

            log_operation(f"[BotReportes] Backup guardado en {backup_file}")

        # Limpiar handler para nuevo día
        handler.flush()
        log_operation("[BotReportes] Handler limpiado tras generar reporte diario")

    except Exception as e:
        log_error("[BotReportes] Error durante flush diario", error=str(e))


def schedule_report():
    """Calcula el tiempo hasta el próximo reporte diario."""
    now = datetime.now()
    next_run = now.replace(hour=REPORT_HOUR, minute=REPORT_MINUTE, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)

    delay = (next_run - now).total_seconds()
    log_operation(f"[BotReportes] Próximo reporte programado en {delay/3600:.2f}h")

    threading.Timer(delay, run_report).start()


def run_report():
    """Genera y envía el reporte, luego reprograma el siguiente."""
    try:
        log_operation("[BotReportes] Generando reporte diario…")
        report = generate_daily_report()
        send_message(report)
        flush_daily_events()
        log_operation("[BotReportes] Reporte diario enviado con éxito")
    except Exception as e:
        log_error("[BotReportes] Error al generar reporte diario", error=str(e))
    finally:
        schedule_report()


def main():
    log_operation("[BotReportes] Iniciando bot de reportes diarios…")
    start_mail_monitor()  # En caso de que el cliente no esté corriendo
    schedule_report()
    while True:
        time.sleep(60)




if __name__ == "__main__":
    main()
