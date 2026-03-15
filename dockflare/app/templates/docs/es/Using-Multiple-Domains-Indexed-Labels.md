# Uso de múltiples dominios (etiquetas indexadas)

DockFlare proporciona una poderosa característica llamada **etiquetas indexadas** que le permite definir múltiples reglas ingress independientes para un solo contenedor. Esto es particularmente útil cuando desea exponer diferentes puertos o rutas del mismo servicio en diferentes nombres de host públicos.

## Cómo funciona

Para crear múltiples reglas, simplemente anteponga las etiquetas DockFlare estándar con un número entero y un punto, comenzando desde `0`. Por ejemplo, `dockflare.0.hostname`, `dockflare.1.hostname`, etc.

* Cada índice (por ejemplo, `0`, `1`, `2`) representa una regla ingress separada.
* Siempre se requiere un nombre de host indexado (por ejemplo, `dockflare.<index>.hostname`) para iniciar una nueva regla.
* Otras etiquetas en el mismo índice (por ejemplo, `dockflare.<index>.service`) se aplicarán solo a esa regla específica.

## El mecanismo de respaldo

Una característica clave de las etiquetas indexadas es el mecanismo de reserva. Si no proporciona una etiqueta indexada específica para una regla, **volverá al valor de la etiqueta base correspondiente (no indexada)**.

Esto le permite definir configuraciones comunes una vez en el nivel base y solo anular los valores específicos que deben cambiar para cada regla indexada.

## Ejemplo: exponer una interfaz web y una API

Supongamos que tiene un único contenedor que sirve tanto una aplicación web en el puerto `80` como una API independiente en el puerto `3000`. Desea exponerlas en `app.example.com` y `api.example.com` respectivamente. También desea proteger la API con un grupo de acceso específico, mientras que la aplicación principal permanece pública.

Así es como puede configurarlo usando etiquetas indexadas:

```yaml
services:
  my-app:
    image: my-application
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"

      # --- Base Labels (Fallback) ---
      # This service is used by rule 0, as it's not specified there.
      - "dockflare.service=http://my-app:80" 

      # --- Rule 0: Main web interface ---
      - "dockflare.0.hostname=app.example.com"
      # No 'service' label here, so it falls back to the base one.
      # No 'access.group' label, so it's public.

      # --- Rule 1: The API ---
      - "dockflare.1.hostname=api.example.com"
      # Override the service to point to the API port.
      - "dockflare.1.service=http://my-app:3000"
      # Add a specific access policy for this rule only.
      - "dockflare.1.access.group=api-users-policy"
```

### Desglose del ejemplo

* **Regla 0 (`app.example.com`)**:
    * Define `dockflare.0.hostname`.
    * No define `dockflare.0.service`, por lo que vuelve a la base `dockflare.service` y usa `http://my-app:80`.
    * Es un servicio público porque no está definida ninguna política de acceso para este índice ni a nivel base.

* **Regla 1 (`api.example.com`)**:
    * Define `dockflare.1.hostname`.
    * **Anula** el servicio con `dockflare.1.service`, apuntando al puerto API `3000`.
    * Aplica una política de seguridad específica utilizando `dockflare.1.access.group`. Esta etiqueta solo afecta a esta regla.

Este enfoque mantiene limpia la configuración de su etiqueta y evita la repetición, lo que hace que sus archivos `docker-compose.yml` sean más fáciles de leer y mantener.
