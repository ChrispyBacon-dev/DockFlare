# Cambiar entre modos

Puede cambiar DockFlare entre los modos **Interno** (predeterminado) y **Externo** `cloudflared` en cualquier momento. Esta guía explica el proceso para una transición sin problemas.

Para obtener una comparación detallada de los dos modos, consulte la página [Interno vs. Externo `cloudflared`](Internal-vs-External-cloudflared.md).

---

## Cambiar del modo interno al externo

Este proceso implica configurar su propio agente `cloudflared` y luego decirle a DockFlare que lo use.

**Paso 1: Configure su agente externo `cloudflared`**

Primero, necesita configurar y ejecutar su propio agente `cloudflared`. Podría ser un proceso en el sistema operativo host u otro contenedor Docker.

* Asegúrese de que esté configurado para utilizar un túnel de Cloudflare específico.
* Tome nota del **ID del túnel** (UUID).
* Inicie el agente y confirme que se esté ejecutando correctamente y que se muestre como "conectado" en su panel de Cloudflare.

**Paso 2: Reconfigurar y reiniciar DockFlare**

A continuación, debe actualizar las variables de entorno de su contenedor DockFlare para indicarle que cambie al modo externo.

En su `docker-compose.yml`:
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Enable external mode
      - USE_EXTERNAL_CLOUDFLARED=true
      # Provide the ID of your running tunnel
      - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Paso 3: implementar el cambio**

Ejecute `docker compose up -d` para recrear el contenedor DockFlare con las nuevas variables de entorno.

Cuando se inicia el contenedor DockFlare actualizado:
1. Detectará que `USE_EXTERNAL_CLOUDFLARED` es `true`.
2. **Detendrá y eliminará** su propio contenedor `cloudflared-agent` administrado.
3. Comenzará a enviar todas sus configuraciones de reglas ingress al túnel especificado por `EXTERNAL_TUNNEL_ID`.

Sus servicios ahora serán atendidos por su agente `cloudflared` administrado externamente.

---

## Cambiar del modo externo al interno

Este proceso es más sencillo ya que implica dejar que DockFlare recupere el control.

**Paso 1: Reconfigurar DockFlare**

Elimine las variables de entorno del modo externo de su archivo DockFlare `docker-compose.yml`.

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Remove the following two lines
      # - USE_EXTERNAL_CLOUDFLARED=true
      # - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Paso 2: implementar el cambio**

Ejecute `docker compose up -d` para recrear el contenedor DockFlare.

Cuando se inicia el contenedor DockFlare actualizado:
1. Detectará que `USE_EXTERNAL_CLOUDFLARED` es `false`.
2. Automáticamente **creará, configurará e iniciará** su propio contenedor interno `cloudflared-agent`.
3. Configurará este nuevo agente para usar el nombre del túnel definido en la configuración de DockFlare.

**Paso 3: Retire su agente externo**

Una vez que haya confirmado que el nuevo agente interno se está ejecutando correctamente y atendiendo el tráfico, puede detener y eliminar de forma segura su propio agente `cloudflared`.
