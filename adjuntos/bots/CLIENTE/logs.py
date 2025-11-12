from utils.logger import log_error, log_operation 
from typing import Any

# ======================= LOGS =======================
def client_log_operation(message: str, **context: Any) -> None:
    log_operation(f"[ClientBot] {message}", **context)

def client_log_error(message: str, **context: Any) -> None:
    log_error(f"[ClientBot] {message}", **context)