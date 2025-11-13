from time import time
from typing import Dict, Any
import copy


DEFAULT_STATUS = {
    "mission_running": False,
    "mission_start_time": None,
    "mission_chat_id": None,
    "mission_name": None,
    "expected_duration": None,
    "waiting_takeoff": False,
    "completed": False,
    "aborted": False
}

MISSION_LOG = []

DRONE_STATE = {
    "in_air": False,
    "takeoff_time": None,
    "last_mission": None
}


def build_status(misions: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Devuelve un dict del tipo:
    {
      "mision1": {"status": {...}},
      "mision2": {"status": {...}},
      ...
    }
    """
    return {
        key: {"status": copy.deepcopy(DEFAULT_STATUS)}
        for key in misions.keys()
    }

def registrar_mision(nombre, estado, duracion_real):
    MISSION_LOG.append({
        "timestamp": time.time(),
        "nombre": nombre,
        "estado": estado,   # “completada” o “abortada”
        "duracion": duracion_real
    })