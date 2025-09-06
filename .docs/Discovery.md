# Módulo: Descubrimiento de comunidades

## Requerimientos

* Buscar comunidades por texto, tags, campus, visibilidad y rango de tamaño.
* Ordenar por actividad reciente, crecimiento de miembros, relevancia semántica y verificación.
* Mostrar facetas (counts por tag/campus/visibilidad).
* Endpoint para “Descubrir para mí”: usa datos del usuario como campus, carrera y tags de interés.
* Auditoría básica de búsquedas (para métricas de producto).

## Diagrama de arquitectura

```mermaid
---
config:
  look: classic
  theme: redux-dark
---
flowchart LR
  classDef outOfScope stroke-dasharray: 5 5,opacity:0.7
  subgraph Clients
    A[App Web/Movil]
  end
  subgraph Shared Edge
    APIGW[API Gateway auth, rate limit, routing]
  end
  subgraph Edge Discovery
    BFF[Discovery API BFF]
  end
  subgraph Search
    SAPI[Search API / Worker]
    IDX[(Search Index)]
    RANK[Ranking Service]
    CACHE[( Cache)]
  end
  subgraph Core
    CAT[Community Catalog]
    MEM[Membership]
    ACT[Activity Stream]
  end
  subgraph Infra
    BUS[[Event Bus]]
  end

  A -->|HTTPS| APIGW
  APIGW -->|/discovery/*| BFF
  BFF -->|query| SAPI
  SAPI --> IDX
  BFF --> CACHE
  RANK --> CACHE
  CAT -->|CommunityCreated/Updated| BUS
  MEM -->|MembershipAdded/Removed| BUS
  ACT -->|CommunityActivityWindowAggregated| BUS
  BUS -->|consume events| SAPI
  SAPI -->|update index| IDX
  RANK -->|periodic compute| IDX

  class APIGW outOfScope

```

## Diagrama de flujo de indexación

```mermaid
---
config:
  theme: redux-dark-color
  look: classic
---
sequenceDiagram
  participant CAT as Community Catalog
  participant MEM as Membership
  participant ACT as Activity
  participant BUS as Event Bus
  participant WRK as Indexer Worker
  participant IDX as Search Index
  CAT->>BUS: CommunityCreated/Updated (Outbox)
  MEM->>BUS: MembershipAdded/Removed/CountUpdated (Outbox)
  ACT->>BUS: CommunityActivityWindowAggregated
  BUS-->>WRK: eventos (at-least-once)
  WRK->>IDX: upsert document (community_id)
  WRK-->>WRK: backoff/idempotencia
```

## Diagrama de flujo de búsqueda

```mermaid
---
config:
  theme: redux-dark-color
  look: classic
---
sequenceDiagram
  participant APP as Cliente
  participant BFF as Discovery API
  participant SAPI as Search API
  participant IDX as Search Index
  participant CACHE as Cache
  APP->>BFF: GET /discovery/search?q=&tags=&campus=
  BFF->>CACHE: GET topN
  alt cache hit
    CACHE-->>BFF: resultados
  else cache miss
    BFF->>SAPI: query + filtros + ordenamiento
    SAPI->>IDX: search + aggregations
    IDX-->>SAPI: hits + facetas
    SAPI-->>BFF: resultados
    BFF->>CACHE: set (TTL)
  end
  BFF-->>APP: 200 OK (paginado)
```

## Listado de puntos de comunicación

### Sincrónicos (HTTP/RPC)

#### Discovery API
- Buscar comunidades con filtros y orden: `GET /discovery/search`
- Obtener facetas (counts por tag/campus/visibilidad): `GET /discovery/facets`

#### Search API
- Ejecutar consulta al índice de búsqueda: `POST /search/query`
- Reindexar manualmente una comunidad: `POST /search/reindex/{community_id}`

#### Community Catalog
- Crear una comunidad: `POST /communities`
- Actualizar parcialmente una comunidad: `PATCH /communities/{id}`
- Obtener detalles de una comunidad: `GET /communities/{id}`

#### Membership
- Agregar miembro a una comunidad: `POST /communities/{id}/members`
- Eliminar miembro de una comunidad: `DELETE /communities/{id}/members/{userId}`
- Obtener conteo de miembros de una comunidad: `GET /communities/{id}/members/count`

### Asincrónicos (Eventos Pub/Sub)

- Notificar creación de comunidad: `Evento Community.Created`
- Notificar actualización de comunidad: `Evento Community.Updated`
- Notificar archivado de comunidad: `Evento Community.Archived`
- Notificar alta de miembro: `Evento Membership.Added`
- Notificar baja de miembro: `Evento Membership.Removed`
- Notificar actualización del conteo de miembros: `Evento Community.MemberCountUpdated`
- Publicar agregación de actividad reciente: `Evento CommunityActivity.WindowAggregated`

### Suscriptores
- Mantener el índice de búsqueda actualizado: `Indexer Worker` a `Community*`, `Membership*`, `CommunityActivity.WindowAggregated`
