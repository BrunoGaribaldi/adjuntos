class DataHandler:
    def __init__(self):
        self.colaDatos = []  

    def agregarDatos(self, datos):
        self.colaDatos.append(datos)

    def flushColaDatos(self):
        self.colaDatos.clear()

    def popColaDatos(self):
        if not self.colaDatos:
            return None
        return self.colaDatos.pop(0)
    
    def colaVacia(self):
        return not bool(self.colaDatos)
    
    def getColaDatos(self):
        return self.colaDatos
    
    def obtenerDatosLanded(self):
        dato = self.popColaDatos()
        if not dato:
            return None
        if dato.get('drone') == 'LANDED' and 'Perimetro Planta' in dato.get('flight_details'):
            return dato
        else: 
            return None
        
    def obtenerDatosTakeOff(self):
        dato = self.popColaDatos()
        if dato.get('drone') == 'take off' and 'Perimetro Planta' in dato.get('flight_details'):
            return dato
        else: 
            return {}
        
    
handler = DataHandler()

