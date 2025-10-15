import psycopg
import uuid
import datetime
from db.sqlc.models import *
from db.sqlc.messages import *
CHUNK_DATE, CHUNK_CANT = 10, 50  #10 dias y 50 mensajes

QUEUE = {} #Definir los valores de la cola de eventos
DB = {
    "name":"messages_service",
    "user":"root",
    "password":"secret",
    "host":"localhost",
    "port":"8001"
}
#data se pasa como diccionario para tener todos los valores deseados
def SendEvent(typeM, data):
    global QUEUE
    error = None
    if typeM == "CREATE":
        try:
            #Poner insert
            x = True
        except Exception as e:
            #print("Error:", e)
            error = e
    else:
        error = "Error en el tipo en SendEvent()"
    return error
    

def CreateMessage(thread,user,content,typeM,path):
    resultado, error, data = None, None, {}

    conn = psycopg.connect(
        dbname=DB["name"],
        user=DB["user"],
        password=DB["password"],
        host=DB["host"],
        port=DB["port"]
    )
    conn.autocommit = True
    msg = Message(
        id=None,
        thread_id=thread,
        user_id=user,
        type=typeM,
        content=content,
        paths=path,
        created_at=datetime.datetime.now(),
        updated_at=None,
        deleted_at=None
    )
    try:
        cur = conn.cursor()
        cur.execute(
            CREATE_MESSAGE,
            {
                "p1": msg.id,
                "p2": str(msg.thread_id),
                "p3": str(msg.user_id),
                "p4": msg.type.value if msg.type else None,
                "p5": msg.content,
                "p6": msg.paths,
                "p7": msg.created_at,
                "p8": msg.updated_at
            }
        )
        result = cur.fetchone()
        print("Mensaje insertado:", result)
    except Exception as e:
        error = e
    conn.close()
    if error != None:
        data = {
            "tag": "message-service",
            "message": msg
        }
        error = SendEvent("CREATE", data)
    return resultado, error

def UpdateMessage(thread,message,user,content,typeM,path):
    resultado, error, data = None, None, {}

    error = SendEvent(typeM, data)
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
