# Módulo: Calendario (Externos)
## Diagrama arquitectura
```mermaid
---
config:
  look: classic
  theme: redux-dark
---
flowchart LR
  classDef outOfScope stroke-dasharray: 5 5,opacity:0.7
  subgraph Clients
    APP[App Web/Movil]
  end

  subgraph Shared Edge
    APIGW[API Gateway auth, rate limit, routing]
  end

  subgraph Calendar Edge
    BFF[Calendar API BFF]
  end

  subgraph Calendar
    CALAPI[Calendar Integration API]
    MAP[(User-Provider Map)]
    TOK[(Token Store)]
    ADP1[Adapter Google]
    ADP2[Adapter Microsoft]
    ADP3[Adapter iOS/CalDAV]
    WEBH[Webhook Receiver]
  end

  subgraph Automation
    AUTO[Automatizacion]
  end

  subgraph Infra
    BUS[[Event Bus]]
  end

  %% Cliente
  APP -->|HTTPS| APIGW
  APIGW -->|/calendar/*| BFF
  BFF --> CALAPI

  %% Automatizacion por colas
  AUTO -->|CalendarCommand*| BUS --> CALAPI
  CALAPI -->|CalendarEvent*| BUS --> AUTO

  %% Proveedores
  CALAPI --> ADP1
  CALAPI --> ADP2
  CALAPI --> ADP3
  ADP1 --> WEBH
  ADP2 --> WEBH
  ADP3 --> WEBH
  WEBH --> CALAPI

  %% Estado minimo
  CALAPI --- MAP
  CALAPI --- TOK

  class APIGW outOfScope
  class WEBH outOfScope
```

## Requerimientos

- Vincular cuentas vía OAuth/OIDC (Google, Microsoft, CalDAV); guardar vínculo por usuario/proveedor.
- Crear, actualizar y cancelar eventos por HTTP y vía comandos asíncronos; idempotencia con `Idempotency-Key`.
- Listar/consultar eventos por rango y zona horaria; copia de eventos del calendario académico al personal.
- Integrarse con Asistente/Avisos/Chats/Comunidades.

## Listado de puntos de comunicación

### HTTP (sincrónico)
- Iniciar vínculo con Google/Microsoft/iOS (consent OAuth/OIDC; una vez por usuario/proveedor): `GET /calendar/connect?provider={p}`
- Cerrar OAuth y guardar token del usuario: `GET /calendar/callback`
- Crear evento externo “en nombre del usuario” (idempotente por `Idempotency-Key`): `POST /calendar/events`
- Recibir notificaciones del proveedor (lista conocida de orígenes): `POST /{provider}/webhook`

### Eventos (Pub/Sub)
- Crear evento disparado por flujos del Asistente: Evento `CalendarCommand.ScheduleEvent`
- Confirmación de creación exitosa: Evento `CalendarEvent.Created`
- Notificación de falla al crear: Evento `CalendarEvent.CreateFailed`
