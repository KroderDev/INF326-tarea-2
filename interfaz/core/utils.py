import requests
import json
import os
import uuid
from typing import Tuple, Dict, Any, Optional, List

NOMBRE_JSON = r"mapChatsHilos.json"

API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "https://api-grupo04.inf326.nursoft.dev").rstrip("/")
API_GATEWAY_ALT_URL = os.getenv("API_GATEWAY_ALT_URL", "https://api-utfsm.kroder.dev").rstrip("/")
GATEWAY_BASES = [u for u in dict.fromkeys([API_GATEWAY_URL, API_GATEWAY_ALT_URL]) if u]
GATEWAY_BASE = GATEWAY_BASES[0] if GATEWAY_BASES else ""

URLS = {
    "canales": f"{GATEWAY_BASE}/channels",
    "mensajes": f"{GATEWAY_BASE}/messages",
    "moderacion": f"{GATEWAY_BASE}/moderation",
    "presencia": f"{GATEWAY_BASE}/presence",
    "busqueda": f"{GATEWAY_BASE}/search",
    "usuarios": f"{GATEWAY_BASE}/users",
    "archivos": f"{GATEWAY_BASE}/files",
    "hilos": f"{GATEWAY_BASE}/threads",
}

CHATBOT_ENDPOINTS = {
    "academico": {
        "path": "/chatbot-academico/chat",
        "request_key": "message",
        "response_keys": ("reply", "message", "answer"),
    },
    "utilidad": {
        "path": "/chatbot-utilidad/chat",
        "request_key": "message",
        "response_keys": ("reply", "message", "result"),
    },
    "wikipedia": {
        "path": "/chatbot-wikipedia/chat-wikipedia",
        "request_key": "message",
        "response_keys": ("message", "reply"),
    },
    "programacion": {
        "path": "/chatbot-programming/chat",
        "request_key": "message",
        "response_keys": ("reply", "message"),
    },
}

CHATBOT_OPTIONS = [
    ("academico", "Chatbot Academico"),
    ("utilidad", "Chatbot Utilidad"),
    ("wikipedia", "Chatbot Wikipedia"),
    ("programacion", "Chatbot Programacion"),
]
#------------------ USUARIOS ------------------

def API_LogIn(user, password):
    url = URLS["usuarios"] + "/v1/auth/login"
    body = {"username_or_email": user, "password": password}
    
    try:
        response = requests.post(url, json=body)
        
        # Manejo según el código de estado
        if response.status_code == 200:
            data = response.json()
            return True,{
                "success": True,
                "access_token": data.get("access_token"),
                "token_type": data.get("token_type")
            }

        elif response.status_code == 401:
            # Credenciales inválidas
            data = response.json()
            return False,{
                "success": False,
                "error": "Credenciales inválidas",
                "details": data
            }

        elif response.status_code == 422:
            # Error de validación
            data = response.json()
            return False,{
                "success": False,
                "error": "Validation Error",
                "details": data.get("detail", [])
            }

        else:
            # Otro error inesperado
            return False,{
                "success": False,
                "error": f"Error inesperado: {response.status_code}",
                "details": response.text
            }

    except requests.exceptions.RequestException as e:
        # Error de conexión, timeout, etc.
        return False,{
            "success": False,
            "error": f"No se pudo contactar la API: {e}"
        }

def obtener_usuario(token):
    url = URLS["usuarios"] + "/v1/users/me"  # endpoint protegido
    headers = {
        "Authorization": f"Bearer {token}"  # enviamos el JWT
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # lanza error si falla
        data = response.json()
        # Devuelve id y username
        return {
            "id": data.get("id"),
            "username": data.get("username")
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": f"No se pudo obtener usuario: {e}"
        }

def crear_usuario(username, email, password, fullname):
    url = URLS["usuarios"] + "/v1/users/register"  # endpoint para crear usuario
    body = {
        "email": email,
        "username": username,
        "password": password,
        "full_name": fullname
    }
    
    try:
        response = requests.post(url, json=body)
        
        if response.status_code == 201:
            # Usuario creado correctamente
            data = response.json()
            return {
                "success": True,
                "id": data.get("id"),
                "username": data.get("username"),
                "email": data.get("email")
            }
        elif response.status_code == 422:
            # Error de validación
            data = response.json()
            return {
                "success": False,
                "error": "Validation Error",
                "details": data.get("detail", [])
            }
        else:
            return {
                "success": False,
                "error": f"Error inesperado: {response.status_code}",
                "details": response.text
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"No se pudo contactar la API: {e}"
        }


#------------------ PRESENCIA ------------------
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

def registrar_presencia(request):
    url = URLS["presencia"]+"/api/v1.0.0/presence"
    ip = get_client_ip(request)

    data = {
        "userId": request.session["user_id"],
        "device": "web",
        "ip": ip
    }

    r = requests.post(
        url,
        json=data,
        verify=False
    )

    return r.json()

def actualizar_estado_presencia(user_id, status):
    url = URLS["presencia"]+f"/api/v1.0.0/presence/{user_id}"

    data = {
        "status": status  
    }

    try:
        r = requests.patch(
            url,
            json=data,
            verify=False   # solo desarrollo
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def obtener_total_online():
    url = URLS["presencia"]+"/api/v1.0.0/presence"
    params = {"status": "online"}

    try:
        r = requests.get(url, params=params, verify=False)

        # Si el status no es 200, se considera error
        if r.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {r.status_code}",
                "details": r.text
            }

        data = r.json()

        return {
            "success": True,
            "total": data["data"]["total_users"]
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

#------------------ CANALES ------------------
def GetChannelById(channel_id):
    """Llamada GET /v1/channels/{channel_id} — devuelve dict o None si no existe/err."""
    url = f"{URLS['canales']}/v1/channels/{channel_id}"
    headers = {"Accept": "application/json"}
    try:
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            return resp.json()
        else:
            # no disponible, 404, 422, 500 o inesperado -> devolver None para que sea filtrado
            return None
    except requests.exceptions.RequestException:
        return None

def GetChatsMiosFiltrados(owner):
    """Devuelve sólo los canales 'buenos' (is_active == True) entre los que el owner posee."""
    resp = GetChatsMios(owner)
    if not resp.get("success"):
        return resp  # propaga el error tal cual

    canales = resp.get("channels", [])
    canales_filtrados = []

    # usar requests.Session para mejor performance (conexión persistente)
    with requests.Session() as s:
        for c in canales:
            # obtener id del objeto (podría venir como "id" o "_id")
            cid = c.get("id") or c.get("_id")
            if not cid:
                # si no hay id, saltar
                continue

            try:
                r = s.get(f"{URLS['canales']}/v1/channels/{cid}", headers={"Accept":"application/json"}, timeout=6)
            except requests.exceptions.RequestException:
                # salta en caso de error de conexión con ese canal
                continue

            if r.status_code == 200:
                data = r.json()
                # sólo mantener si is_active == True (si no viene la clave, asumimos False)
                if data.get("is_active") is True:
                    # opcional: combinar datos originales y los devueltos por la API
                    # mantengo la estructura original (c) y actualizo con info real del GET
                    merged = c.copy()
                    merged.update(data)
                    canales_filtrados.append(merged)
                # else: canal no activo -> saltar
            else:
                # 404/422/500 -> ignorar/saltar
                continue

    return {"success": True, "channels": canales_filtrados}

def GetChats(user_id):
    url = f"{URLS['canales']}/v1/members/{user_id}"  # endpoint con user_id en path
    headers = {
        "Accept": "application/json",
        # Si necesitas autenticación, por ejemplo con JWT:
        # "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            # Respuesta exitosa, lista de canales
            return {
                "success": True,
                "channels": response.json()
            }
        elif response.status_code == 422:
            # Datos o ID inválidos
            data = response.json()
            return {
                "success": False,
                "error": "Entidad no procesable",
                "details": data
            }
        elif response.status_code == 500:
            # Error interno del servidor
            data = response.json()
            return {
                "success": False,
                "error": "Error interno del servidor",
                "details": data
            }
        else:
            # Otro error inesperado
            return {
                "success": False,
                "error": f"Código inesperado: {response.status_code}",
                "details": response.text
            }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"No se pudo contactar la API: {e}"
        }

def GetChatsMios(owner):
    url = f"{URLS['canales']}/v1/members/owner/{owner}"  # endpoint con user_id en path
    headers = {
        "Accept": "application/json",
        # Si necesitas autenticación, por ejemplo con JWT:
        # "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            # Respuesta exitosa, lista de canales
            #Aca antes de retornar realizar una consulta para filtar cada channel id y ver si estan activos
            return {
                "success": True,
                "channels": response.json()
            }
        elif response.status_code == 422:
            # Datos o ID inválidos
            data = response.json()
            return {
                "success": False,
                "error": "Entidad no procesable",
                "details": data
            }
        elif response.status_code == 500:
            # Error interno del servidor
            data = response.json()
            return {
                "success": False,
                "error": "Error interno del servidor",
                "details": data
            }
        else:
            # Otro error inesperado
            return {
                "success": False,
                "error": f"Código inesperado: {response.status_code}",
                "details": response.text
            }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"No se pudo contactar la API: {e}"
        }    

def CreateChat( name,channel_type, owner_id):
    url = f"{URLS['canales']}/v1/channels/"  # endpoint POST
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        # Si necesitas autenticación, por ejemplo:
        # "Authorization": f"Bearer {token}"
    }

    payload = {
        "channel_type": channel_type,  # "public" o "private"
        "name": name,
        "owner_id": owner_id
    }

    try:
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 201:
            # Canal creado exitosamente
            return {
                "success": True,
                "channel": response.json()
            }

        elif response.status_code == 422:
            # Datos no válidos
            data = response.json()
            return {
                "success": False,
                "error": "Entidad no procesable",
                "details": data
            }

        elif response.status_code == 404:
            data = response.json()
            return {
                "success": False,
                "error": "Recurso no encontrado",
                "details": data
            }

        elif response.status_code == 500:
            # Error interno del servidor
            data = response.json()
            return {
                "success": False,
                "error": "Error interno del servidor",
                "details": data
            }

        else:
            # Otro código inesperado
            return {
                "success": False,
                "error": f"Código inesperado: {response.status_code}",
                "details": response.text
            }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"No se pudo contactar la API: {e}"
        }

def ModifyChat(channel_id, name, channel_type,  owner_id):
    url = f"{URLS['canales']}/v1/channels/{channel_id}"  # endpoint PUT
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        # Si necesitas autenticación:
        # "Authorization": f"Bearer {token}"
    }

    payload = {
        "channel_type": channel_type,
        "name": name,
        "owner_id": owner_id
    }

    try:
        response = requests.put(url, json=payload, headers=headers)

        if response.status_code == 200:
            # Canal modificado correctamente
            return {
                "success": True,
                "channel": response.json()
            }

        elif response.status_code == 404:
            # Canal no encontrado
            data = response.json()
            return {
                "success": False,
                "error": "Recurso no encontrado",
                "details": data
            }

        elif response.status_code == 422:
            # Datos inválidos
            data = response.json()
            return {
                "success": False,
                "error": "Entidad no procesable",
                "details": data
            }

        elif response.status_code == 500:
            # Error interno del servidor
            data = response.json()
            return {
                "success": False,
                "error": "Error interno del servidor",
                "details": data
            }

        else:
            # Código inesperado
            return {
                "success": False,
                "error": f"Código inesperado: {response.status_code}",
                "details": response.text
            }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"No se pudo contactar la API: {e}"
        }

def DeleteChat(channel_id):
    url = f"{URLS['canales']}/v1/channels/{channel_id}"  # endpoint DELETE
    headers = {
        "Accept": "application/json",
        # Si necesitas autenticación:
        # "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.delete(url, headers=headers)

        if response.status_code == 200:
            # Canal desactivado correctamente
            return {
                "success": True,
                "result": response.json()
            }

        elif response.status_code == 404:
            # Canal no encontrado
            data = response.json()
            return {
                "success": False,
                "error": "Recurso no encontrado",
                "details": data
            }

        elif response.status_code == 409:
            # Canal ya estaba desactivado
            data = response.json()
            return {
                "success": False,
                "error": "Conflicto: el canal ya estaba desactivado",
                "details": data
            }

        elif response.status_code == 422:
            # ID inválido u otros datos erróneos
            data = response.json()
            return {
                "success": False,
                "error": "Entidad no procesable",
                "details": data
            }

        elif response.status_code == 500:
            # Error interno del servidor
            data = response.json()
            return {
                "success": False,
                "error": "Error interno del servidor",
                "details": data
            }

        else:
            # Código inesperado
            return {
                "success": False,
                "error": f"Código inesperado: {response.status_code}",
                "details": response.text
            }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"No se pudo contactar la API: {e}"
        }

def AddUserToChannel(channel_id: str, user_id: str, verify: bool = True):
    """
    Agrega un usuario a un canal (POST /v1/members/).
    Retorna:
      - {"success": True, "channel": <json>} en caso OK (200/201)
      - {"success": False, "error": "...", "details": ...} en caso de fallo

    :param channel_id: id del canal (string)
    :param user_id: id del usuario (string)
    :param base_url: URL base del servicio (opcional). Si no se pasa, intenta usar URLS['canales'] o fallback.
    :param verify: pasar False si necesitas ignorar verificación SSL (no recomendado en prod).
    """
    # Determinar base URL
    #base = base_url if base_url else (URLS.get("canales") if "URLS" in globals() and URLS.get("canales") else "https://channel-api.inf326.nur.dev")
    url = f"{URLS['canales']}/v1/members/"

    payload = {
        "channel_id": channel_id,
        "user_id": user_id
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=8, verify=verify)
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"No se pudo contactar la API: {e}"}

    # intentar parsear JSON (si viene)
    try:
        data = r.json()
    except ValueError:
        data = r.text

    if r.status_code in (200, 201):
        return {"success": True, "channel": data}
    elif r.status_code == 404:
        return {"success": False, "error": "Recurso no encontrado", "details": data}
    elif r.status_code == 422:
        return {"success": False, "error": "Entidad no procesable", "details": data}
    elif r.status_code == 500:
        return {"success": False, "error": "Error interno del servidor", "details": data}
    else:
        return {"success": False, "error": f"Código inesperado: {r.status_code}", "details": data}

def RemoveUserFromChannel(channel_id: str, user_id: str, verify: bool = True):
    """
    Elimina un usuario de un canal (DELETE /v1/members/).
    Retorna:
      - {"success": True, "channel": <json>} en caso OK (200)
      - {"success": False, "error": "...", "details": ...} en caso de fallo

    Parámetros:
      - channel_id: id del canal (string)
      - user_id: id del usuario (string)
      - base_url: URL base del servicio (opcional). Si no se pasa, intenta usar URLS['canales'] o fallback.
      - verify: pasar False si necesitas ignorar verificación SSL (no recomendado en prod).
    """
    # Determinar base URL
    #base = base_url if base_url else (URLS.get("canales") if "URLS" in globals() and URLS.get("canales") else "https://channel-api.inf326.nur.dev")
    url = f"{URLS['canales']}/v1/members/"

    payload = {
        "channel_id": channel_id,
        "user_id": user_id
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        r = requests.delete(url, json=payload, headers=headers, timeout=8, verify=verify)
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"No se pudo contactar la API: {e}"}

    # intentar parsear JSON (si viene)
    try:
        data = r.json()
    except ValueError:
        data = r.text

    if r.status_code == 200:
        return {"success": True, "channel": data}
    elif r.status_code == 404:
        return {"success": False, "error": "Recurso no encontrado", "details": data}
    elif r.status_code == 422:
        return {"success": False, "error": "Entidad no procesable", "details": data}
    elif r.status_code == 500:
        return {"success": False, "error": "Error interno del servidor", "details": data}
    else:
        return {"success": False, "error": f"Código inesperado: {r.status_code}", "details": data}

#------------------ HILOS ------------------
"""
def GetHilos(llave):

    Extrae los elementos asociados a una llave (uid) de un ARCHIVO JSON
    y los devuelve como una lista de tuplas (uid, nombre).

    
    # --- Cargar los datos del archivo JSON ---
    try:
        # Abrimos el archivo en modo lectura ('r')
        with open(NOMBRE_JSON, 'r', encoding='utf-8') as f:
            # json.load() lee el archivo y lo convierte en un diccionario
            datos_json = json.load(f)
            
    except FileNotFoundError:
        # Error si la ruta (RUTA_A_TU_JSON) está mal y no se encuentra el archivo
        print(f"ERROR: No se encontró el archivo JSON en: {NOMBRE_JSON}")
        return [] # Devuelve vacío como solicitaste
    except json.JSONDecodeError:
        # Error si el archivo JSON tiene un formato inválido (ej: una coma extra)
        print(f"ERROR: El archivo JSON ({NOMBRE_JSON}) está mal formateado.")
        return [] # Devuelve vacío
    # -------------------------------------------
    
    
    # 1. Obtener la lista de elementos (esto ahora sí funciona)
    lista_elementos = datos_json.get(llave, [])
    
    # 2. Usar la list comprehension (esto estaba bien)
    resultados = [
        (item.get("uid"), item.get("nombre")) 
        for item in lista_elementos 
        if "uid" in item and "nombre" in item
    ]
    
    return resultados

"""

def GetHilosAPI(channel_id: str):
    """
    Llama a la API GET /channel/get_threads y retorna
    una lista de tuplas (thread_id, title).
    """
    url = f"{URLS['hilos']}/channel/get_threads"
    params = {"channel_id": channel_id}

    try:
        response = requests.get(url, params=params)
        print("DATAAAAAAAA: ", response.text)
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Falló la conexión con el servidor: {e}")
        return []

    if response.status_code != 200:
        print(f"ERROR API {response.status_code}: {response.text}")
        return []

    try:
        data = response.json()
        print("DATAAAAAAAA: ",data)
    except ValueError:
        print("ERROR: La respuesta no es JSON válido.")
        return []

    # data debería ser una LISTA de hilos
    # ejemplo:
    # [
    #   {
    #       "thread_id": "...",
    #       "title": "...",
    #       "created_by": "...",
    #       "channel_id": "..."
    #   }
    # ]
    '''
    
    '''
    resultados = [
        (item.get("thread_id"), item.get("title"))
        for item in data
        if "thread_id" in item and "title" in item
    ]
    print("RESULTADOS: ", resultados)
    return resultados

def get_channel_threads(channel_id: str):
    """
    Obtiene todos los hilos asociados a un canal específico mediante GET.
    """
    # Construcción de la URL según la documentación: /channel/get_threads
    url = f"{URLS['hilos']}/channel/get_threads"
    
    # Los parámetros Query (?channel_id=...) se pasan en el diccionario 'params'
    params = {
        "channel_id": channel_id
    }

    headers = {
        "accept": "application/json"
    }

    # Print para depuración (opcional)
    print(f"GET Request a: {url} con params: {params}")

    try:
        # Usamos requests.get para una petición GET
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        
    except requests.RequestException as e:
        return False, {"error": f"Error de red: {e}"}

    # Validación del código de estado
    if resp.status_code != 200:
        # Si es 422, es un error de validación (ej. channel_id formato incorrecto)
        return False, {"error": f"Status {resp.status_code}: {resp.text}"}

    try:
        data = resp.json()
    except ValueError:
        return False, {"error": "Respuesta JSON inválida desde la API"}
    print("NUEVA DATAA: ",data)
    # Retorna True y la lista de hilos
    return True, data
'''
def ManageHilo(action, channel_id, uid=None, new_name=None):

    path = NOMBRE_JSON
    p = path if path else NOMBRE_JSON
    cid = str(channel_id or "").strip()
    if not cid:
        return False, {"error": "channel_id inválido"}

    # Cargar datos (si no existe y la acción es create, inicializamos dict vacío)
    data = {}
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
        except Exception:
            # si el archivo está corrupto, devolvemos error
            return False, {"error": "No se pudo leer el archivo JSON o está corrupto."}
    else:
        if action != "create":
            return False, {"error": f"Archivo JSON no encontrado ({p})."}
        # si create y no existe, data quedará {} y se creará al guardar

    # Asegurar que la lista del canal sea una lista
    lst = data.get(cid)
    if not isinstance(lst, list):
        if lst is None:
            lst = []
            data[cid] = lst
        else:
            # si existe pero no es lista, normalizamos a lista vacía
            lst = []
            data[cid] = lst

    # --- CREATE ---
    if action == "create":
        name = (new_name or "").strip()
        if not name:
            return False, {"error": "new_name vacío para create"}
        new_uid = str(uuid.uuid4())
        item = {"uid": new_uid, "nombre": name}
        lst.append(item)
        # guardar
        try:
            tmp = f"{p}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, p)
        except Exception as e:
            return False, {"error": f"Error guardando archivo: {e}"}
        return True, {"uid": new_uid, "nombre": name, "hilos": lst}

    # Para rename/delete se requiere uid
    uid = str(uid or "").strip()
    if not uid:
        return False, {"error": "uid inválido para esta acción"}

    # buscar el índice/item por uid
    found_idx = None
    for i, it in enumerate(lst):
        if isinstance(it, dict) and str(it.get("uid","")).strip() == uid:
            found_idx = i
            break

    if action == "rename":
        name = (new_name or "").strip()
        if not name:
            return False, {"error": "new_name vacío para rename"}
        if found_idx is None:
            return False, {"error": "Hilo no encontrado"}
        # actualizar nombre
        lst[found_idx]["nombre"] = name
        try:
            tmp = f"{p}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, p)
        except Exception as e:
            return False, {"error": f"Error guardando archivo: {e}"}
        return True, {"uid": uid, "nombre": name, "hilos": lst}

    if action == "delete":
        if found_idx is None:
            return False, {"error": "Hilo no encontrado"}
        # eliminar elemento
        removed = lst.pop(found_idx)
        try:
            tmp = f"{p}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, p)
        except Exception as e:
            return False, {"error": f"Error guardando archivo: {e}"}
        return True, {"uid": uid, "removed": removed, "hilos": lst}

    return False, {"error": f"Acción desconocida: {action}"}
'''
def edit_thread(thread_id: str, title: str, metadata: Optional[Dict[str, Any]] = None):
    """
    Edita un hilo existente (PUT /threads/{thread_id}/edit).
    Requiere thread_id, title y opcionalmente metadata.
    """
    # Construcción de la URL según la documentación: /threads/{thread_id}/edit
    url = f"{URLS['hilos']}/{thread_id}/edit"
    
    # Si no envían metadata, iniciamos un diccionario vacío para cumplir con el esquema
    if metadata is None:
        metadata = {}

    # Preparamos el cuerpo de la petición (Request body)
    payload = {
        "title": title,
        "metadata": metadata
    }

    try:
        # Usamos requests.put para enviar datos al servidor
        # El argumento 'json=' se encarga de convertir el diccionario a JSON 
        # y poner el header Content-Type: application/json automáticamente.
        resp = requests.put(url, json=payload, timeout=10)
        
    except requests.RequestException as e:
        return False, {"error": f"Error de red: {e}"}

    # Validamos el código de éxito (según tu doc es 200)
    if resp.status_code != 200:
        return False, {"error": f"Status {resp.status_code}: {resp.text}"}

    try:
        # Intentamos parsear la respuesta
        data = resp.json()
    except:
        # Si la API devuelve solo un string plano sin comillas o nada, manejamos el error
        # O podrías devolver resp.text si esperas texto plano.
        return False, {"error": "Respuesta JSON inválida"}

    return True, data

def delete_thread(thread_id: str):
    url = f"{URLS['hilos']}/{thread_id}"
    try:
        resp = requests.delete(url, timeout=10)
    except requests.RequestException as e:
        return False, {"error": f"Error de red: {e}"}

    if resp.status_code not in (200, 204):
        return False, {"error": f"Status {resp.status_code}: {resp.text}"}

    try:
        data = resp.json()
    except:
        data = {}

    return True, data
"""
def delete_thread(thread_id: str):
    url = f"{URLS['hilos']}/threads/threads/{thread_id}"
    print("DELETE URL:", url)

    try:
        resp = requests.delete(url, timeout=10)
    except requests.RequestException as e:
        return False, {"error": f"Error de red: {e}"}

    # La API solo devuelve 204
    if resp.status_code == 204:
        return True, {"message": "Hilo eliminado correctamente"}

    # Si devuelve error, lo retornamos
    try:
        data = resp.json()
        return False, {"error": f"Status {resp.status_code}", "detail": data}
    except:
        return False, {"error": f"Status {resp.status_code}", "detail": resp.text}
"""

def create_thread(channel_id: str, thread_name: str, user_id: str):
    url = f"{URLS['hilos']}/"
    print(url)
    params = {
        "channel_id": channel_id,
        "thread_name": thread_name,
        "user_id": user_id,
    }

    try:
        resp = requests.post(url, params=params, timeout=10, allow_redirects=False)
    except requests.RequestException as e:
        return False, {"error": f"Error de red: {e}"}
    print("REQUEST URL:", resp.request.url)            # URL final enviada (con query)
    print("REQUEST METHOD:", resp.request.method)
    print("STATUS:", resp.status_code)
    print("HEADERS (respuesta):", resp.headers)
    print("LOCATION header:", resp.headers.get("Location"))
    if resp.status_code != 200:
        return False, {"error": f"Status {resp.status_code}: {resp.text}"}

    try:
        data = resp.json()
    except:
        return False, {"error": "Respuesta JSON inválida desde la API"}

    return True, data
#------------------ CHAT BOTS ------------------
def API_CB(tipo, texto):
    config = CHATBOT_ENDPOINTS.get(tipo)
    if not config:
        return "No entiendo la solicitud."

    payload = {config.get("request_key", "message"): texto}
    errores = []

    for base in GATEWAY_BASES or [""]:
        url = f"{base.rstrip('/')}{config['path']}"
        try:
            response = requests.post(url, json=payload, timeout=12)
        except requests.exceptions.RequestException as exc:
            errores.append(f"{base or 'sin_base'}: {exc}")
            continue

        # Saltar respuestas HTML (normalmente indican ruta errónea)
        if "text/html" in response.headers.get("content-type", ""):
            errores.append(f"{base or 'sin_base'}: respuesta HTML")
            continue

        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}

        if response.ok:
            for key in config.get("response_keys", ()):
                if isinstance(data, dict) and data.get(key) is not None:
                    return data.get(key)
            if isinstance(data, dict) and len(data) == 1:
                return next(iter(data.values()))
            return str(data)

        errores.append(f"{base or 'sin_base'}: HTTP {response.status_code}")

    return f"Error al contactar la API ({'; '.join(errores)})"

#------------------ MENSAJES ------------------
"""
def formatear_uuid(uid: str) -> str | None:
    # Limpiamos espacios
    uid = uid.strip()
    
    # Si ya tiene guiones y es un UUID válido
    try:
        return str(uuid.UUID(uid))
    except ValueError:
        pass
    
    # Si no tiene guiones, intentamos agregar guiones automáticamente
    # Debe tener exactamente 32 caracteres hexadecimales
    uid_sin_guiones = uid.replace("-", "")
    if len(uid_sin_guiones) != 32:
        return None  # UID inválido
    
    try:
        return str(uuid.UUID(uid_sin_guiones))
    except ValueError:
        return None
"""
def formatear_uuid(uuid_str):
    # Si ya tiene guiones, retornar igual
    if "-" in uuid_str:
        return uuid_str

    # Si tiene 24 caracteres (Mongo ObjectId) → imposible convertir a UUID real
    # pero algunos servicios esperan que lo conviertas a UUID v5
    if len(uuid_str) == 24:
        # UUID determinístico usando lo recibido
        import uuid
        return str(uuid.uuid5(uuid.NAMESPACE_URL, uuid_str))

    return uuid_str

"""

"""
def enviar_mensaje(thread_id: str, user_id: str, contenido: str) -> dict | None:
    tid = formatear_uuid(thread_id)
    #tid = thread_id
    uid = formatear_uuid(user_id)
    #uid=user_id
    if tid is None or uid is None:
        print("IDs de hilo/usuario no validos, no se envia el mensaje.")
        return None

    print("################### USER ID: ", uid)
    print("################### thread ID: ", tid)
    url = f"{URLS['mensajes']}/threads/{tid}/messages"
    headers = {
        "accept": "application/json",
        "X-User-Id": uid,
        "Content-Type": "application/json",
    }
    payload = {
        "content": contenido,
        "type": "text",
        "paths": ["string"],
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Lanza excepción si status >= 400
        return response.json()
    except requests.RequestException as e:
        print("Error al enviar mensaje:", e)
        return None

"""
def obtener_mensajes(thread_id, limit=50, cursor=None):
    #tid = formatear_uuid(thread_id)
    tid =thread_id
    if tid is None:
        print("Thread ID invalido, no se pueden obtener mensajes.")
        return {}
    url = f"{URLS['mensajes']}/threads/{tid}/messages"
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    try:
        r = requests.get(url, params=params, headers={"accept": "application/json"}, timeout=5)
        r.raise_for_status()  # Levanta excepción si hay error HTTP
        if r.content:
            return r.json()
        else:
            print("Respuesta vacía de la API")
            return {}
    except requests.RequestException as e:
        print(f"Error al obtener mensajes: {e}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error al parsear JSON: {e}")
        return {}
"""
def obtener_mensajes(thread_id, limit=50, cursor=None):
    tid = formatear_uuid(thread_id)

    url = f"{URLS['mensajes']}/threads/{tid}/messages"
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor

    try:
        r = requests.get(url, params=params, headers={"accept": "application/json"}, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error al obtener mensajes: {e}")
        return {}

def obtener_archivos_por_mensajes(thread_id: str, message_ids: List[str]) -> dict:
    """
    Consulta la API /v1/files?thread_id=... y agrupa los archivos por message_id.
    Devuelve:
      {"ok": True, "files_by_message": {message_id: [file_obj, ...], ...}}
    o
      {"ok": False, "error": "..."}
    NOTA: las claves en files_by_message incluyen todas las message_ids pasadas
    (si no hay archivos para una message_id, la lista estará vacía).
    """
    url = URLS["archivos"].rstrip("/") + "/v1/files"
    try:
        resp = requests.get(url, params={"thread_id": thread_id}, timeout=10)
        if resp.status_code != 200:
            return {"ok": False, "error": f"Error HTTP {resp.status_code}: {resp.text}"}

        data = resp.json()  # se espera una lista de objetos de archivo

        # Inicializar mapa con todas las message_ids (mantener orden externo)
        files_by_message = {mid: [] for mid in message_ids}
        message_ids_set = set(message_ids)

        # Agrupar archivos por message_id (sólo para los message_ids solicitados)
        for f in data:
            mid = f.get("message_id")
            if mid in message_ids_set:
                files_by_message.setdefault(mid, []).append(f)

        return {"ok": True, "files_by_message": files_by_message}

    except Exception as e:
        return {"ok": False, "error": str(e)}



def GetArchivos(thread_id: str, message_ids: List[str]) -> Tuple[List[Any], Any]:
    """
    Para cada message_id en message_ids (manteniendo el mismo orden) devuelve:
      - una lista de URLs presignadas (si hay 1+ archivos para ese message)
      - False si NO hay archivos para ese message
    Retorna (result_list, None) en caso OK, o (None, error_msg) en caso de error global.
    """
    # 1) Obtener archivos agrupados por message_id
    resultado = obtener_archivos_por_mensajes(thread_id, message_ids)
    if not resultado.get("ok"):
        return [], resultado.get("error")

    files_by_message = resultado["files_by_message"]
    base = URLS["archivos"].rstrip("/")
    presign_timeout = 10

    resultados = []  # mantendrá una entrada por cada message_id en el mismo orden

    for mid in message_ids:
        archivos = files_by_message.get(mid, [])
        if not archivos:
            # No hay archivos para este mensaje → posicion False
            resultados.append(False)
            continue

        # Si hay archivos, intentamos obtener presigned URLs para cada uno
        urls_por_archivo = []
        for archivo in archivos:
            file_id = archivo.get("id")
            if not file_id:
                # objeto inválido, saltar
                continue

            try:
                presign_endpoint = f"{base}/v1/files/{file_id}/presign-download"
                resp = requests.post(presign_endpoint, timeout=presign_timeout)

                if resp.status_code != 200:
                    # Falló obtener presign para este archivo: guardamos un mensaje de error
                    urls_por_archivo.append({"file_id": file_id, "error": f"HTTP {resp.status_code}: {resp.text}"})
                    continue

                # La API devuelve un string (URL). Intentamos parsearlo como JSON (puede ser un string JSON)
                try:
                    presigned = resp.json()
                except ValueError:
                    presigned = resp.text

                urls_por_archivo.append({"file_id": file_id, "url": presigned})

            except Exception as e:
                urls_por_archivo.append({"file_id": file_id, "error": str(e)})

        # Si no pudimos obtener ninguna URL exitosa, pero hubo intentos, devolvemos la lista (con errores)
        # Si prefieres que en caso de que **ningún** archivo tenga URL devuelva False, podrías comprobar:
        any_success = any(isinstance(x, dict) and x.get("url") for x in urls_por_archivo)
        if not any_success:
            # Ningún archivo pudo generar URL presign -> devolvemos lista con errores (útil para debugging)
            resultados.append(urls_por_archivo if urls_por_archivo else False)
        else:
            # Devolver sólo los objetos con "url" y su file_id (manteniendo posible información de error en los que fallaron)
            resultados.append(urls_por_archivo)

    return resultados, None

def subir_archivo(message_id: str, thread_id: str, archivo, token: str | None = None, timeout: int = 30):
    """
    Sube un solo archivo a la API /v1/files.
    Args:
        message_id (str): id del mensaje (query param)
        thread_id (str): id del hilo (query param)
        archivo: archivo de Django (InMemoryUploadedFile o TemporaryUploadedFile)
        api_base_url (str): ej. "https://mi-api.com"
        token (str|None): token Bearer opcional
        timeout (int): segundos antes de timeout
    Returns:
        dict: JSON de respuesta en caso de éxito, o {'error':..., 'detail':...} en fallo esperado.
    """
    url = URLS["archivos"].rstrip("/") + "/v1/files"
    params = {
        "message_id": message_id,
        "thread_id": thread_id
    }

    # files puede ser una tupla (filename, fileobj, content_type)
    content_type = getattr(archivo, "content_type", "application/octet-stream")
    # requests acepta el file-like que entrega Django UploadedFile directamente
    files = {
        "upload": (archivo.name, archivo, content_type)
    }

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.post(url, params=params, files=files, headers=headers, timeout=timeout)
    except requests.RequestException as e:
        # Error de red / timeout
        return {"error": "request_exception", "detail": str(e)}

    # Manejo de código HTTP
    if resp.status_code == 201:
        try:
            return resp.json()
        except ValueError:
            return {"error": "invalid_json", "detail": "La API devolvió 201 pero no JSON válido."}
    elif resp.status_code == 422:
        # Validación: devolver el JSON con detalle si lo tiene
        try:
            return {"error": "validation_error", "detail": resp.json()}
        except ValueError:
            return {"error": "validation_error", "detail": resp.text}
    else:
        # Otros errores
        try:
            body = resp.json()
        except ValueError:
            body = resp.text
        return {"error": "http_error", "status_code": resp.status_code, "detail": body}

'''
def obtener_archivos_por_mensajes(thread_id: str, message_ids: list[str]):
    """
    Consulta la API de archivos filtrando por thread_id y devuelve solo
    aquellos cuyo message_id esté en message_ids.

    Retorna:
      {"ok": True, "files": [...]} en éxito
      {"ok": False, "error": "..."} en caso de fallo
    """
    url = URLS["archivos"]+"/v1/files"
    try:
        # --- 1) Llamar a la API ---
        resp = requests.get(url, params={"thread_id": thread_id}, timeout=10)

        # Manejo de status
        if resp.status_code != 200:
            return {
                "ok": False,
                "error": f"Error HTTP {resp.status_code}: {resp.text}"
            }

        data = resp.json()  # debería ser una lista de archivos

        # --- 2) Filtrar por message_id ---
        message_ids_set = set(message_ids)  # optimiza el lookup O(1)

        archivos_filtrados = [
            f for f in data
            if f.get("message_id") in message_ids_set
        ]

        return {
            "ok": True,
            "files": archivos_filtrados
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }
    
def GetArchivos(thread_id: str, message_ids: list[str]):
    # Llamada a tu función existente
    resultado = obtener_archivos_por_mensajes(thread_id, message_ids)
    url = URLS["archivos"]+"/v1/files"
    if not resultado["ok"]:
        print("ERROR:", resultado["error"])
        return None, resultado["error"]

    archivos = resultado["files"]
    print("Archivos encontrados:", archivos)

    # Diccionario donde guardaremos file_id -> presigned_url
    archivos_descargables = {}

    # Iterar archivos y obtener el enlace de descarga
    for archivo in archivos:
        file_id = archivo["id"]

        try:
            # POST a la API para obtener la URL presignada
            url_presign = f"{url}/{file_id}/presign-download"
            resp = requests.post(url_presign)

            if resp.status_code != 200:
                print(f"Error obteniendo URL para {file_id}: {resp.text}")
                #return None, f"Error obteniendo presign URL para {file_id}"
                archivos_descargables[file_id] = "Error obteniendo el archivo adjunto"

            presigned_url = resp.json()   # La API devuelve un string

            archivos_descargables[file_id] = presigned_url

        except Exception as e:
            #return None, f"Excepción al obtener archivo {file_id}: {e}"
            archivos_descargables[file_id] = "Error obteniendo el archivo adjunto"

    # Si todo funcionó
    return archivos_descargables, None
'''
