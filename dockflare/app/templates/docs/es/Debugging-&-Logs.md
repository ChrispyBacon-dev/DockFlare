# Depuración y registros

Al solucionar problemas con DockFlare, sus herramientas principales son los registros generados por el contenedor DockFlare y su agente `cloudflared` administrado.

## 1. Verificación de los registros del contenedor DockFlare

La fuente de información más importante es la salida del registro del propio contenedor DockFlare. Estos registros proporcionan una vista detallada en tiempo real de lo que está haciendo DockFlare.

### Lo que encontrarás en los registros:
* Detección de eventos de inicio/parada del contenedor Docker.
* Procesamiento de etiquetas `dockflare.*`.
* Llamadas realizadas a la API de Cloudflare.
* Mensajes de éxito o respuestas de error detalladas de la API de Cloudflare.
* El estado de las tareas en segundo plano, como la limpieza de recursos.

### Cómo ver los registros:
Para ver los registros, use el siguiente comando de Docker en su terminal:
```bash
# View the full log history
docker logs dockflare

# Follow the logs in real-time
docker logs -f dockflare
```

## 2. Uso de los registros en tiempo real de la interfaz web

Para mayor comodidad, el panel de DockFlare incluye un **visor de registros en tiempo real** en la parte inferior de la página principal.

Este visor transmite exactamente los mismos registros que vería con `docker logs -f dockflare`, pero proporciona una manera fácil de ver lo que está sucediendo en este momento sin salir de su navegador. Esto es particularmente útil para observar las acciones que realiza DockFlare inmediatamente después de iniciar o detener un contenedor.

## 3. Verificación de los registros del agente `cloudflared`

Si sospecha que el problema está relacionado con la conexión entre su servidor y la red Cloudflare, puede verificar los registros del contenedor del agente `cloudflared` directamente.

### Cómo ver los registros de los agentes:
Primero, necesita encontrar el nombre del contenedor del agente. De forma predeterminada, se llama `cloudflared-agent-<tunnel-name>`, donde `<tunnel-name>` es el nombre del túnel configurado en la configuración de DockFlare.

Puede encontrar el nombre exacto con `docker ps`.

Una vez que tengas el nombre, ejecuta:
```bash
# Replace with the actual container name
docker logs cloudflared-agent-dockflare-tunnel
```

Estos registros son útiles para diagnosticar:
* Errores de conexión al borde de Cloudflare.
* Problemas de autenticación con su token de túnel.
* Errores a nivel de protocolo para el tráfico proxy.

**Nota:** Esto solo se aplica si está utilizando el **Modo interno** predeterminado. Si está utilizando [Modo externo](External-cloudflared-Mode.md), deberá verificar los registros de su propio proceso de agente `cloudflared`.

## 4. Comprobación del panel de Cloudflare

Finalmente, no olvide utilizar el panel de Cloudflare como herramienta de depuración.
* **Página DNS:** Compruebe si los registros CNAME se crearon como esperaba.
* **Panel de confianza cero:** Vaya a **Acceso -> Túneles** para verificar el estado de su túnel y sus reglas ingress.
* **Panel de Zero Trust:** Vaya a **Acceso -> Aplicaciones** para verificar la configuración y el estado de sus políticas de Zero Trust. El estado "Visto por última vez" de las políticas puede ser muy informativo.
