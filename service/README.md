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

---

### Eventos

Nuevo mensaje

---

