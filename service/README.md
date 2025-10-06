# Proyecto Arquitectura de Software

## Microservicio: Mensajes

### Flujo del microservicio

```mermaid
---
config:
  layout: elk
  look: classic
  theme: neo-dark
---
flowchart LR
 subgraph s1["Message Service"]
        n1["Controller"]
        n3["Redis Cache"]
        n5["Postgres"]
  end
 subgraph s2["Edge"]
        n6["API"]
  end
 subgraph s3["User Service"]
        n7["API"]
  end
 subgraph s4["Infra"]
        n8["Event BUS"]
  end
    s2 L_s2_n1_0@--> n1
    n1 --> n5 & n3 & n7 & n8
    n3@{ shape: db}
    n5@{ shape: db}
    L_s2_n1_0@{ animation: slow } 
    L_n1_n7_0@{ animation: slow } 
    L_n1_n8_0@{ animation: slow }
```

---

### API

**POST _/message/{thread_id}/{user_id}/{content}_**
- thread_id: identificador unico del hilo.
- user_id: identificador unico del usuario que registra el mensaje.
- content: Contenido a insertar dentro del mensaje.
- typeM_(Se pasa como opcional)_: Lista con los tipos de mensajes que tiene (archivo, mensaje de voz, etc.).
- path_(Se pasa como opcional)_: Lista con las rutas de todos los archivos insertados en el mensaje.
>Ej de llamada:
    POST /message/1/42?typeM=text?path=dir/archivo_texto

**PUT _/message/{thread_id}/{message_id}/{user_id}/{content}_**
- thread_id: identificador unico del hilo.
- user_id: identificador unico del usuario que registra el mensaje.
- message_id: identificador unico del mensaje a modificar.
- content: Contenido a insertar dentro del mensaje.
- typeM_(Se pasa como opcional)_: Lista con los tipos de mensajes que tiene (archivo, mensaje de voz, etc.).
- path_(Se pasa como opcional)_: Lista con las rutas de todos los archivos insertados en el mensaje.
>Ej de llamada:
    PUT /message/1/5/42?typeM=text?path=dir/archivo_texto


**DELETE _/message/{thread_id}/{message_id}/{user_id}_**
- thread_id: identificador unico del hilo.
- user_id: identificador unico del usuario que registra el mensaje.
- message_id: identificador unico del mensaje a modificar.
>Ej de llamada:
    DELETE /message/1/5/42

**GET _/message/{thread_id}_**
- thread_id: identificador unico del hilo.
- typeM_(Se pasa como opcional)_: Valor del tipo del filtrado, -1 segun fecha y 1 segun cantidad de mensajes.
- filtro_(Se pasa como opcional)_: Valor donde realiza el corte la obtencion, podrian ser X mensajes o desde Y fecha.
>Ej de llamada:
    GET /message/1/?typeM=1?filtro=18-01-2025
---

### Eventos

Nuevo mensaje

---

