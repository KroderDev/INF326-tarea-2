# Módulo: Automatización

## Diagrama arquitectura
```mermaid
---
config:
  look: classic
  theme: redux-dark-color
---
flowchart LR
  subgraph Bus
    EV[[Event Bus]]
  end

  subgraph Automation
    ING[Event Ingest]
    TR[Trigger Router]
    ORC[Run Orchestrator]
    WRK[Worker Pool]
    SCH[Scheduler]
    REG[(Flow Registry)]
    ST[(Run State Store)]
  end

  subgraph External
    CAL[Calendar Service]
    OTHER[Other Services]
    CHAT[Chat Service]
  end

  EV --> ING --> TR --> ORC
  SCH --> ORC
  ORC --> WRK
  WRK --> ST
  ORC --> ST
  WRK -- FlowOutputProduced --> EV
  WRK -- Calls --> CAL
  WRK -- Calls --> OTHER
  EV --> CHAT
```

---

## Requerimientos

- Registrar y versionar definiciones de flujos (triggers, condiciones, pasos, plantillas de salida).
- Disparar flujos por eventos (p. ej., `AssistantCommandIssued`), por cron y por API manual.
- Orquestar pasos con reintentos exponenciales, idempotencia por `step_id`, y compensaciones opcionales.
- Mantener estado de ejecución consultable (`flow_run_id`, historial de steps, errores, tiempos).
- Integrarse con servicios internos (Calendar, Discovery, Avisos) y producir salidas para Asistente/Chat.
- Seguridad: ejecutar “en nombre de” del usuario cuando aplique (delegación/OBO) o con credenciales de servicio.

---

## Secuencia típica (mensaje → evento de calendario → respuesta)

```mermaid
---
config:
  look: classic
  theme: redux-dark-color
---
sequenceDiagram
  participant Chat as Chat Service
  participant Asst as Assistant
  participant Auto as Automation
  participant Cal as Calendar Service

  Chat->>Asst: ChatMessageReceived (m-123)
  Asst->>Asst: Clasificar (intent calendar.create_event)
  Asst->>Auto: AssistantCommandIssued (m-123, intent, entities)
  Auto->>Auto: FlowRunStarted
  Auto->>Cal: CreateEvent(...)
  Cal-->>Auto: 200 OK (event_id)
  Auto->>Asst: FlowOutputProduced (render text)
  Asst->>Chat: ChatSendRequest ("Listo, cree el evento...")
  Chat-->>Usuario: mensaje de respuesta
```

---

## Listado de puntos de comunicación

### Eventos (Pub/Sub)

- Disparar flujos por intención del asistente: `AssistantCommandIssued` (desde Asistente) — trigger por `intent`.
- Ejecutar trabajos programados: Cron del Scheduler (interno) → `FlowRunStarted`.
- Emitir resultados para el Asistente: `FlowOutputProduced` (payload renderizable por Chat).
- Integración con Calendar (ver módulo Calendar):
  - Comandos: `CalendarCommand.ScheduleEvent`, `CalendarCommand.UpdateEvent`, `CalendarCommand.CancelEvent`.
  - Eventos: `CalendarEvent.Created`, `CalendarEvent.Updated`, `CalendarEvent.Canceled`, `CalendarEvent.CreateFailed`.
- Integración con Discovery (ver módulo Discovery):
  - Paso invoca Search API/BFF sincrónicamente; opcionalmente se cachea el topN.

### HTTP/RPC (sincrónico)

- `POST /automation/flows` — registrar/actualizar definición de flujo (admin).
- `GET /automation/flows/{id}` — obtener definición de flujo.
- `POST /automation/flows/{id}/run` — disparar manualmente un flujo (debug/manual).
- `GET /automation/runs/{runId}` — estado de ejecución.
