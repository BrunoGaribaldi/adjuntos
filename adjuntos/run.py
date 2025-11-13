import threading
import subprocess
import sys, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))     # adjuntos/
PARENT_DIR = os.path.dirname(BASE_DIR)                    # Telegram Mail/

sys.path.append(PARENT_DIR)

def run_cliente():
    import adjuntos.bots.CLIENTE.bot_clientev2 as cliente
    cliente.main()

def run_reportes():
    import adjuntos.bots.REPORTES.bot_reportes as reportes
    reportes.main()

if __name__ == "__main__":
    threading.Thread(target=run_cliente, daemon=False).start()
    threading.Thread(target=run_reportes, daemon=True).start()
