# API Gateway

El borde del sistema se resuelve con Kong en modo estatico (DB-less). Toda la configuracion vive en `deployment/api-gateway/kong.yml` y se aplica via `kubectl/argocd` usando el `kustomization` del mismo directorio.

Dominios publicos del gateway (aislados para group-04):
- https://api-group04.kroder.dev
- https://api-group04.inf326.nursoft.dev

Todas las llamadas externas deben salir por estos hostnames; la interfaz ya apunta al gateway en vez de usar URLs directas de cada microservicio.

## Rutas versionadas

| Grupo | Ruta base | Servicio Kubernetes | Estado |
|-------|-----------|---------------------|--------|
| 1: Usuarios | `/users` | `users-service` | Activo |
| 2: Canales | `/channels` | `channel-api-service` | Activo |
| 3: Hilos | `/threads` | `threads-service` | Activo |
| 4: Mensajes | `/messages` | `messages-service` | Activo |
| 5: Presencia | `/presence` | `presence-service` | Activo |
| 6: Moderacion | `/moderation` | `moderation-service` | Activo |
| 7: Archivos | `/files` | `file-service-api` (ns: `file-service`) | Activo |
| 8: Busqueda | `/search` | `search-service` | Activo |
| 9: Chatbot Academico | `/chatbot-academico` | `ia-chatbot-programacion` | Activo |
| 10: Chatbot Utilidad | `/chatbot-utilidad` | `chatbot-svc-api-gateway` | Activo |
| 11: Chatbot Calculo | `/chatbot-calculo` | `api-gateway-service` (ns: `calculadora`) | Activo |
| 12: Chatbot Wikipedia | `/chatbot-wikipedia` | `wikipedia-chatbot-service` | Activo |
| 13: Chatbot Programacion | `/chatbot-programming` | `chatbot-programming-service-svc` | Activo |
