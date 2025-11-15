# Proyecto INF326 - Messages Service

Servicio de mensajes para un sistema de chat desarrollado en Fast API y listo para ser desplegado en kubernetes.

### Diagrama del sistema
```mermaid
---
config:
  layout: elk
  look: neo
  theme: redux-dark
---
flowchart LR
 subgraph EDGE["Edge"]
        UI["Web/Mobile App"]
        APIGW["API Gateway (Kong)"]
  end
 subgraph MessagesService["Messages Service"]
        MSPod["Service"]
        MSRedis["Redis Cache"]
        MSPostgres["Postgres"]
  end
 subgraph Infra["Infra"]
        BUS["Event BUS"]
  end
    UI L_UI_APIGW_0@--> APIGW
    APIGW L_APIGW_MSPod_0@--> MSPod
    MSPod --- MSRedis & MSPostgres
    MSPod L_MSPod_BUS_0@-.-> BUS
    MSRedis@{ shape: cyl}
    MSPostgres@{ shape: cyl}
    style EDGE stroke:#FFFFFF
    linkStyle 0 stroke:#FFFFFF,fill:none
    linkStyle 1 stroke:#FFFFFF,fill:none
    linkStyle 2 stroke:#E1BEE7,fill:none
    linkStyle 3 stroke:#E1BEE7,fill:none
    linkStyle 4 stroke:#E1BEE7,fill:none
    L_UI_APIGW_0@{ animation: fast } 
    L_APIGW_MSPod_0@{ animation: fast } 
    L_MSPod_BUS_0@{ animation: slow }

```

## Servicio
- Codigo y documentacion en [`service/`](service/) (ver [`service/README.md`](service/README.md) para flujos, API y eventos).
- [`service/docker-compose.yml`](service/docker-compose.yml) y el [`service/Makefile`](service/Makefile) levantan Postgres, Redis, RabbitMQ y ejecutan pruebas de manera local.
- Los manifiestos listos para `kubectl` o Argo CD estan en [`deployment/messages-service/`](deployment/messages-service/).

## API Gateway
- Se implementó **Kong OSS** en modo DB-less para exponer cada ruta; la tabla completa de equipos y paths vive en [`docs/API Gateway.md`](docs/API%20Gateway.md).
- Los manifiestos listos para `kubectl` o Argo CD estan en [`deployment/api-gateway/`](deployment/api-gateway/).

## Interfaz
- Work in Progress.

## Tools
- [`tools/`](tools/) tiene scripts de benchmarking, ver [`tools/README.md`](tools/README.md).

## Integrantes

Grupo 4
- [Sebastián Richiardi](https://github.com/KroderDev) 202030555-2
- [Felipe Durán](https://github.com/Felipe-Duran-Alonso) 202160599-1