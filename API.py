from fastapi import FastAPI, Query
import random
from typing import List
import controller
import logging
from logging.handlers import RotatingFileHandler
import os
DIR = os.path.normpath("/app/logs")
NAME = "logsAPI.log"
os.makedirs(DIR, exist_ok=True)
app = FastAPI()

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    log_path = os.path.join(DIR, NAME)
    handler = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False
    return logger

def set_info(string):
    global LOGS
    LOGS.info(string)
    for h in LOGS.handlers:
        h.flush()
    return None

LOGS = get_logger("API_logs")


#Se llama como: POST /message/1/42?typeM=text&typeM=image&typeM=video
@app.post("/message/{thread_id}/{user_id}/{content}")
def create_message(thread_id: int, user_id: int,content: str ,typeM: List[str] = Query(...), path: List[str] = Query(...)):
    global LOGS
    set_info(f"INGRESO, Crear mensaje. Hilo: {thread_id}, Usuario: {user_id}, Contenido: {content}, Tipos: {typeM}, Path: {path} ")
    resultado, error =controller.CreateMessage(thread_id,user_id,content,typeM,path)
    if error != None:
        set_info(f"FALLO, Crear mensaje. Error: {error}")
        return error
    else:
        set_info(f"EXITO, Crear mensaje. Resultado: {resultado}")
        return resultado

@app.put("/message/{thread_id}/{message_id}/{user_id}/{content}")
def create_message(thread_id: int, message_id: int,user_id: int,content: str ,typeM: List[str] = Query(...), path: List[str] = Query(...)):
    global LOGS
    set_info(f"INGRESO, Modificar mensaje. Hilo: {thread_id}, Mensaje: {message_id},Usuario: {user_id}, Contenido: {content}, Tipos: {typeM}, Path: {path} ")
    resultado, error =controller.ModifyMessage(thread_id,message_id,user_id,content,typeM,path)
    if error != None:
        set_info(f"FALLO, Modificar mensaje. Error: {error}")
        return error
    else:
        set_info(f"EXITO, Modificar mensaje. Resultado: {resultado}")
        return resultado

@app.delete("/message/{message_id}/{user_id}")
def create_message(message_id: int, user_id: int):
    global LOGS
    set_info(f"INGRESO, Eliminar mensaje. Mensaje: {message_id}, Usuario: {user_id}")
    resultado, error =controller.DeleteMessage(message_id,user_id)
    if error != None:
        set_info(f"FALLO, Eliminar mensaje. Error: {error}")
        return error
    else:
        set_info(f"EXITO, Eliminar mensaje. Resultado: {resultado}")
        return resultado