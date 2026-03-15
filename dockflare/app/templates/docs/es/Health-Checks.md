# Controles de salud

DockFlare incluye un punto final de verificación de estado dedicado que se puede usar con el mecanismo de verificación de estado integrado de Docker. Esto permite a Docker monitorear el estado de la aplicación DockFlare y reiniciarla automáticamente si deja de responder.

## El punto final `/ping`

DockFlare expone un punto final HTTP simple en `/ping`.

* **Propósito:** Proporcionar una forma sencilla para que los sistemas automatizados verifiquen si el servidor web DockFlare se está ejecutando y responde.
* **Autenticación:** Este punto final está **exento de autenticación**. No es necesario iniciar sesión para acceder a él, que es lo que permite que el mecanismo de verificación de estado interno de Docker lo utilice.
* **Respuesta saludable:** Una aplicación DockFlare en ejecución saludable responderá a una solicitud en `/ping` con un código de estado **HTTP 200 OK**.
* **Información de la versión:** El cuerpo de la respuesta del punto final `/ping` también contiene la versión en ejecución de la aplicación DockFlare.

## Cómo configurar una verificación de estado en Docker Compose

Puede agregar una sección `healthcheck` al servicio `dockflare` en su archivo `docker-compose.yml` para que Docker supervise automáticamente el estado de la aplicación.

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    # ... other settings
    healthcheck:
      # The command to run to check health.
      # curl is used to make an HTTP request to the ping endpoint.
      test: ["CMD", "curl", "-f", "http://localhost:5000/ping"]
      # How often to run the check
      interval: 1m30s
      # How long to wait for a response
      timeout: 10s
      # How many consecutive failures before marking as unhealthy
      retries: 3
      # How long to wait after the container starts before running the first check
      start_period: 40s
```

### Desglose de la configuración `healthcheck`:

* `test`: Este es el comando que Docker ejecuta dentro del contenedor. `curl -f` realizará una solicitud HTTP al punto final `/ping` y saldrá con un código de estado distinto de cero si la respuesta no es HTTP 200 OK.
* `interval`: Docker ejecutará esta verificación cada 90 segundos.
* `timeout`: Docker esperará hasta 10 segundos para que se complete el comando.
* `retries`: Si la verificación falla 3 veces seguidas, Docker marcará el contenedor como `unhealthy`.
* `start_period`: Docker esperará 40 segundos después de que el contenedor se haya iniciado antes de realizar la primera verificación de estado. Esto le da tiempo a la aplicación para inicializarse correctamente.

Con esta configuración implementada, puede verificar el estado de su contenedor ejecutando `docker ps`. La columna de estado mostrará `(healthy)` si la verificación de estado pasa. Si el contenedor deja de estar en buen estado, Docker lo reiniciará automáticamente según la política `restart` (por ejemplo, `unless-stopped`).