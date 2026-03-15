# Monitoreo con Prometheus y Grafana

El agente `cloudflared` que administra DockFlare puede exponer una amplia gama de métricas de rendimiento y estado en el formato Prometheus. Al recopilar y visualizar estas métricas, puede obtener información valiosa sobre el tráfico, la latencia y las tasas de error de su túnel.

Esta guía explica cómo habilitar el punto final de métricas y proporciona una configuración rápida para una pila de monitoreo usando Prometheus y Grafana.

## Paso 1: Habilite el punto final de métricas en DockFlare

El primer paso es decirle a DockFlare que habilite el punto final de métricas de Prometheus en su agente `cloudflared` administrado.

Puede hacer esto configurando la variable de entorno `CLOUDFLARED_METRICS_PORT` para su contenedor DockFlare.

**Ejemplo `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Enable the metrics endpoint on port 2000 inside the container
      - CLOUDFLARED_METRICS_PORT=2000
```
Cuando reinicia DockFlare con esta variable, recreará automáticamente su agente `cloudflared` administrado con el servidor de métricas habilitado en el puerto especificado.

**Nota:** Esta función solo está disponible en el **Modo interno** predeterminado. Si utiliza [Modo externo](External-cloudflared-Mode.md), usted es responsable de habilitar el punto final de métricas en su propio agente `cloudflared`.

## Paso 2: configurar una pila de monitoreo

Si aún no tiene una pila de monitoreo, puede configurar una rápidamente usando Docker Compose. El repositorio DockFlare proporciona una configuración de ejemplo en el directorio `/examples`.

Para obtener una guía completa de copiar y pegar sobre cómo configurar Prometheus y Grafana para monitorear DockFlare, consulte el archivo **[`grafana quick setup.md`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/grafana%20quick%20setup.md)** en el repositorio.

Esta guía lo guiará a través de:
1. Crear la estructura de directorios necesaria.
2. Agregar servicios de Prometheus y Grafana a su `docker-compose.yml`.
3. Configurar Prometheus para extraer métricas del agente `cloudflared`.
4. Aprovisionar a Grafana con la fuente de datos de Prometheus automáticamente.

## Paso 3: Importe el panel de Grafana prediseñado

Para facilitar la visualización, DockFlare proporciona un panel de Grafana prediseñado que está diseñado para funcionar perfectamente con las métricas expuestas por el agente `cloudflared`.

1. El panel está disponible como **[`dashboard.json`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/dashboard.json)** en el directorio `/examples` del repositorio.
2. Descargue este archivo.
3. Inicie sesión en su instancia de Grafana.
4. Vaya a la sección "Paneles" y haga clic en "Importar".
5. Cargue el archivo `dashboard.json`.
6. Seleccione su fuente de datos de Prometheus e importe el panel.

Ahora tendrá una descripción general completa del rendimiento de su túnel Cloudflare, incluido el recuento de solicitudes, las tasas de error, la latencia de conexión y más.

![Ejemplo de panel de Grafana](../static/images/grafana_dashboard_example.png)