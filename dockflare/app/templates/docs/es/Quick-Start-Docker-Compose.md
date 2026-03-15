# Inicio rápido (Docker Compose)

Esta guía explica la forma más rápida de ejecutar DockFlare con el socket proxy reforzado y la configuración rootless del Master.

### 1. Cree el archivo `docker-compose.yml`

La siguiente pila inicia Docker-socket-proxy, prepara el volumen persistente con la propiedad correcta e inicia DockFlare junto con Redis.

```yaml
version: '3.8'
services:
  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:v0.4.1
    container_name: docker-socket-proxy
    restart: unless-stopped
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
      - CONTAINERS=1
      - EVENTS=1
      - NETWORKS=1
      - IMAGES=1
      - POST=1
      - PING=1
      - INFO=1
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal

  dockflare-init:
    image: alpine:3.20
    command: ["sh", "-c", "chown -R 65532:65532 /app/data"]
    volumes:
      - dockflare_data:/app/data
    networks:
      - dockflare-internal
    restart: "no"

  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - dockflare_data:/app/data
    environment:
      - REDIS_URL=redis://redis:6379/0
      - REDIS_DB_INDEX=0  # Optional: specify Redis database index (0-15) for isolation from other containers
      - DOCKER_HOST=tcp://docker-socket-proxy:2375
    depends_on:
      docker-socket-proxy:
        condition: service_started
      dockflare-init:
        condition: service_completed_successfully
      redis:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

  redis:
    image: redis:7-alpine
    container_name: dockflare-redis
    restart: unless-stopped
    command: ["redis-server", "--save", "", "--appendonly", "no"]
    volumes:
      - dockflare_redis:/data
    networks:
      - dockflare-internal

volumes:
  dockflare_data:
  dockflare_redis:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```

**Notas:**
- El contenedor Master se ejecuta como el usuario `dockflare` (UID/GID 65532). Si necesita hacer coincidir diferentes permisos de host, configure `DOCKFLARE_UID`/`DOCKFLARE_GID` y reconstruya la imagen o ajuste el init job.
- El proxy es obligatorio. DockFlare nunca monta `/var/run/docker.sock` directamente, lo que limita la superficie de la API de Docker a la que puede acceder el Master.
- Cuando utilice montajes vinculados en lugar de volúmenes con nombre, asegúrese de que se pueda escribir en el directorio de destino mediante UID/GID 65532 (o sus valores anulados).
- Crear la red externa una vez si no existe: `docker network create cloudflare-net`.

### 2. Ejecute DockFlare

Inicie la pila en modo independiente:

```bash
docker compose up -d
```

Esto abre el proxy, prepara el volumen e inicia DockFlare junto con Redis.

### 3. Complete la configuración previa al vuelo

Una vez que los servicios se estén ejecutando, abra su navegador en `http://<your-server-ip>:5000`.

El **asistente de configuración inicial** le guiará a través de:
1. Crear una contraseña para la interfaz web.
2. Ingresando sus credenciales de Cloudflare (ID de cuenta, ID de zona, token API).
3. Configurar su túnel Cloudflare inicial.
4. *(Opcional)* Restauración desde un archivo de copia de seguridad de DockFlare. Si ya tiene un `dockflare_backup_*.zip`, elija **Restaurar desde copia de seguridad** antes del Paso 1; el asistente importa su configuración y reinicia el contenedor automáticamente.

### 4. Para usuarios existentes (actualización)

Si está actualizando desde una versión anterior, DockFlare detecta el archivo `.env` heredado, migra su configuración al almacén cifrado y lo guía a través de la creación de contraseñas. Mantenga el proxy de socket en su lugar; ya no se admiten montajes directos de `/var/run/docker.sock`.
