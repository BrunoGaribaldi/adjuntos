import threading
import time

from bots.CLIENTE.bot_cliente import main as run_client_bot
from bots.NOTIFICADOR.bot_notificador import monitor_log
from mail.lector_mail import main as run_mail_lector


def start_client_bot() -> None:
    print("[Main] Iniciando bot de clientes...")
    run_client_bot()


def start_notifier_bot() -> None:
    print("[Main] Iniciando bot de monitoreo de errores...")
    monitor_log()

def start_mail_lector() -> None:
    print("[Main] Iniciando lector de mail flytbase...")
    run_mail_lector()

def main() -> None:
    client_thread = threading.Thread(target=start_client_bot, name="ClientBot", daemon=True)
    notifier_thread = threading.Thread(target=start_notifier_bot, name="NotifierBot", daemon=True)
    lector_mail = threading.Thread(target=start_mail_lector, name="MailLector", daemon=True)  # <-- FIX

    client_thread.start()
    notifier_thread.start()
    lector_mail.start()

    print("[Main] Ambos bots en ejecución. Presioná Ctrl+C para detener.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Main] Finalizando bots...")


if __name__ == "__main__":
    main()
