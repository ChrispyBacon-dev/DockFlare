# Uso de dominios comodín

DockFlare admite el uso de dominios comodín (por ejemplo, `*.example.com`) para enrutar el tráfico de múltiples subdominios a un solo servicio. Esto es particularmente útil para aplicaciones que manejan subdominios dinámicos, como servicios multiinquilino o paneles personales como Heimdall.

## Cómo funciona

Cuando utiliza un nombre de host comodín, Cloudflare Tunnel enrutará todo el tráfico de cualquier subdominio que no tenga un registro DNS más específico al servicio que especifique.

Por ejemplo, si configura `*.apps.example.com`, el tráfico de `service1.apps.example.com`, `service2.apps.example.com`, etc., se enrutará al mismo contenedor de destino.

## Consideraciones importantes

A diferencia de los nombres de host normales, DockFlare **no puede crear automáticamente registros DNS para dominios comodín**. Debe crear el registro DNS comodín manualmente en su panel de Cloudflare.

DockFlare seguirá administrando la **regla ingress** en su túnel Cloudflare, pero la configuración inicial de DNS es un paso manual.

## Guía paso a paso

A continuación se explica cómo configurar correctamente un dominio comodín con DockFlare, usando `*.plex.example.com` como ejemplo.

### Paso 1: Crear manualmente el registro DNS comodín

1. Inicie sesión en su **Panel de Cloudflare**.
2. Navegue hasta la configuración de DNS de su dominio.
3. Haga clic en **Agregar registro** y cree un registro CNAME con los siguientes detalles:
    * **Tipo:** `CNAME`
    * **Nombre:** `*.plex` (o simplemente `*` si su dominio principal es `plex.example.com`)
    * **Objetivo:** El nombre de host público de su túnel. Puede encontrar esto en su panel de Cloudflare Zero Trust en **Acceso -> Túneles**. Se verá algo así como `your-tunnel-uuid.cfargotunnel.com`.
    * **Estado del proxy:** Asegúrese de que esté **Proxied** (nube naranja).

    Este registro DNS manual le dice a Cloudflare que envíe todo el tráfico de `*.plex.example.com` a su túnel.

### Paso 2: Configure su servicio con una etiqueta comodín

Ahora, configure su servicio en su archivo `docker-compose.yml` con una etiqueta de nombre de host comodín.

```yaml
services:
  my-proxy-manager:
    image: nginxproxymanager/nginx-proxy-manager
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      # Use the wildcard hostname here
      - "dockflare.hostname=*.plex.example.com"
      - "dockflare.service=http://my-proxy-manager:81"
```

### Paso 3: Implementar y verificar

1. Guarde su archivo `docker-compose.yml` y ejecute `docker compose up -d`.
2. DockFlare detectará el contenedor y creará una regla ingress en su túnel de Cloudflare para el nombre de host `*.plex.example.com`.
3. Puede verificar esto en la interfaz web de DockFlare y en la configuración de su túnel en el panel de Cloudflare.

Ahora, cualquier solicitud a un subdominio como `sonarr.plex.example.com` o `radarr.plex.example.com` se enrutará a través de su túnel Cloudflare a su contenedor `my-proxy-manager`, que luego puede manejar el tráfico en consecuencia.
