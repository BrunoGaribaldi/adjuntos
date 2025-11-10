from datetime import datetime, timedelta, timezone
from typing import Any, Dict

#bot brunobauti 8152369007:AAEnROhZ5yTFtBN_LT7Rd-7w5EoU-BpFLIU
#botnqn 8242825417:AAHS5y43tAG5KV3Btadx1Kvz7nRXvFkFyAg

BOT_TOKEN = "8152369007:AAEnROhZ5yTFtBN_LT7Rd-7w5EoU-BpFLIU"
URL_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}/"


POLL_TIMEOUT = 30          # Espera 30 segundos hasta que la conexión cierre. Si no llega nada el request termina y vuelve a llamar getUpdates(). Es para eficientizar.
SLEEP_BETWEEN_POLLS = 4    # Cada vez que llega un mensaje, se espera 4 segundos antes de volver a consultar.
SESSION_TTL_SECS = 180     # Ventana de atención. Define cuanto tiempo esta una ventana activa. En este caso 180 segundos.

OFFSET = 0 # Para no procesar mensajes viejos
# sessions[chat_id] = {"started_at": datetime, "expires_at": datetime, "user_name": str}
SESSIONS: Dict[int, Dict[str, Any]] = {}