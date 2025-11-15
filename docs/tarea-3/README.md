# Tarea Unidad 3 - Arquitectura de Software
## Descripción del problema
Se requiere implementar un sistema que permita el desarrollo de la comunidad universitaria a través de la **generación de grupos de mensajería**, una **aplicación de chat**.

## Contexto de negocio
- **Asistente de chat:** Chat personal, en el cual se podrán consultar preguntas frecuentes relacionadas a trámites, eventos, y tópicos relacionados con la universidad.
- **Añadir, modificar, recordatorios y eventos de calendario:** Se contará con un calendario académico, el cual contará con las fechas importantes de la institución pero también permite la manipulación del estudiante.
- **Canales de difusión:**
  - **Canales temáticos** que permitirán conectar estudiantes relacionados al tópico.
  - **Avisos:** Difusión masiva de manera nativa, con alcance variable según privilegios.
  - **Grupos oficiales:** Encuentra grupos oficiales de ramos y carreras creados por autoridades.
  - **Descubrimiento de comunidades:** Encuentra grupos y comunidades dentro de la universidad más allá de grupos de los oficiales.

## Lenguaje ubicuo
- **Estudiante:** Persona inscrita en algún plan de estudios de la universidad.
- **Profesores:** Persona que imparte clases en la universidad.
- **Centro de alumnos:** Estudiantes de la universidad que son parte del centro de alumnos vigente.
- **Federación estudiantil:** Organización de estudiantes que son parte de la federación del campus respectivo.
- **Campus:** Sede a la que pertenece el estudiante, centro de alumnos y federación estudiantil. Los profesores podrían llegar a ser parte de dos campus.
- **Carrera:** Plan de estudios en el que son parte Estudiantes y Profesores.
- **Curso:** Asignatura que se imparte en la universidad.
- **Administrativo:** Persona que trabaja en la universidad en labores administrativas.
- **Comunidad:** Grupo de estudiantes que siguen una temática en común.
- **Curso:** Asignatura que se imparte en la universidad.
- **Aviso:** Mensaje de difusión emitido por una sola autoridad a un grupo de estudiantes.
- **Afinidad:** Grado de coincidencia entre intereses.
- **Faceta:** Conteo por atributo para filtrar resultados (tag, campus, visibilidad).

## Módulos

- [Autenticación de usuario](./Auth.md)
- [Descubrimiento de comunidades](./Discovery.md)
- [Comunidades](./Comunidades.md)
- [Calendario (Externo)](./Calendar.md)
- [Asistente](./Asistente.md)
- [Automatización](./Automatización.md)
- [Chat](./Chat.md)
- [Avisos](./Avisos.md)
## Diagrama de arquitectura general

### Vista rápida

```mermaid
---
config:
  look: classic
  theme: neutral
---
flowchart LR
  APP[Clientes]
  APIGW[API Gateway]
  AUTH[Auth]
  CHAT[Chat]
  AST[Asistente]
  AUTO[Automatización]
  COMM[Comunidades]
  DISC[Discovery]
  CAL[Calendario]
  ADV[Avisos]
  BUS[[Event Bus]]

  APP --> APIGW
  APIGW --> AUTH
  APIGW --> CHAT
  APIGW --> AST
  APIGW --> AUTO
  APIGW --> COMM
  APIGW --> DISC
  APIGW --> CAL
  APIGW --> ADV

  CHAT <--> AST
  AST <---> BUS <---> AUTO
  AUTO <---> CAL
  COMM --> BUS --> DISC
  ADV --> BUS --> AST
  APP -. JWT .-> APIGW
```


> [!NOTE]
> Para ver cada módulo en detalle, revisa su documento específico. [aquí](#módulos)

---

### Diagrama "casi" completo
```mermaid
---
config:
  look: classic
  theme: redux-dark-colors
---
flowchart LR
  classDef outOfScope stroke-dasharray: 5 5,opacity:0.7

  subgraph Clients
    APP[App Web/Móvil]
  end

  subgraph Shared Edge
    APIGW[API Gateway\nAuth, Rate limit, Routing]
  end

  subgraph Identity
    AUTH[Auth Service/API]
    JW[(JWKS Cache)]
    RBAC[(Roles/Permisos)]
    IDP[Microsoft Entra ID]
  end

  subgraph Chat
    CHAT[Chat Service]
    CHIST[(Histórico mensajes)]
    CCACHE[(Cache mensajes recientes)]
  end

  subgraph Assistant
    AING[Ingress]
    ACLF[Classifier]
    ACTX[(Context Store)]
  end

  subgraph Automation
    ORCH[Run Orchestrator]
    WORK[Worker Pool]
    FLOWS[(Flow Registry)]
    STATE[(Run State)]
    SCH[Scheduler]
  end

  subgraph Calendar
    CALBFF[Calendar API BFF]
    CALAPI[Calendar Integration API]
    CMAP[(User-Provider Map)]
    CTOK[(Token Store)]
    ADP1[Adapter Google]
    ADP2[Adapter Microsoft]
    ADP3[Adapter CalDAV]
  end

  subgraph Discovery
    DBFF[Discovery API BFF]
    SAPI[Search API]
    IDX[(Search Index)]
    RANK[Ranking]
  end

  subgraph Communities
    CAT[Community Catalog]
    MEM[Membership]
    ACT[Activity]
    CAPI[Communities API]
  end

  subgraph Avisos
    REC[Receiver]
    TRA[Transmitter]
    AHIST[(Avisos Store)]
    ACACHE[(Recent Avisos)]
  end

  subgraph Infra
    BUS[[Event Bus]]
  end

  %% Cliente y shared edge
  APP -->|HTTPS| APIGW
  APIGW -->|/chat/*| CHAT
  APIGW -->|/discovery/*| DBFF
  APIGW -->|/communities/*| CAPI
  APIGW -->|/calendar/*| CALBFF
  APIGW -->|/avisos/*| REC
  APIGW -->|/auth/*| AUTH

  %% Auth
  AUTH -->|authorize/loginC| IDP
  AUTH -->|tokens id/access| APP
  APIGW -->|obtener JWKS| AUTH
  AUTH --> JW
  AUTH --- RBAC
  class IDP outOfScope

  %% Chat <-> Assistant
  CHAT -- ChatMessageReceived --> AING
  AING --> ACLF --> ACTX
  ACLF -- AssistantCommandIssued --> BUS
  BUS -- FlowOutputProduced --> AING
  AING -- ChatSendRequest --> CHAT
  CHAT -. membership/visibility .-> MEM

  %% Automatización (orquestación)
  BUS --> ORCH
  SCH --> ORCH
  ORCH --> WORK
  WORK --> STATE
  ORCH --> STATE
  WORK -- FlowOutputProduced --> BUS

  %% Calendar (integraciones externas)
  CALBFF --> CALAPI
  WORK -- CalendarCommand* --> CALAPI
  CALAPI -- CalendarEvent* --> BUS
  CALAPI --- CMAP
  CALAPI --- CTOK
  CALAPI --> ADP1
  CALAPI --> ADP2
  CALAPI --> ADP3
  class ADP1,ADP2,ADP3 outOfScope

  %% Discovery (búsqueda e indexación)
  DBFF --> SAPI
  SAPI --> IDX
  RANK --> IDX
  CAT -- Community* --> BUS
  MEM -- Membership* --> BUS
  ACT -- Activity* --> BUS
  BUS -->|consume| SAPI
  SAPI -->|update index| IDX

  %% Avisos
  REC --> AHIST
  REC --> ACACHE
  TRA --> ACACHE
  APIGW --> TRA
  TRA -- AssistantQueue --> BUS
  BUS --> CHAT

  %% Autorización transversal via JWT en APIGW
  APP -. Authorization: Bearer .-> APIGW
```

> [!NOTE]
> El diagrama muestra flujos principales entre módulos: Auth, Chat, Asistente, Automatización, Calendario, Comunidades, Descubrimiento y Avisos, junto al Event Bus y el API Gateway.
> Componentes externos (IdP y proveedores de calendario) se marcan como fuera de alcance.
