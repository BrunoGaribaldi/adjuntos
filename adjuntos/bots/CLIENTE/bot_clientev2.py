import os
import sys
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, List, Tuple
import re
import threading
import requests
from . import config
from adjuntos.mail.lector_mail import MonitorearCorreo  
from adjuntos.mail.mail_state_sync import sync_mission_status  
from adjuntos.mail.mail_data_handler import handler      
from . import jsonsender  
from . import logs 
from . import status_misiones
from . import lista_misiones as misiones
from . import UI
from .status_misiones import DRONE_STATE
from . import user_mision_handler

# ================== Loop principal ==================
def main():
    # Cargamos el estado de las misiones con configuraciones default.
    status_misiones.MISION_STATUS = status_misiones.build_status(misiones.MISIONS)

    # Cargamos la UI con las misiones cargadas.
    UI.set_main_menu_chat(misiones.MISIONS)
    UI.set_main_menu_keyboard(misiones.MISIONS)

    # Ignoramos mensajes viejos.
    clear_pending_updates()


    logs.client_log_operation("Bot iniciado con ventanas de conversación y control de misión…")

    # =============================
    # HILOS PARA MAIL Y SINCRONIZACIÓN
    # =============================

    # Hilo A: Lee correos cada 30 segundos
    correo = MonitorearCorreo()
    threading.Thread(
        target=correo.ejecutar,
        args=(30,),      
        daemon=True
    ).start()
    logs.client_log_operation("Hilo de monitoreo de correo iniciado")

    # Hilo  B: Sincroniza estado de misiones cada 10 segundos
    threading.Thread(
        target=sync_mission_status,
        args=(10,),        
        daemon=True
    ).start()
    logs.client_log_operation("Hilo de sincronización de misiones iniciado")

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

                lower = (text or "").lower().strip()

                if lower in ("/start", "hola"):
                    handle_start_or_hola(mission_chat_id, user_name)

                elif lower == "lista de misiones":
                    #a esto hay que agregarle los chequeos de maill
                    #TODO
                    #handle_lista_misiones(mission_chat_id)
                    pass

                elif lower == "estado":
                    #TODO
                    #a esto tmb hay que agregar los chequeos de mail
                    #handle_estado(mission_chat_id)
                    pass

                elif lower in ("cerrar", "/cerrar"):
                    handle_cerrar(mission_chat_id)

                elif lower == "soporte":
                    #TODO
                    pass
                    #prompt_support_opt_in(mission_chat_id)
                
                else:

                    mission_key = user_mision_handler.resolve_mission_key(lower,misiones.MISIONS)

                    if mission_key:
                        handle_mision(mission_key, mission_chat_id, user_name)
                
                    else:
                        handle_fallback(mission_chat_id)


        time.sleep(config.SLEEP_BETWEEN_POLLS)

# ================== Enviar Mision ==================
#TODO
def handle_mision(mission_key: str, chat_id: int, user_name: str):

    # 1) Chequear ventana activa
    if not is_session_active(chat_id):
        remove_keyboard(chat_id, 
            "Tu ventana estaba cerrada por inactividad. Escribí 'hola' para abrir una nueva.")
        return

    touch_session(chat_id)

    # 2) Si el dron está en vuelo → NO permitir misión
    if DRONE_STATE["in_air"]:
        send_message(
            chat_id,
            (
                "*No se puede iniciar la misión.*\n"
                "El dron ya se encuentra en vuelo.\n"
                f"Última misión detectada: {DRONE_STATE['last_mission']}"
            )
        )
        logs.client_log_operation(
            "Intento de lanzamiento con dron en vuelo",
            chat_id=chat_id,
            last_mission=DRONE_STATE["last_mission"]
        )
        return

    # Datos de la misión
    mission_cfg = misiones.MISIONS[mission_key]
    nombre = mission_cfg["name"]

    send_message(chat_id, f"Iniciando misión: {nombre}")
    send_message(chat_id, "Enviando comando a FlytBase...")

    try:
        # 3) Enviar misión
        response = jsonsender.enviar()

        estado = status_misiones.MISION_STATUS[mission_key]["status"]

        estado["mission_running"] = False
        estado["waiting_takeoff"] = True
        estado["mission_start_time"] = time.time()
        estado["expected_duration"] = misiones.MISIONS[mission_key]["duracion"]
        estado["mission_chat_id"] = chat_id
        estado["mission_name"] = nombre
        estado["completed"] = False
        estado["aborted"] = False

        logs.client_log_operation(
            "Misión enviada correctamente",
            chat_id=chat_id,
            mission=nombre,
            response=response,
        )

        send_message(
            chat_id,
            (
                f"Misión '{nombre}' enviada correctamente.\n"
                "Esperando despegue…\n"
                "Bloqueo operativo activo hasta su finalización."
            ),
        )

    except requests.exceptions.RequestException as e:
        logs.client_log_error("Error de comunicación con FlytBase",
                               chat_id=chat_id, mission=nombre, error=str(e))
        send_message(
            chat_id,
            "Error enviando la misión a FlytBase.\n"
            "¿Querés que soporte te contacte por WhatsApp?"
        )

    except Exception as e:
        logs.client_log_error("Error inesperado", chat_id=chat_id,
                              mission=nombre, error=str(e))
        send_message(
            chat_id,
            "Ocurrió un error inesperado.\n"
            "¿Querés asistencia por WhatsApp?"
        )



# ================== Otras Respuestas ==================
#RESPONDEMOS A MENSAJE HOLA
def handle_start_or_hola(chat_id: int, user_name: str):
    if is_session_active(chat_id):
        touch_session(chat_id)
        send_message(chat_id, f"Ya tenés una ventana activa, {user_name}. Usá el menú o escribí 'cerrar' para reiniciar.")
        return
    start_session(chat_id, user_name)
    send_message(
        chat_id,
        (
            f"Hola, {user_name} 👋 Soy el bot operacional de NQNPetrol. "
            f"Tenés una ventana de atención de {config.SESSION_TTL_SECS} segundos."
        ),
    )
    send_message(chat_id,(UI.send_main_menu()),reply_markup=UI.main_menu_keyboard())

#RESPONDEMOS A MENSAJE LISTA DE MISIONES
def handle_lista_misiones(chat_id: int):
    if not is_session_active(chat_id):
        remove_keyboard(chat_id, "Tu ventana estaba cerrada por inactividad. Escribí 'hola' para abrir una nueva.")
        return
    touch_session(chat_id)
    send_message(
    chat_id,
    (
        "Misiones disponibles:\n"
        f"{UI.MISIONES_DISPONIBLES}\n\n"
        "Seleccioná la misión escribiendo o tocando 'mision1'."
    )
)

#RESPONDEMOS A MENSAJE ESTADO
def handle_estado(chat_id: int):
    if not is_session_active(chat_id):
        remove_keyboard(chat_id, "Tu ventana estaba cerrada. Escribí 'hola' para abrir una nueva sesión.")
        return

    touch_session(chat_id)

    # Verificamos el estado del dron
    if DRONE_STATE["in_air"]:
        elapsed = int(time.time() - DRONE_STATE["takeoff_time"])
        minutos, segundos = divmod(elapsed, 60)

        status_msg = (
            "*Estado del dron: EN VUELO*\n\n"
            f"🚁 Última misión: {DRONE_STATE['last_mission']}\n"
            f"⏱ Tiempo en vuelo: {minutos} min {segundos} s"
        )
    else:
        status_msg = (
            "*Estado del dron: EN TIERRA*\n\n"
            "No hay misiones ejecutándose en este momento."
        )

    send_message(chat_id, status_msg)
    logs.client_log_operation("Consulta de estado", chat_id=chat_id, status=status_msg)

    touch_session(chat_id)
    status_message = format_mission_status()
    client_log_operation("Consulta de estado", chat_id=chat_id, status=status_message)
    send_message(chat_id, status_message)

def handle_cerrar(chat_id: int):
    if is_session_active(chat_id):
        end_session(chat_id)
    logs.client_log_operation("Cierre de sesión solicitado", chat_id=chat_id)
    remove_keyboard(chat_id)

def handle_fallback(chat_id: int):
    if is_session_active(chat_id):
        touch_session(chat_id)
        send_message(
            chat_id,
            (
                "No pude interpretar el mensaje recibido.\n"
                "Usá el menú para continuar o escribí 'Lista de misiones'."
            ),
        )
        send_message(chat_id,(UI.send_main_menu()),reply_markup=UI.main_menu_keyboard())
    else:
        send_message(chat_id, "No hay ventana activa. Escribí 'hola' para abrir una nueva sesión operativa.")





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

