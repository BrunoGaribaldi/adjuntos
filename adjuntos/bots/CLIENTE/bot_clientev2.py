import os
import sys
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, List, Tuple
import re
import threading
import requests
import config
from mail.lector_mail import MonitorearCorreo  
from mail.mail_data_handler import handler      
import adjuntos.bots.CLIENTE.jsonsender as jsonsender  
import logs 
import status_misiones
import lista_misiones as misiones
import UI

# ================== Loop principal ==================
def main():
    # Cargamos el estado de las misiones con configuraciones default.
    status_misiones.MISION_STATUS = status_misiones.build_status(misiones.MISIONS)

    # Cargamos la UI con las misiones cargadas.
    UI.setMainMenuChat(misiones.MISIONS)
    UI.setMainMenuKeyboard(misiones.MISIONS)

    # Ignoramos mensajes viejos.
    clear_pending_updates()


    logs.client_log_operation("Bot iniciado con ventanas de conversación y control de misión…")

    while True:
        updates = get_updates(config.OFFSET)
        if updates:
            for update in updates:
                config.OFFSET = update["update_id"] + 1

                if "message" not in update:
                    continue

                message = update["message"]
                mission_chat_id = message["chat"]["id"]
                text = (message.get("text") or "").strip()
                user_name = message["from"].get("first_name", "Desconocido")


                if not is_session_active(mission_chat_id) and mission_chat_id in config.SESSIONS:
                    end_session(mission_chat_id)
                    remove_keyboard(mission_chat_id, "La ventana expiró por inactividad. Escribí 'hola' para empezar de nuevo.")

                lower = text.lower()
                if lower in ("/start", "hola"):
                    handle_start_or_hola(mission_chat_id, user_name)
                elif lower == "lista de misiones":
                    handle_lista_misiones(mission_chat_id)
                elif lower == "mision1":
                    handle_mision1(mission_chat_id, user_name)
                elif lower == "estado":
                    handle_estado(mission_chat_id)
                elif lower in ("cerrar", "/cerrar"):
                    handle_cerrar(mission_chat_id)
                elif lower == "soporte":
                    prompt_support_opt_in(mission_chat_id)
                else:
                    handle_fallback(mission_chat_id)


        time.sleep(config.SLEEP_BETWEEN_POLLS)


        
# ================== Ignorar mensajes viejos ==================
def clear_pending_updates():
    try:
        url = f"{config.URL_BASE}getUpdates?timeout=1"
        r = requests.get(url, timeout=3)
        r.raise_for_status()
        data = r.json().get("result", [])

        if data:
            # actualizás el OFFSET que vive en config
            config.OFFSET = data[-1]["update_id"] + 1
            logs.client_log_operation(
                "Ignorando mensajes previos al arranque", total=len(data)
            )
        else:
            logs.client_log_operation("No hay mensajes pendientes al inicio")

    except Exception as e:
        logs.client_log_error("Error al limpiar mensajes pendientes", error=str(e))






# ================== Helpers de API ==================

# ------------- Obtener Updates del Chat -------------
def get_updates(offset_value: int) -> List[Dict[str, Any]]:
    """
    Obtiene updates con long polling. No envía mensajes (no hay chat_id en este nivel).
    Ante error, loguea y retorna lista vacía para que el loop principal continúe.
    """
    try:
        url = f"{config.URL_BASE}getUpdates?timeout={config.POLL_TIMEOUT}&offset={offset_value}"
        resp = requests.get(url, timeout=config.POLL_TIMEOUT + 5)
        resp.raise_for_status()
        result = resp.json().get("result", [])
        if result:
            logs.client_log_operation("Actualizaciones recibidas", total=len(result))
        return result
    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", None)
        if status == 409:
            logs.client_log_error("Error 409: Bot activo en otra instancia", error=str(e))
        else:
            logs.client_log_error("Error HTTP inesperado al pedir updates", error=str(e), status_code=status)
        return []
    except Exception as e:
        logs.client_log_error("Error general al pedir updates", error=str(e))
        return []
    
#  ------------- Enviar Mensaje en Chat -------------
def send_message(chat_id: int, text: str, reply_markup: Optional[Dict[str, Any]] = None):
    url = f"{config.URL_BASE}sendMessage"
    data: Dict[str, Any] = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        data["reply_markup"] = json.dumps(reply_markup)
    try:
        r = requests.post(url, data=data, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        logs.client_log_error("Error al enviar mensaje", chat_id=chat_id, error=str(e), payload=text)

def remove_keyboard(chat_id: int, text: str = "Ventana cerrada. Escribí 'hola' para empezar de nuevo."):
    send_message(chat_id, text, reply_markup={"remove_keyboard": True})




# ================== Sesiones ==================

# Devuelve fecha y hora actual en UTC
def now():
    return datetime.now(timezone.utc)

# Comprueba si un usuario identificado por chat_id tiene una sesión activa.
def is_session_active(chat_id: int) -> bool:
    s = config.SESSIONS.get(chat_id)
    if not s:
        return False
    if now() >= s["expires_at"]:
        config.SESSIONS.pop(chat_id, None)
        return False
    return True

# Renueva el vencimiento de la sesión cada vez que el usuario interactúa.
def touch_session(chat_id: int) -> None:
    if chat_id in config.SESSIONS:
        config.SESSIONS[chat_id]["expires_at"] = now() + timedelta(seconds=config.SESSION_TTL_SECS)

# Crea una nueva sesión en memoria.
def start_session(chat_id: int, user_name: str) -> None:
    config.SESSIONS[chat_id] = {
        "started_at": now(),
        "expires_at": now() + timedelta(seconds=config.SESSION_TTL_SECS),
        "user_name": user_name,
    }
    logs.client_log_operation("Sesión iniciada", chat_id=chat_id, user_name=user_name)

# Finaliza la sesión y la elimina de memoria.
def end_session(chat_id: int) -> None:
    session = config.SESSIONS.pop(chat_id, None)
    logs.client_log_operation(
        "Sesión finalizada",
        chat_id=chat_id,
        duration_seconds=int((now() - session["started_at"]).total_seconds()) if session else None
    )

