# API Gateway

El borde del sistema se resuelve con **Kong** en modo estático (DB-less). Toda la configuración vive en `deployment/api-gateway/kong.yml` y se aplica vía `kubectl/argocd` usando el `kustomization` del mismo directorio.

## Rutas versionadas

| Grupo | Ruta base | Servicio Kubernetes | Estado |
|-------|-----------|---------------------|--------|
| 1: Usuarios | `/users` | `users-service` | Activo |
| 2: Canales | `/channels` | `channel-api-service` | Activo |
| 3: Hilos | `/threads` | `threads-service` | Activo |
| 4: Mensajes | `/messages` | `messages-service` | Activo |
| 5: Presencia | `/presence` | `presence-service` | Activo |
| 6: Moderación | `/moderation` | `moderation-service` | Activo |
| 7: Archivos | `/files` | `file-service-api` (ns: `file-service`) | Activo |
| 8: Búsqueda | `/search` | `search-service` | Activo |
| 9: Chatbot Académico | `/chatbot-academico` | `ia-chatbot-programacion` | Activo |
| 10: Chatbot Utilidad | `/chatbot-utilidad` | `chatbot-svc-api-gateway` | Activo |
| 11: Chatbot Cálculo | `/chatbot-calculo` | `api-gateway-service` (ns: `calculadora`) | Activo |
| 12: Chatbot Wikipedia | `/chatbot-wikipedia` | `wikipedia-chatbot-service` | Activo |
| 13: Chatbot Programación | `/chatbot-programming` | `chatbot-programming-service-svc` | Activo |
