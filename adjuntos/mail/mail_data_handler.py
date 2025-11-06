from collections import deque
import threading

class DataHandler:
    def __init__(self):
        self.colaDatos = deque()
        self._lock = threading.Lock()

    def agregarDatos(self, datos):
        with self._lock:
            self.colaDatos.append(datos)

    def flushColaDatos(self):
        with self._lock:
            self.colaDatos.clear()

    def colaVacia(self):
        with self._lock:
            return not bool(self.colaDatos)

    def getColaDatos(self):
        with self._lock:
            return list(self.colaDatos)

    def _es_landed(self, d, mission_substr='Perimetro Planta'):
        drone = (d.get('drone') or '').strip().lower().replace(' ', '').replace('-', '')
        msg   = (d.get('message') or '').casefold()
        det   = (d.get('flight_details') or '')
        return (('landed' in drone or 'land' in msg) and mission_substr in det)

    def _es_takeoff(self, d, mission_substr='Perimetro Planta'):
        drone = (d.get('drone') or '').strip().lower().replace(' ', '').replace('-', '')
        msg   = (d.get('message') or '').casefold()
        det   = (d.get('flight_details') or '')
        return ((drone == 'takeoff' or 'take off' in msg or 'takeoff' in msg or 'airborne' in msg)
                and mission_substr in det)

    def obtenerDatosLanded(self, mission_substr='Perimetro Planta'):
        with self._lock:
            for d in list(self.colaDatos):
                if self._es_landed(d, mission_substr):
                    self.colaDatos.remove(d)  # <-- en deque, remove() elimina la primera coincidencia
                    return d
        return None

    def obtenerDatosTakeOff(self, mission_substr='Perimetro Planta'):
        with self._lock:
            for d in list(self.colaDatos):
                if self._es_takeoff(d, mission_substr):
                    self.colaDatos.remove(d)
                    return d
        return None

handler = DataHandler()
