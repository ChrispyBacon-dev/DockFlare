# Uso básico (dominio único)

Esta guía demuestra el caso de uso más común de DockFlare: exponer un único contenedor Docker a Internet en un nombre de host público.

## Requisitos previos

Antes de comenzar, asegúrese de tener:
1. Completó la guía [Inicio rápido](Quick-Start-Docker-Compose.md).
2. DockFlare se está ejecutando y conectado a su cuenta de Cloudflare.
3. Tiene un servicio que desea exponer (usaremos `nginx` en este ejemplo).

## Ejemplo: exposición de un contenedor NGINX

Supongamos que desea exponer un servidor web NGINX estándar con el nombre de host `nginx.example.com`.

### 1. Agregue el Servicio a su `docker-compose.yml`

Modifique su archivo `docker-compose.yml` para incluir el servicio `nginx`. La clave es agregar las etiquetas `dockflare.*` a su configuración.

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

  # Add your new service here
  nginx-webserver:
    image: nginx:latest
    container_name: my-nginx
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://nginx-webserver:80"
      # Optional: Apply public access with zone protection bypass
      - "dockflare.access.group=public-default-bypass"

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
> **¿Por qué Redis?** DockFlare depende de Redis para el almacenamiento en caché, la transmisión de registros y la mensajería entre subprocesos. Ejecutarlo en la red privada `dockflare-internal` mantiene a Redis accesible solo para DockFlare, mientras que las cargas de trabajo permanecen aisladas en `cloudflare-net`.


### 2. Comprensión de las etiquetas

* `dockflare.enable=true`: Esto le dice a DockFlare que administre este contenedor.
* `dockflare.hostname=nginx.example.com`: Esta es la URL pública donde estará disponible su servicio. DockFlare creará un registro DNS para este nombre de host en su cuenta de Cloudflare.
* `dockflare.service=http://nginx-webserver:80`: Esto le indica a Cloudflare Tunnel dónde enviar el tráfico. Es la dirección interna del contenedor NGINX. Tenga en cuenta que estamos utilizando el nombre del servicio (`nginx-webserver`) como nombre de host, lo cual es posible porque ambos contenedores están en la misma red Docker.
* `dockflare.access.group=public-default-bypass`: (Opcional) Utiliza la política de omisión del sistema para garantizar el acceso público incluso si existe una política de protección `*.example.com` a nivel de zona. Esto es importante cuando tiene políticas comodín que protegen su dominio pero necesita servicios específicos para permanecer público.

### 3. Implementar el servicio

Guarde su archivo `docker-compose.yml` y ejecute el siguiente comando para iniciar el nuevo servicio:

```bash
docker compose up -d
```

### 4. Verificación

DockFlare detectará el nuevo contenedor y realizará automáticamente las siguientes acciones:
1. Agregue una regla ingress a su túnel de Cloudflare para `nginx.example.com`.
2. Cree un registro CNAME para `nginx.example.com` en su DNS de Cloudflare, apuntando al túnel.

Puedes verificar esto de varias maneras:
* **Interfaz web de DockFlare**: el servicio `nginx.example.com` aparecerá en el panel.
* **Panel de control de Cloudflare**: Verá el nuevo registro CNAME en su configuración de DNS y la nueva regla ingress en la configuración de su túnel.

Después de unos momentos para que se propague DNS, debería poder navegar a `https://nginx.example.com` en su navegador y ver la página de bienvenida predeterminada de NGINX.

## Copia de seguridad y restauración de profundidad

DockFlare viene con un flujo de respaldo de primera clase para que puedas mover o recuperar una instancia en minutos.

### Qué contiene el archivo de copia de seguridad

Cuando descarga una copia de seguridad desde **Settings → Backup & Restore** (o el wizard de onboarding), DockFlare genera un `.zip` con los siguientes archivos:

| Archivo | Descripción |
| --- | --- |
| `dockflare_config.dat` | Carga útil de configuración cifrada (credenciales de Cloudflare, hash de contraseña de la interfaz web, valores predeterminados de túnel, clave API del Master, etc.). |
| `dockflare.key` | La clave Fernet utilizada para descifrar `dockflare_config.dat` y otras cargas útiles cifradas. Guárdelo con el archivo. |
| `agent_keys.dat` | Registro cifrado de claves API del agente, metadatos y estado de revocación. |
| `state.json` | Instantánea JSON simple del estado del tiempo de ejecución: reglas administradas, agentes, grupos de acceso. Esto se incluye para que los operadores puedan inspeccionar o migrar piezas específicas si es necesario. |
| `manifest.json` | Sumas de verificación e información de versiones para cada archivo en el archivo. |

La copia de seguridad es autónoma: restaurarla a través del asistente/punto final de aplicación escribe cada archivo en `/app/data/` e inmediatamente programa un reinicio del contenedor para que la configuración cifrada se vuelva a cargar al arrancar.

### Notas de restauración y compatibilidad

- **Interfaz web del asistente y de Settings**: cargue el `.zip` y DockFlare lo importará, recargará el estado y saldrá. Docker reinicia el contenedor automáticamente, por lo que vuelve al modo operativo sin intervención manual.
- **Legacy `state.json`**: para solucionar problemas o flujos de trabajo avanzados, aún puede cargar solo un archivo `state.json`. DockFlare completará el estado de ejecución pero omitirá la configuración cifrada; luego deberá volver a ingresar las credenciales.
- **Automatización**: debido a que el reinicio es automático, asegúrese de que cualquier verificación de estado del proxy inverso permita una breve ventana de reinicio (~5 segundos) después de una restauración.

Las copias de seguridad **no** incluyen el conjunto de datos de Redis; solo almacena en caché los datos que DockFlare puede volver a calcular. El volumen `/app/data` junto con el archivo es la pieza fundamental para proteger y realizar copias de seguridad.
