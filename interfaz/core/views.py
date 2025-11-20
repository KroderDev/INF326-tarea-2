from django.shortcuts import render, redirect
from . import utils
# Create your views here.
from django.shortcuts import render
from datetime import datetime
#URL_BASE = "https://api-utfsm.kroder.dev/"

#CANALES = []
#HILOS = ["Certamenes", "Controles","Extra"]

def home(request):
    global USER
    print(request.session)
    total_online = utils.obtener_total_online()
    if not total_online["success"]:
        print("ERROR AL CONSULTAR PRESENCE:", total_online["error"])
        total_online = 0  # o None, como prefieras
    else:
        total_online = total_online["total"]
    if request.method == "GET":
        return render(request, "home.html", {"online": total_online})
    else:
        registro = request.POST.get('registrar')
        print("registro:",registro)
        if registro =="1":
            #Mandar a crear usuario
            return redirect("create_user")
        else:
            username= request.POST.get('username')
            password= request.POST.get('password')  
            #USER = username
            #request.session["user"] = username
            flag,data = utils.API_LogIn(username, password)        
            if flag:
                request.session["token"] = data["access_token"]
                request.session["token_type"] =data["token_type"]
                var = utils.obtener_usuario(request.session["token"])
                request.session["user"] = var["username"]
                request.session["user_id"] = var["id"]
                print("MI ID ",request.session["user_id"])
                utils.registrar_presencia(request)
                return redirect("main")
            else:
                return render(request, "home.html",{"err":data["error"], "online": total_online})   

def create_user(request):  
    print("////////////")
    if request.method == "GET":
        return render(request, "create_user.html") 
    else:
        print("ENTRE A CREAR")
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        fullname = request.POST.get('fullname')
        # Validar que todos los campos tengan valor
        if not username or not email or not password:
            return render(request, "create_user.html", {"err": "Todos los campos son obligatorios."})
        print("Voy a entrar al crear")
        # Llamar a la API para crear el usuario
        resp = utils.crear_usuario(username, email, password,fullname)
        print("Sali del crear",resp["success"])
        if resp["success"]:
            # Hacer login automático
            print("Voy a entrar al login")
            flag, data = utils.API_LogIn(username, password)
            print("Sali del login")
            if flag:
                request.session["token"] = data["access_token"]
                request.session["token_type"] = data["token_type"]
                var = utils.obtener_usuario(request.session["token"])
                request.session["user"] = var["username"]
                request.session["user_id"] = var["id"]
                return redirect("main")
            else:
                return render(request, "home.html", {"err": "Usuario creado, pero no se pudo iniciar sesión."})
        else:
            # Mostrar mensaje de error real de la API
            error_msg = resp["error"]
            if resp.get("details"):
                error_msg += f": {resp.get('details')}"
            return render(request, "create_user.html", {"err": error_msg})
   
def log_out(request):
    #Actualizar la sesion mandar a cerrar
    utils.actualizar_estado_presencia(request.session["user_id"], "offline")
    request.session.flush()
    return redirect("home")

def main(request): 
    ip = request.META.get('REMOTE_ADDR')
    print("//////MI IP: ",ip)
    user_id = request.session.get("user_id")  
    if not user_id:
        return redirect("home")  # si no hay sesión, redirige a login    
    if request.method == "GET":
        chats = utils.GetChats(user_id)
        chatsMIOS = utils.GetChatsMiosFiltrados(user_id)           
        print("entreeeeeeeeeee")
        if chats["success"] and chats["success"]:
            canales_dict = {
                c["name"]: [c["id"], c["user_count"], c["channel_type"]]
                for c in chats["channels"]
            }

            # Diccionario de canales que YO manejo
            canales_dictMIOS = {
                c["name"]: [c["id"], c["user_count"], c["channel_type"]]
                for c in chatsMIOS["channels"]
            }

            # Obtener solo los NO míos
            canales_no_mios = {
                name: data
                for name, data in canales_dict.items()
                if name not in canales_dictMIOS
            }
            request.session["canales_all"] = canales_dict
            request.session["canales_mios"] = canales_dictMIOS
            print(request.session["canales_mios"])
            datos = {
                "User": request.session.get("user"),
                "UserId": request.session.get("user_id"),
                "Chats": list(canales_no_mios.keys()),
                "Mios": list(canales_dictMIOS.keys()),
            }

            return render(request, "main.html", datos)

        else:
            # Mostrar error y pasar chats vacío
            print("Error:", chats["error"], chats.get("details"))
            return render(request, "main.html", {
                "User": request.session.get("user"),
                "UserId": request.session.get("user_id"),
                "Chats": [],
                "err": chats["error"]
            })

    else:
        # POST: redirigir a hilos
        flag = request.POST.get('new_chat')
        if flag == "1":
            return redirect("mod_chat")
        else:
            request.session["chat_actual"] = request.POST.get('chat')
            return redirect("hilos")

def mod_chat(request):
    user_id = request.session.get("user_id")  
    if not user_id:
        return redirect("home")  # si no hay sesión, redirige a login   
    if request.method == "GET":
        return render(request, "mod_chat.html",{'Chats':request.session["canales_mios"]})
    else:
        action = request.POST.get('action')
        if action == "create":
            resp = utils.CreateChat(request.POST.get('new_name'),request.POST.get('new_type'),request.session["user_id"])
            if not resp["success"]: return render(request, "mod_chat.html",{'Chats':request.session["canales_mios"], 'Err_create':resp["error"]})

        else:
            chat = request.POST.get('chat')
            chat_id = request.session["canales_mios"][chat][0]
            if action == "rename":
                resp = utils.ModifyChat(chat_id,request.POST.get('new_name'),request.POST.get('new_type'),request.session["user_id"])
                if not resp["success"]: return render(request, "mod_chat.html",{'Chats':request.session["canales_mios"], 'Err_mod':resp["error"]})
            elif action == "delete":
                resp = utils.DeleteChat(chat_id)
                if not resp["success"]: return render(request, "mod_chat.html",{'Chats':request.session["canales_mios"], 'Err_del':resp["error"]})
            elif action == "add_user":
                resp = utils.AddUserToChannel(chat_id, request.POST.get("user_id"))
                if not resp["success"]: return render(request, "mod_chat.html", {'Chats': request.session["canales_mios"], 'Err_add': resp["error"]})
            elif action == "remove_user":
                resp = utils.RemoveUserFromChannel(chat_id, request.POST.get("user_id"))
                if not resp["success"]: return render(request, "mod_chat.html", {'Chats': request.session["canales_mios"], 'Err_del_u': resp["error"]})
            else:
                return redirect("mod_chat")
        return redirect("main")        

def hilos(request):
    user_id = request.session.get("user_id")  
    if not user_id:
        return redirect("home")  # si no hay sesión, redirige a login   
    print("///////ID:",request.session["canales_all"][request.session["chat_actual"]][0])
    hilos = utils.GetHilos(str(request.session["canales_all"][request.session["chat_actual"]][0]).strip())
    print("----------HILOS: ",hilos)
    request.session["hilos_all"] = {
        c[1]: c[0]
        for c in hilos
    }
    print(request.session["hilos_all"])
    
    #Pedir los chats del usuario y crear los accesos a los mismos
    print("Voy a pasar al chat: ", request.session["chat_actual"])
    print("CNAAAAAAL:",request.session["chat_actual"])
    flag = False
    if request.session["chat_actual"] in list(request.session["canales_mios"].keys()):
        flag = True

    print("CANALES MIOS:",request.session["canales_mios"])
    datos = {"User":request.session["user"], "Chat":request.session["chat_actual"],"Hilos":request.session["hilos_all"],"Mio":flag}
    if request.method == "GET":
        print("Usuario ", request.session["user"])
        
        return render(request, "hilos.html",datos) 
    else:
        request.session["hilo_actual"] = request.POST.get('hilo')
        if request.POST.get('new_thread') == "1":
            return redirect("mod_hilos")
        return redirect("mensajes")  

def mod_hilos(request):
    user_id = request.session.get("user_id")  
    if not user_id:
        return redirect("home")  # si no hay sesión, redirige a login   
    if request.method == "GET":
        return render(request, "mod_hilo.html",{'Hilos':request.session["hilos_all"]})
    else:
        action = request.POST.get('action')
        if action == "create":
            flag, resp = utils.ManageHilo("create",
                        str(request.session["canales_all"][request.session["chat_actual"]][0]).strip(),
                        new_name=request.POST.get("new_name"))
            if not flag: return render(request, "mod_hilo.html",{'Chats':request.session["hilos_all"], 'Err_create':resp["error"]})

        else:
            hilo = request.POST.get('hilo')
            if action == "rename":
                flag, resp = utils.ManageHilo("rename",
                        str(request.session["canales_all"][request.session["chat_actual"]][0]).strip(),
                        uid=request.session["hilos_all"][hilo],
                        new_name=request.POST.get("new_name"))
                if not flag: return render(request, "mod_hilo.html",{'Hilos':request.session["hilos_all"], 'Err_mod':resp["error"]})
            elif action == "delete":
                flag, resp = utils.ManageHilo("delete",
                        str(request.session["canales_all"][request.session["chat_actual"]][0]).strip(),
                        uid=request.session["hilos_all"][hilo])
                if not flag: return render(request, "mod_hilo.html",{'Hilos':request.session["hilos_all"], 'Err_del':resp["error"]})
            else:
                return redirect("mod_chat")
        return redirect("main")  


"""
def mensajes(request):
    mensajes = [
        {"user": "Felipe", "texto": "Hola, ¿cómo estás?"},
        {"user": "Bot", "texto": "Todo bien, ¿y tú?"},
        {"user": "Felipe", "texto": "Probando el chat estilo frontend."},
    ]
    datos = {"User":request.session["user"], "Chat":request.session["chat_actual"],"Hilos":request.session["hilo_actual"],"mensajes":mensajes}
    if request.method == "GET":
        #print("Usuario ", request.session["user"])
        
        return render(request, "mensajes.html",datos) 
    else:
        #HACER INGRESO DEL MENSAJE EN PARALELO AL RETURN
        return render(request, "mensajes.html",datos)  
"""
def mensajes(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("home")

    user_name = request.session.get("user", "Desconocido")
    thread_id = str(request.session["hilos_all"][request.session["hilo_actual"]]).strip()

    if request.method == "POST":
        texto = request.POST.get("mensaje")
        archivos = request.FILES.getlist("archivos")
        print("---------OBTUVE LOS ARCHIVOS, cantidad: ", len(archivos))
        for f in archivos:
            #print("Revisio: ",f)
            print("-------------------Archivo:", f.name)
        if texto:
            api_response = utils.enviar_mensaje(thread_id, user_id, texto)
            if api_response is None:
                print(f"Error al enviar mensaje")
            else:
                mensaje_id = api_response.get("id")
                if len(archivos) > 0:
                    for f in archivos:
                        # Llama a la funcion de subida
                        resultado = utils.subir_archivo(
                            message_id=mensaje_id,
                            thread_id=thread_id,
                            archivo=f
                        )
                        # Manejo de la respuesta para logging / control
                        if resultado is None:
                            print(f"Error indeterminado subiendo {f.name}")
                        elif resultado.get("error"):
                            print(f"Error subiendo {f.name}: {resultado}")
                        else:
                            print(f"Archivo subido OK: {f.name} -> id: {resultado.get('id')}")
        return redirect("mensajes")

    # GET: obtener mensajes
    api_response = utils.obtener_mensajes(thread_id, limit=50)

    mensajes = []
    ids = []
    if api_response:
        mensajes_aux = []
        for item in api_response.get("items", []):
            fecha_dt = datetime.fromisoformat(item.get("created_at"))
            fecha_legible = fecha_dt.strftime("%d/%m/%Y %H:%M:%S")

            mensajes_aux.append({
                "user": item.get("user_id"),
                "texto": item.get("content"),
                "date": fecha_legible,
            })
            ids.append(item.get("id"))

        archivos, error = utils.GetArchivos(thread_id, ids)
        #print(archivos)
        for idx in range(len(ids)):
            flag = False
            # Caso error global
            if error:
                url = error
                flag = True

            else:
                # Caso mensaje SIN archivos
                if archivos[idx] is False:
                    url = False

                else:
                    # Caso mensaje CON archivos
                    flag = False
                    url = []
                    for j in range(len(archivos[idx])):
                        entry = archivos[idx][j]  # más claro

                        if "error" in entry:
                            url.append(entry["error"])
                        else:
                            url.append(entry.get("url")["url"])

            mensajes.append({
                "id":idx,
                "user": mensajes_aux[idx]["user"],
                "texto": mensajes_aux[idx]["texto"],
                "date": mensajes_aux[idx]["date"],
                "file": url,
                "Error": flag,
            })
            #print( mensajes_aux[idx]["texto"],url)


    mensajes.reverse()

    datos = {
        "User": user_name,
        "mensajes": mensajes,
        "current_user_id": user_id,
    }

    # ############### AJAX: SOLO retornar mensajes #################
    if request.GET.get("ajax") == "1":
        return render(request, "fragment_mensajes.html", datos)
    # ##############################################################

    return render(request, "mensajes.html", datos)

def chatsbots(request):
    user_id = request.session.get("user_id")  
    if not user_id:
        return redirect("home")  # si no hay sesión, redirige a login   
    opciones = [
        #("academico", "Chatbot Académico"),
        #("utilidad", "Chatbot Utilidad"),
        #("calculo", "Chatbot Cálculo"),
        ("wikipedia", "Chatbot Wikipedia"),
        ("programacion", "Chatbot Programación"),
    ]

    if request.method == "GET":
        # Enviar solo nombres bonitos
        return render(request, "chatsbots.html", {"chatsbots": opciones})

    # POST
    eleccion = request.POST.get("chat_bot")  # aquí llega academico / utilidad / ...

    return redirect("chatbot_view", tipo=eleccion)


def chatbot_view(request, tipo):
    user_id = request.session.get("user_id")  
    if not user_id:
        return redirect("home")  # si no hay sesión, redirige a login   
    historial = request.session.get(f"chat_{tipo}", [])

    if request.method == "POST":
        user_msg = request.POST.get("mensaje")
        historial.append({"sender": "user", "text": user_msg})

        respuesta = utils.API_CB(tipo, user_msg)
        historial.append({"sender": "bot", "text": respuesta})

        request.session[f"chat_{tipo}"] = historial

    return render(request, "chat_template.html", {
        "tipo": tipo.capitalize(),
        "historial": historial
    })

