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
  end
 subgraph MessagesService["Messages Service"]
        MSPod["Service API"]
        MSRedis["Redis Cache"]
        MSPostgres["Postgres"]
  end
 subgraph Infra["Infra"]
        BUS["Event BUS"]
  end
 subgraph OtherServices["Other Services"]
        OSPod["Service API"]
        OSDatabase["Database/Cache"]
  end
 subgraph Cluster["Cluster"]
        APIGW["API Gateway (Kong)"]
        MessagesService
        Infra
        OtherServices
  end
    UI L_UI_APIGW_0@--> APIGW
    APIGW L_APIGW_MSPod_0@--> MSPod & OSPod
    MSPod L_MSPod_MSRedis_0@<--> MSRedis & MSPostgres
    MSPod L_MSPod_BUS_0@-.-> BUS
    OSPod L_OSPod_OSDatabase_0@<--> OSDatabase & BUS
    MSRedis@{ shape: db}
    MSPostgres@{ shape: db}
    OSDatabase@{ shape: db}
    style EDGE stroke:#FFFFFF
    style Cluster stroke:#BBDEFB
    linkStyle 0 stroke:#FFFFFF,fill:none
    linkStyle 1 stroke:#FFFFFF,fill:none
    linkStyle 3 stroke:#FFFFFF,fill:none
    linkStyle 4 stroke:#FFFFFF,fill:none
    linkStyle 5 stroke:#FFFFFF,fill:none
    L_UI_APIGW_0@{ animation: fast } 
    L_APIGW_MSPod_0@{ animation: fast } 
    L_APIGW_OSPod_0@{ animation: fast } 
    L_MSPod_MSRedis_0@{ animation: fast } 
    L_MSPod_MSPostgres_0@{ animation: slow } 
    L_MSPod_BUS_0@{ animation: slow } 
    L_OSPod_OSDatabase_0@{ animation: fast } 
    L_OSPod_BUS_0@{ animation: slow }

```

## Servicio
- Codigo y documentacion en [`service/`](service/) (ver [`service/README.md`](service/README.md) para flujos, API y eventos).
- [`service/docker-compose.yml`](service/docker-compose.yml) y el [`service/Makefile`](service/Makefile) levantan Postgres, Redis, RabbitMQ y ejecutan pruebas de manera local.
- Los manifiestos listos para `kubectl` o Argo CD estan en [`deployment/messages-service/`](deployment/messages-service/).

## API Gateway
- Se implementó **Kong OSS** en modo DB-less para exponer cada ruta; la tabla completa de equipos y paths vive en [`docs/API Gateway.md`](docs/API%20Gateway.md).
- Los manifiestos listos para `kubectl` o Argo CD estan en [`deployment/api-gateway/`](deployment/api-gateway/).

## Interfaz
- Se desarrollo con el framework django, el cual permitio desarrollo de back simple, para manejar generar las llamadas y filtrar algunos datos. Debido al uso de este framework, mencionar que se puede ejecutar localmente de la forma:

       python manage.py runserver



- Las credenciales empleadas para el testing:

  
       Usuario1: felipe.durana

       Clave1: Colocolo91

       Usuario2: felipe.duran

       Clave2: Colocolo

- Video demostrativo:
 
## Tools
- [`tools/`](tools/) tiene scripts de benchmarking, ver [`tools/README.md`](tools/README.md).

## Integrantes

Grupo 4
- [Sebastián Richiardi](https://github.com/KroderDev) 202030555-2
- [Felipe Durán](https://github.com/Felipe-Duran-Alonso) 202160599-1
