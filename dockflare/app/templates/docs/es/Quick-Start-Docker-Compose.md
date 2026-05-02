# Inicio rápido (Docker Compose)

Esta guía explica la forma más rápida de ejecutar DockFlare con el socket proxy reforzado y la configuración rootless del Master.

## Opción A — Instalación en un solo comando (Recomendado)

La forma más rápida de poner en marcha DockFlare es el script de instalación interactivo alojado en [dockflare.app](https://dockflare.app):

```bash
bash <(curl -fsSL https://dockflare.app/install.sh)
```

El script le guiará a través de:
1. Elección del directorio de instalación (predeterminado: `~/dockflare/`).
2. Elección del puerto local de la interfaz (predeterminado: `5000`).
3. Configuración opcional de un túnel de Cloudflare para DockFlare.
4. Activación opcional del perfil de correo electrónico (dockflare-mail-manager + dockflare-webmail).

A continuación, escribe el archivo `docker-compose.yml`, permite revisarlo y pregunta antes de iniciar el stack.

Una vez en ejecución, abra `http://<your-server-ip>:5000` y complete el asistente de configuración.

---

## Opción B — Docker Compose manual

### 1. Cree el archivo `docker-compose.yml`

La siguiente pila inicia Docker-socket-proxy, prepara el volumen persistente con la propiedad correcta e inicia DockFlare junto con Redis.

```yaml
services:
  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:v0.4.1
    container_name: docker-socket-proxy
    restart: unless-stopped
    logging:
      driver: "none"
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
    command: ["sh", "-c", "chown -R ${DOCKFLARE_UID:-65532}:${DOCKFLARE_GID:-65532} /app/data"]
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
      - "5000:5000" # Optional: comment out once exposed via Cloudflare Tunnel with an Access Policy to restrict access to tunnel-only
    #labels: # -- Cloudflare Tunnel Configuration (via DockFlare) OPTIONAL --
      # Main DockFlare with access policy
      #- dockflare.enable=true
      #- dockflare.hostname=dockflare.TLD  # replace with your domain
      #- dockflare.service=http://dockflare:5000
      #- dockflare.access.group=YOUR-ACCESS-GROUP-ID  # your custom access policy
      # -- OAuth Callback Path (Bypass Access Policy) OPTIONAL --
      # Required if using OAuth authentication with access policies on main interface
      #- dockflare.0.hostname=dockflare.example.tld
      #- dockflare.0.path=/auth/google/callback
      #- dockflare.0.service=http://dockflare:5000
      #- dockflare.0.access.group=public-default-bypass

      # Add additional callback paths for other OAuth providers as needed
      # - dockflare.1.hostname=dockflare.example.com
      # - dockflare.1.path=/auth/github/callback
      # - dockflare.1.service=http://dockflare:5000
      # - dockflare.1.access.group=public-default-bypass
    volumes:
      - dockflare_data:/app/data
    environment:
      - REDIS_URL=redis://redis:6379/0
      - REDIS_DB_INDEX=0
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
    logging:
      driver: "none"
    volumes:
      - dockflare_redis:/data
    networks:
      - dockflare-internal

  dockflare-mail-manager:
    image: alplat/dockflare-mail-manager:stable
    container_name: dockflare-mail-manager
    restart: unless-stopped
    profiles: ["email"]
    environment:
      - DOCKFLARE_MASTER_URL=http://dockflare:5000
      - MAIL_DATA_PATH=/data
    volumes:
      - mail_data:/data
    depends_on:
      dockflare:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

  dockflare-webmail:
    image: alplat/dockflare-webmail:stable
    container_name: dockflare-webmail
    restart: unless-stopped
    profiles: ["email"]
    environment:
      - DOCKFLARE_MASTER_URL=https://dockflare.TLD  # replace with your domain
    labels:
      - dockflare.enable=true
      - dockflare.hostname=mail.dockflare.TLD  # replace with your domain
      - dockflare.service=http://dockflare-webmail:80
    depends_on:
      dockflare-mail-manager:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  dockflare_data:
  dockflare_redis:
  mail_data:

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

### 2. Crear la red externa

Si todavía no existe:

```bash
docker network create cloudflare-net
```

### 3. Ejecute DockFlare

Inicie la pila en modo independiente:

```bash
docker compose up -d
```

Esto abre el proxy, prepara el volumen e inicia DockFlare junto con Redis.

### 4. Complete la configuración previa al vuelo

Una vez que los servicios se estén ejecutando, abra su navegador en `http://<your-server-ip>:5000`.

El **asistente de configuración inicial** le guiará a través de:
1. Crear una contraseña para la interfaz web.
2. Ingresando sus credenciales de Cloudflare (ID de cuenta, ID de zona, token API).
3. Configurar su túnel Cloudflare inicial.
4. *(Opcional)* Restauración desde un archivo de copia de seguridad de DockFlare. Si ya tiene un `dockflare_backup_*.zip`, elija **Restaurar desde copia de seguridad** antes del Paso 1; el asistente importa su configuración y reinicia el contenedor automáticamente.

### 5. Para usuarios existentes (actualización)

Si está actualizando desde una versión anterior, DockFlare detecta el archivo `.env` heredado, migra su configuración al almacén cifrado y lo guía a través de la creación de contraseñas. Mantenga el proxy de socket en su lugar; ya no se admiten montajes directos de `/var/run/docker.sock`.
