# Persistencia del estado

DockFlare es una aplicación con estado. Necesita realizar un seguimiento de los servicios que administra, los ajustes aplicados desde la interfaz web y otros detalles de configuración. Este estado persiste en el disco para garantizar que su configuración no se pierda si se reinicia o se vuelve a crear el contenedor DockFlare.

## Cómo se almacena el estado

DockFlare almacena su estado en tres archivos clave ubicados en el directorio `/app/data` dentro del contenedor:

1. `dockflare_config.dat`: Este es el archivo más crítico. Contiene todas sus configuraciones principales e información confidencial en un formato **cifrado**. Esto incluye:
    * Su token API de Cloudflare y su ID de cuenta.
    * El hash de contraseña de la interfaz web de DockFlare.
    * Configuraciones principales establecidas a través de la interfaz web, como el nombre del túnel y los ID de zona.

2. `agent_keys.dat`: un almacén cifrado que contiene todas las claves API del agente y sus metadatos (propietario, estado, marcas de tiempo). Mantener este archivo seguro evita que se reutilicen claves obsoletas.

3. `state.json`: este archivo almacena el estado dinámico de sus servicios administrados en un formato JSON simple. Esto incluye:
    * La lista de todas las reglas ingress que DockFlare administra, ya sea que provengan de etiquetas de Docker o se hayan creado manualmente en la interfaz web.
    * Cualquier ajuste aplicado desde la interfaz web a las políticas de acceso.
    * Todos los grupos de acceso que hayas creado.
    * El estado de "eliminación pendiente" para los servicios que se han detenido pero que aún se encuentran dentro de su período de gracia.

## La importancia de un volumen persistente

Debido a que toda su configuración se almacena en el directorio `/app/data`, es **absolutamente crucial** que asigne este directorio a un volumen persistente en su máquina host.

Si no utiliza un volumen persistente, **todas sus configuraciones, la contraseña de la interfaz web y la configuración de reglas se perderán** cada vez que se elimine y vuelva a crear el contenedor DockFlare, por ejemplo al actualizar la imagen.

### Configuración recomendada de Docker Compose

La configuración recomendada `docker-compose.yml` maneja esto automáticamente definiendo un volumen con nombre y montándolo en `/app/data`:

```yaml
services:
  dockflare:
    # ... other settings
    volumes:
      # This line ensures your data is persisted
      - ./dockflare_data:/app/data

volumes:
  # This defines the named volume on your host
  dockflare_data:
```

Con esta configuración, sus archivos `dockflare_config.dat`, `agent_keys.dat` y `state.json` se almacenarán en un directorio llamado `dockflare_data` en su host, preservando de forma segura su configuración en todas las actualizaciones del contenedor.

## Copia de seguridad y restauración

DockFlare ahora agrupa todos los datos críticos en un único archivo de respaldo cifrado. Las cachés de Redis se omiten porque se pueden reconstruir de forma segura en la red privada `dockflare-internal`. El panel **Settings → Backup & Restore** le permite descargar un `.zip` que contiene:

* `dockflare_config.dat`
* `dockflare.key`
* `agent_keys.dat`
* `state.json` (cuando esté presente)
* Un manifiesto con sumas de verificación para verificación de integridad.

La restauración del archivo recrea estos archivos y los recarga en la instancia en ejecución. Las cargas heredadas de `state.json` aún se aceptan, pero solo restauran los metadatos de las reglas; luego deberá volver a ingresar las credenciales manualmente.
DockFlare reinicia automáticamente el contenedor después de una restauración completa del archivo para que la configuración cifrada se cargue inmediatamente.
