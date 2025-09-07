# Módulo: Comunidades

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
    APP[App Web/Móvil]
  end

  subgraph Shared Edge
    APIGW[API Gateway auth, rate limit, routing]
  end

  subgraph Edge Communities
    BFF[Communities API]
  end

  subgraph Core
    CAT[Community Catalog]
    MEM[Membership Service]
    ACT[Activity Aggregator]
  end

  subgraph Infra
    BUS[[Event Bus]]
  end

  subgraph Integrations
    DISC[Discovery Indexer]
    CHAT[Chat Service]
    AUTO[Automatización]
  end

  APP -->|HTTPS| APIGW -->|/communities/*| BFF
  BFF --> CAT
  BFF --> MEM
  ACT --> BUS
  CAT -- Community* --> BUS
  MEM -- Membership* --> BUS
  BUS -->|consume| DISC
  BUS -->|consume| AUTO
  CHAT -. consulta membresía .-> MEM

  class DISC outOfScope
  class AUTO outOfScope
  class CHAT outOfScope
  class APIGW outOfScope
```

---

## Requerimientos

- Gestionar el ciclo de vida de comunidades: crear, actualizar, archivar/eliminar, verificación y visibilidad (pública/privada/oficial).
- Modelo de membresía con roles: owner, moderador, miembro; solicitudes de ingreso, aprobación/rechazo, expulsión, abandono.
- Políticas de acceso por campus/carrera/rol institucional; soporte a comunidades oficiales y temáticas.
- Actividad: agregar y consolidar señales de actividad (mensajes, publicaciones, crecimiento de miembros) para ranking/descubrimiento.
- Emitir eventos de dominio para mantener actualizado el índice de Discovery y sincronizar accesos de Chat.
- Auditoría básica: quién creó/archivó/aceptó solicitudes; timestamps e IP opcional.
- Integrarse con Auth para autorización RBAC y claims de usuario (campus/carrera/roles).

---

## Diagramas de flujo

### Solicitud de ingreso y acceso al Chat

```mermaid
---
config:
  look: classic
  theme: redux-dark-color
---
sequenceDiagram
  participant APP as Cliente
  participant BFF as Communities API
  participant MEM as Membership
  participant CHAT as Chat Service
  participant BUS as Event Bus

  opt Solicitud de ingreso
    APP->>BFF: POST /communities/{id}/join
    BFF->>MEM: create PendingMembership(user,id)
    MEM-->>APP: 202 Accepted
    MEM->>BUS: Membership.PendingCreated
  end

  opt Aprobación y acceso al chat
    APP->>BFF: POST /communities/{id}/members/{user}/approve
    BFF->>MEM: set status=Active
    MEM->>BUS: Membership.Added
    BUS-->>CHAT: Membership.Added (suscriptor)
    CHAT->>CHAT: habilita acceso al chat comunitario
  end
```

### Actualización de metadatos y reindexación

```mermaid
---
config:
  look: classic
  theme: redux-dark-color
---
sequenceDiagram
  participant APP as Cliente
  participant BFF as Communities API
  participant CAT as Community Catalog
  participant BUS as Event Bus
  participant DISC as Discovery Indexer
  APP->>BFF: PATCH /communities/{id} (tags, descripción)
  BFF->>CAT: update
  CAT->>BUS: Community.Updated
  BUS-->>DISC: consumir evento
  DISC->>DISC: upsert en índice
```

---

## Listado de puntos de comunicación

### Sincrónicos (HTTP/RPC)

#### Communities API
- Crear comunidad: `POST /communities`
- Actualizar parcialmente comunidad: `PATCH /communities/{id}`
- Archivar/Eliminar comunidad: `DELETE /communities/{id}`
- Obtener detalles: `GET /communities/{id}`
- Listar mis comunidades: `GET /me/communities`

#### Membership
- Solicitar unirse: `POST /communities/{id}/join`
- Aprobar solicitud: `POST /communities/{id}/members/{userId}/approve`
- Rechazar solicitud: `POST /communities/{id}/members/{userId}/reject`
- Expulsar miembro: `DELETE /communities/{id}/members/{userId}`
- Abandonar comunidad: `DELETE /communities/{id}/members/me`
- Obtener conteo de miembros: `GET /communities/{id}/members/count`

### Asincrónicos (Eventos Pub/Sub)

- `Community.Created`, `Community.Updated`, `Community.Archived`
- `Membership.Added`, `Membership.Removed`, `Community.MemberCountUpdated`
- `CommunityActivity.WindowAggregated`

### Suscriptores

- Discovery Indexer: mantiene índice actualizado a partir de `Community*`, `Membership*`, `CommunityActivity.*`.
- Chat Service: aplica accesos/visibilidad según `Membership.*` y `Community.*`.
- Automatización: puede reaccionar a eventos para flujos de bienvenida/moderación.

---

## Notas de seguridad y datos

- Autorización basada en roles y ownership: sólo owners/moderadores pueden moderar y editar; miembros sólo lectura.
- Validación de visibilidad: comunidades privadas no aparecen en Discovery salvo invitación/miembros.
- Minimización de datos personales: ID de usuario y atributos mínimos (campus/carrera) para reglas.

