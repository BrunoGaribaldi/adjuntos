import time
import logging
from .mail_data_handler import handler
from adjuntos.bots.CLIENTE import status_misiones
from adjuntos.bots.CLIENTE.status_misiones import MISSION_LOG, registrar_mision

def sync_mission_status():
    logging.info("[SYNC] Monitor de estado iniciado...")

    while True:
        try:
            # Si llego un mail de despegue
            takeoff = handler.obtenerDatosTakeOff()
            if takeoff:
                logging.info("[SYNC] TAKEOFF detectado")
                
                # Encontrar qué misión está esperando takeoff
                for key, data in status_misiones.MISION_STATUS.items():
                    st = data["status"]
                    if st["waiting_takeoff"]:
                        st["waiting_takeoff"] = False
                        st["mission_running"] = True
                        st["mission_start_time"] = time.time()

                        logging.info(f"[SYNC] Misión '{st['mission_name']}' ahora en vuelo.")


            # Si llego un mail de aterrizaje
            landed = handler.obtenerDatosLanded()
            if landed:
                logging.info("[SYNC] LANDED detectado")
                ahora = time.time()

                for key, data in status_misiones.MISION_STATUS.items():
                    st = data["status"]

                    if st["mission_running"]:
                        duracion_real = ahora - st["mission_start_time"]
                        duracion_esperada = st["expected_duration"]

                        chat_id = st["mission_chat_id"]
                        nombre = st["mission_name"]

                        # 1 — abortada

                        #Nos fijamos la duracion de la mision y comparamos con el landed
                        if duracion_real < duracion_esperada * 0.8:
                            st["aborted"] = True
                            st["mission_running"] = False

                            registrar_mision(nombre, "abortada", duracion_real)

                            from bot_clientev2 import send_message
                            send_message(chat_id,
                                f"La misión *{nombre}* fue abortada.\n"
                                f"Duración real: {int(duracion_real)} s"
                            )

                        # 2 — completada normal
                        else:
                            st["completed"] = True
                            st["mission_running"] = False

                            registrar_mision(nombre, "completada", duracion_real)

                            from bot_clientev2 import send_message
                            send_message(chat_id,
                                f"La misión *{nombre}* completó correctamente.\n"
                                f"Duración: {int(duracion_real)} s"
                            )

                        # limpiar
                        st["mission_chat_id"] = None
                        st["mission_start_time"] = None

        except Exception as e:
            logging.error(f"[SYNC] Error: {e}")

        time.sleep(2)
