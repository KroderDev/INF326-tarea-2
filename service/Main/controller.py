CHUNK_DATE, CHUNK_CANT = 10, 50  #10 dias y 50 mensajes

def CreateMessage(thread,user,content,typeM,path):
    resultado, error = None, None
    return resultado, error

def ModifyMessage(thread,message,user,content,typeM,path):
    resultado, error = None, None
    return resultado, error

def DeleteMessage(message,user):
    resultado, error = None, None
    return resultado, error   

"""
Tipos de llamada para gestionar:
    Llamada solo por thread:
        GET /message/10
        Se retorna el historico de mensajes en el hilo especificado
    Llamada sin filtro:
        GET /message/10?typeM=1
        Se retorna la cantidad definida para cada tipo 
        (Chunks para filtrar por fecha y chunks para filtrar por cantidad de mensajes)
    Llamada con filtro:
        GET /message/10?typeM=1&filtro=10
        Se retorna segun el filtro especificado.
        (Mensajes desde esa fecha o los ultimos X mensajes)
"""
def GetMessage(thread,typeM,filtro):
    #Si type tiene valor -1 -> El filtro es segun la fecha.
    #Si type tiene valor 1 -> El filtro es segun cantidad de mensajes
    global CHUNK_DATE, CHUNK_CANT
    resultado, error = None, None
    return resultado, error   