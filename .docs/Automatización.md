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

- Disparar flujos por intención del asistente: Evento AssistantCommandIssued (del - Asistente) — trigger cuando `assistant.intent == ...`
- Ejecutar trabajos programados: Cron en Scheduler (interno)
