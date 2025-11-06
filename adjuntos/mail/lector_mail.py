import os
import time
import re
import json
import logging
import imaplib
import email
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from .mail_data_handler import handler

from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



class MonitorearCorreo:
    def __init__(self):
        
        self.config = {
            'email': os.getenv('MON_EMAIL', 'drone01@nqnpetrol.com'),
            'password': os.getenv('MON_PASSWORD', 'nQnpetrol+drone1'),
            'imap_server': os.getenv('MON_IMAP_SERVER', 'imap.hostinger.com'),
            'imap_port': int(os.getenv('MON_IMAP_PORT', '993')),
        }

        self.drone_mapping = {
            'MATRICE4TD01': 'matrice4td-1',
            'MATRICE4TD': 'matrice4td-1',
            'matrice4td01': 'matrice4td-1',
            'matrice4td-01': 'matrice4td-1',
            'matrice4td': 'matrice4td-1',
        }

        self.mail = None 

    def conectar_email(self) -> bool:
        try:
            self.mail = imaplib.IMAP4_SSL(self.config['imap_server'], self.config['imap_port'])
            self.mail.login(self.config['email'], self.config['password'])
            status, data = self.mail.status('INBOX', '(UIDNEXT MESSAGES)')
            logging.info(f"Estado inicial del buzón: {status} - {data}")
            self.mail.select('INBOX')
            logging.info("Conexión IMAP ok")
            return True
        except Exception as e:
            logging.error(f"Error conectando al mail: {e}")
            return False

    def buscar_correos(self):
        try:
            status, messages = self.mail.search(None, 'UNSEEN')
            logging.info(f"Estado búsqueda: {status}")
            if status != 'OK':
                return []
            ids = messages[0].split()
            correos_leer = []

            for correo_id in ids:
                status, msg_data = self.mail.fetch(correo_id, '(RFC822)')
                if status != 'OK' or not msg_data or not msg_data[0]:
                    logging.warning(f"Fetch falló para {correo_id}")
                    continue

                raw_mail = msg_data[0][1]
                msg = email.message_from_bytes(raw_mail)

                # Asunto robusto
                raw_subject = msg.get('Subject', '')
                try:
                    subject = str(make_header(decode_header(raw_subject)))
                except Exception:
                    subject = raw_subject

                remitente = msg.get('From', '')

                if (subject.startswith('INFO: Drone Landed') or subject.startswith('INFO: Drone take off')) and ((
                    'no-reply@flytbase.com' in remitente) or 'drone01@nqnpetrol.com' in remitente):
                    correos_leer.append({
                        'id': correo_id,
                        'asunto': subject,
                        'remitente': remitente,
                        'fecha': msg.get('Date', ''),
                        'mensaje': msg,
                    })
                    logging.info(f"FlytBase OK: {subject}")
                else:
                    logging.info(f"Ignorado: {subject} | From: {remitente}")

            logging.info(f"Total FlytBase a procesar: {len(correos_leer)}")
            return correos_leer
        except Exception as e:
            logging.error(f"Error en buscar_correos: {e}")
            return []

    def obtener_cuerpo_correo(self, mensaje) -> str:
        try:
            if mensaje.is_multipart():
                # Preferir text/plain; si no hay, caer a text/html
                for part in mensaje.walk():
                    ctype = part.get_content_type()
                    disp = str(part.get("Content-Disposition") or "")
                    if ctype == "text/plain" and "attachment" not in disp:
                        return part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                for part in mensaje.walk():
                    if part.get_content_type() == "text/html":
                        return part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                return ""
            else:
                return mensaje.get_payload(decode=True).decode(mensaje.get_content_charset() or 'utf-8', errors='ignore')
        except Exception as e:
            logging.error(f"Error obteniendo cuerpo: {e}")
            return ""

    def extraer_datos_correo(self, cuerpo_correo: str) -> dict:
        try:
            datos = {}
            # Quitar etiquetas HTML para un primer intento
            cuerpo_limpio = re.sub(r'<[^>]+>', '', cuerpo_correo)

            patrones = {
                'event_id': r'Event ID[:\s]*([^\n\r<]+)',
                'message': r'Message[:\s]*([^\n\r<]+)',
                'severity': r'Severity[:\s]*([^\n\r<]+)',
                'drone': r'Drone[:\s]*([^\n\r<]+)',
                'dock': r'Dock[:\s]*([^\n\r<]+)',
                'coordinates': r'Coordinates[:\s]*([^\n\r<]+)',
                'site': r'Site[:\s]*([^\n\r<]+)',
                'organization': r'Organization[:\s]*([^\n\r<]+)',
                'automation': r'Automation[:\s]*([^\n\r<]+)',
                'drone_battery': r'Drone battery[:\s]*([^\n\r<]+)',
                'flight_details': r'Flight details[:\s]*([^\n\r<]+)',
                'timestamp': r'Timestamp[:\s]*([^\n\r<]+)',
            }

            def _aplica(patron, texto):
                m = re.search(patron, texto, re.IGNORECASE)
                if m:
                    val = m.group(1).strip()
                    val = re.sub(r'^[:\s\-]*', '', val)
                    val = re.sub(r'[\s<]+$', '', val)
                    return val
                return None

            # Intento 1: cuerpo limpio
            for k, pat in patrones.items():
                val = _aplica(pat, cuerpo_limpio)
                if val:
                    datos[k] = val

            # Intento 2: original (por si HTML tenía estructura útil)
            if sum(1 for v in datos.values() if v) < 5:
                for k, pat in patrones.items():
                    if not datos.get(k):
                        val = _aplica(pat, cuerpo_correo)
                        if val:
                            datos[k] = val

            # Normalizar drone con mapping
            if 'drone' in datos and datos['drone']:
                clave = datos['drone'].strip()
                datos['drone_normalizado'] = self.drone_mapping.get(clave, self.drone_mapping.get(clave.lower(), clave))

            # Coordenadas
            coords = datos.get('coordinates')
            if coords:
                try:
                    coords_str = re.sub(r'[^0-9\-\., ]', '', coords)
                    latlon = [c.strip() for c in coords_str.split(',') if c.strip()]
                    if len(latlon) == 2:
                        datos['event_coordinates'] = {
                            'latitude': float(latlon[0]),
                            'longitude': float(latlon[1]),
                        }
                    else:
                        datos['event_coordinates'] = None
                except Exception as e:
                    logging.warning(f"No pude parsear coords: {coords} ({e})")
                    datos['event_coordinates'] = None

            # Timestamp robusto
            ts = datos.get('timestamp')
            if ts:
                try:
                    # muchos mails traen "Wed, 05 Nov 2025 10:22:33 +0000"
                    dt = parsedate_to_datetime(ts)
                    datos['event_timestamp'] = dt.isoformat()
                except Exception:
                    # fallback al formato viejo si viene sin headers estándar
                    try:
                        # ej: "05 Nov 2025 10:22:33"
                        datos['event_timestamp'] = datetime.strptime(ts.strip(), '%d %b %Y %H:%M:%S').isoformat()
                    except Exception as e:
                        logging.warning(f"No pude parsear timestamp: {ts} ({e})")
                        datos['event_timestamp'] = None

            return datos
        except Exception as e:
            logging.error(f"Error extrayendo datos: {e}")
            return {}

    def marcar_como_leido(self, correo_id):
        try:
            self.mail.store(correo_id, '+FLAGS', '\\Seen')
        except Exception as e:
            logging.error(f"Error marcando como leído {correo_id}: {e}")

    def procesar_correos(self) -> bool:
        if not self.mail and not self.conectar_email():
            return False

        correos = self.buscar_correos()
        if not correos:
            logging.info("No hay correos FlytBase para procesar")
            return True

        for correo in correos:
            try:
                logging.info(f"Procesando: {correo['asunto']}")
                cuerpo = self.obtener_cuerpo_correo(correo['mensaje'])
                if not cuerpo:
                    logging.warning("Cuerpo vacío")
                    continue

                datos = self.extraer_datos_correo(cuerpo)
                if not datos:
                    logging.warning("Sin datos extraídos")
                    continue

                # → Acá iría tu lógica: guardar en DB, enviar a API, etc.
                print(datos)
                handler.agregarDatos(datos) 
                print("ahora aca")

                # marcar leído solo si procesó ok
                self.marcar_como_leido(correo['id'])

            except Exception as e:
                print("estoy aca")
                logging.error(f"Error procesando {correo['id']}: {e}")

        return True

    def ejecutar(self, intervalo):
        logging.info("Iniciando monitoreo FlytBase…")
        while True:
            try:
                # Re-conectar si se perdió la sesión
                if not self.mail:
                    if not self.conectar_email():
                        time.sleep(60)
                        continue

                self.procesar_correos()
                logging.info(f"Esperando {intervalo} segundos…")
                time.sleep(intervalo)
            except KeyboardInterrupt:
                logging.info("Deteniendo script por teclado")
                break
            except imaplib.IMAP4.abort:
                logging.warning("IMAP abortado, reintentando en 30s")
                self.mail = None
                time.sleep(30)
            except Exception as e:
                logging.error(f"Error en loop: {e}")
                time.sleep(60)


def main(intervalo=10):
    monitor = MonitorearCorreo()
    monitor.ejecutar(intervalo=intervalo)


if __name__ == "__main__":
    main()
