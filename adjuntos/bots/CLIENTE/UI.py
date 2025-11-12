from typing import Dict, Any

# ================== UI: Menú ==================
MAIN_MENU_KEYBOARD: list[list[dict[str, str]]] = []
MAIN_MENU_CHAT: str = ""
MISIONES_DISPONIBLES: str = ""

def set_lista_misiones(misions: Dict[str, Dict[str, Any]]) -> None:
    """Genera una lista numerada con las misiones disponibles y la guarda en MISIONES_DISPONIBLES."""
    global MISIONES_DISPONIBLES

    lineas = []
    for idx, (key, cfg) in enumerate(misions.items(), start=1):
        nombre = cfg.get("name", key)
        descripcion = cfg.get("descripcion", "Misión sin descripción.")
        lineas.append(f"{idx}. {nombre} — {descripcion}")

    MISIONES_DISPONIBLES = "\n".join(lineas)

def set_main_menu_keyboard(misions: Dict[str, Dict[str, Any]], cols: int = 1) -> None:
    """Construye el teclado principal usando los NOMBRES de las misiones."""
    global MAIN_MENU_KEYBOARD
    items = list(misions.items())
    rows: list[list[dict[str, str]]] = []
    for i in range(0, len(items), cols):
        chunk = items[i:i+cols]
        row = [{"text": cfg.get("name", key)} for key, cfg in chunk]
        rows.append(row)
    rows += [
        [{"text": "Lista de misiones"}],
        [{"text": "Estado"}],
        [{"text": "Cerrar"}],
    ]
    MAIN_MENU_KEYBOARD = rows

def set_main_menu_chat(misions: Dict[str, Dict[str, Any]]) -> None:
    """Construye el texto del menú principal con las misiones por nombre."""
    global MAIN_MENU_CHAT
    lines = ["Menú principal:"]
    for key, cfg in misions.items():
        name = cfg.get("name", key)
        lines.append(f"• {name} — Inicia la misión programada.")
    lines.append("• Lista de misiones — Consulta las misiones disponibles.")
    lines.append("• Estado — Revisa el estado operativo del dron.")
    lines.append("• Cerrar — Finaliza la sesión actual.")
    MAIN_MENU_CHAT = "\n".join(lines)

def main_menu_keyboard() -> Dict[str, Any]:
    return {
        "keyboard": MAIN_MENU_KEYBOARD,
        "resize_keyboard": True,
        "one_time_keyboard": False,
        "is_persistent": True
    }

def yes_no_keyboard() -> Dict[str, Any]:
    return {
        "keyboard": [
            [{"text": "Sí"}, {"text": "No"}],
            [{"text": "/cancelar"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
        "is_persistent": True
    }

def back_keyboard() -> Dict[str, Any]:
    return {
        "keyboard": [
            [{"text": "/cancelar"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
        "is_persistent": True
    }

def send_main_menu() -> str:
    return MAIN_MENU_CHAT
