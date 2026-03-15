# Administrar zonas DNS

DockFlare es capaz de administrar registros DNS en múltiples dominios (Zonas de Cloudflare) dentro de la misma cuenta de Cloudflare. Esto le permite ejecutar servicios en `service-a.domain-one.com` y `service-b.another-domain.org` desde la misma instancia de DockFlare.

## Zona predeterminada

Durante la configuración inicial de DockFlare, usted proporciona un **ID de zona**. Esta es la **zona predeterminada** donde DockFlare creará todos los registros DNS. Si solo planeas utilizar un único dominio, esto es todo de lo que debes preocuparte.

## Anulando la zona con una etiqueta

Para administrar un servicio en un dominio distinto al predeterminado, puede usar la etiqueta `dockflare.zonename`.

Esta etiqueta le indica a DockFlare que cree el registro DNS para ese servicio específico en la zona de Cloudflare especificada.

### Requisitos previos

Para que esto funcione, debe asegurarse de que el **Token API de Cloudflare** que está utilizando tenga permisos `Zone:DNS:Edit` para **todas las zonas** que desea administrar.

### Ejemplo

Digamos que su zona predeterminada es `example.com`, pero también desea ejecutar un servicio en `media.io`.

```yaml
services:
  # This service will be created in the default zone (example.com)
  service-one:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://service-one:80"

  # This service will be created in the 'media.io' zone
  service-two:
    image: portainer/portainer-ce
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=portainer.media.io"
      - "dockflare.service=http://service-two:9000"
      # Override the default zone for this service
      - "dockflare.zonename=media.io"
```

Cuando implementes esto, DockFlare:
1. Cree un registro CNAME para `nginx.example.com` en la zona `example.com`.
2. Cree un registro CNAME para `portainer.media.io` en la zona `media.io`.

Ambos nombres de host se agregarán como reglas ingress al mismo túnel de Cloudflare.

## Ver registros DNS en la interfaz web

La interfaz web de DockFlare tiene una función en la página **Settings** que le permite ver todos los túneles de Cloudflare en su cuenta y los registros DNS que apuntan a ellos.

Para asegurarse de que la interfaz web pueda encontrar registros DNS en todas sus zonas, puede utilizar la variable de entorno `TUNNEL_DNS_SCAN_ZONE_NAMES`.

### `TUNNEL_DNS_SCAN_ZONE_NAMES`

Esta variable de entorno acepta una lista separada por comas de nombres de zonas que la interfaz web debe escanear cuando busca registros DNS.

**Ejemplo `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Indica a la interfaz que escanee también estas zonas además de la predeterminada
      - TUNNEL_DNS_SCAN_ZONE_NAMES=media.io,another-domain.org
```

Esto garantizará que el visor de registros DNS en la interfaz web ofrezca una visión completa de todos los dominios que apuntan a sus túneles.
