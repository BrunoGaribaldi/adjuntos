import time
from typing import Optional, Dict, Any
from . import status_misiones
from . import lista_misiones as missions
from . import logs

def resolve_mission_key(text: str, misions: Dict[str, Dict[str, Any]]) -> Optional[str]:
    t = (text or "").strip().lower()
    # 1) Si ya viene la key (mision1, mision2, ...)
    if t in misions:
        return t
    # 2) Buscar por 'name'
    for key, cfg in misions.items():
        if cfg.get("name", "").strip().lower() == t:
            return key
    return None

""" def format_mission_status() -> str:

    if mission_running and current_mission_name:
        elapsed = time.time() - mission_start_time
        remaining = max(0, int(MISSION_DURATION - elapsed))
        minutes, seconds = divmod(remaining, 60)
        return (
            "Estado operativo: EN EJECUCIÓN\n"
            f"Misión activa: {current_mission_name}.\n"
            f"Tiempo restante estimado: {minutes} min {seconds} s."
        )

    return "Estado operativo: INACTIVO\nNo hay misiones en curso en este momento." """

# asegura que la misión no se ejecute para siempre digamos en cuanto a tiempo. Verifica que no se este ejecutando
# Si el tiempo transcurrido supera la duración, marca la misión como finalizada 
""" def update_mission_state(mission_key: str):
    estado = status_misiones.MISION_STATUS.get(mission_key) #estado de mision.
    if not estado:
        logs.client_log_error("No se encontró el estado para la misión", mission=mission_key)
        return

    # Solo si la misión está corriendo
    if estado["status"]["mission_running"]:
        elapsed = time.time() - estado["status"]["mission_start_time"]

    # Duración configurada en lista_misiones
    duracion = missions.MISIONS.get(mission_key, {}).get("duracion", 0)

    if duracion and elapsed >= duracion:
        nombre = missions.MISIONS[mission_key].get("name", mission_key)

        logs.client_log_operation(
                "Misión completada por duración programada",
                mission=nombre,
                elapsed_seconds=int(elapsed),
            )
        
        # Resetear el estado de la misión
        estado["status"]["mission_running"] = False
        estado["status"]["mission_start_time"] = 0.0
        estado["status"]["waiting_takeoff"] = False
        estado["status"]["mission_chat_id"] = None """


    