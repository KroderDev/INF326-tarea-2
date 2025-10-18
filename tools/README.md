Herramienta de seed (desde la carpeta tools)

- Ejecuta estos comandos estando dentro de `tools/`.
- Crea un venv local `.venv-tools` y usa HTTP contra la API.

Carga por defecto

```
make seed
```

Carga media

```
make seed-medium
```

Carga alta

```
make seed-high
```

Carga extrema (estrés real)

```
make seed-extreme
```

Personalizado

```
make seed THREADS=12 MESSAGES=800 CONCURRENCY=200 BASE_URL=http://127.0.0.1:3000
```

Parámetros (por defecto)

```
BASE_URL=http://127.0.0.1:3000
THREADS=10
MESSAGES=500
USERS=10
CONCURRENCY=100
TIMEOUT=10
```

Consumir mensajes aleatoriamente

```
# Usa threads generados por el seed (seed_threads.json)
make consume

# Presets
make consume-medium
make consume-high
make consume-extreme

# Personalizado
make consume CONCURRENCY=80 TIMEOUT=10 BASE_URL=http://127.0.0.1:3000
```

Resumen al finalizar

- El seed imprime: base_url, configuración, elapsed, throughput, success/fail y distribución de códigos; además genera `seed_threads.json` con los threads y metadatos.
- El consumer imprime: reads, items totales recibidos, elapsed, throughput, success/fail y distribución de códigos.

Solución de problemas

```
# Permiso denegado al crear venv o venv corrupto
make seed-clean
make seed

# Forzar intérprete de Python específico (Windows)
make seed PY=py
make seed PY="C:\\Python312\\python.exe"
```
