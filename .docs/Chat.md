# Módulo: Asistente

## Diagrama arquitectura

```mermaid
---
config:
  look: classic
  theme: redux-dark
---
flowchart LR
  subgraph Clients
    APP[App Web/Movil]
  end
  subgraph Edge
    ACC[Chat access]  
    MAN[Chat management]
  end
  subgraph Data
    ACM[Access chat manager]
    HIST[(Historic chat)]
    CACHE[(Cache)]    
    BUS[[Hight access chat ]]
  end
  ASS[[Assistant bus ]] 
  APP -->|Change value calls| MAN
  APP -->|Message access or delivery| ACC
  MAN -->|Values| HIST
  ACC -->|Message access or delivery| ACM
  ACM -->|Extract or enter| HIST
  ACM -->|Extract or enter| BUS
  ACM -->|Extract or enter| CACHE
  ACM -->|Enter| ASS
```

---

## Requerimientos

-Registrar nuevo chat y eliminarlo cuando se estime necesario.
-Agregar manualmente a estudiantes al chat, así como también eliminarlos. En caso de ser un usuario autorizado para esto.
-Unirse o solicitar unirse a canales de difusión públicos o privados.
-Enviar mensajes al chat que el integrante desee.
-Ver mensajes históricos del chat que se consulte.
-Generar mensajes persistentes dentro del chat con el fin de mostrarlo de forma constante (en caso de tener permisos para ello). Así como también eliminarlos si fuera necesario.
-Editar descripción del chat.
-Enviar un mensaje puntual del chat hacia el módulo de asistente.


---

## Listado de puntos de comunicación

### Eventos (Pub/Sub)

- Enviar mensaje del chat al módulo de asistente: `AssistantQueue`
