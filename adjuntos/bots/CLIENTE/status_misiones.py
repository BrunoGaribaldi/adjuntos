from typing import Dict, Any
import copy


DEFAULT_STATUS = {
    "mission_running": False,
    "mission_start_time": 0.0,
    "mission_chat_id": None,
    "waiting_takeoff": False
}

MISION_STATUS = {}


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

