import requests
from . import lista_misiones



def enviar(mision):

    takeoff = lista_misiones.getMisionParticular(mision)   

    url = takeoff["url"]
    headers = takeoff["headers"]
    payload = takeoff["payload"]


    # POST a FlytBase
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()  # <- esto hace tire excepción
    return response.json()   

    