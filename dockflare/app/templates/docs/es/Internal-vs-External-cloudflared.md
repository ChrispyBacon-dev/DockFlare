# Interno versus externo `cloudflared`

DockFlare puede operar en dos modos para administrar el agente `cloudflared`, que es la pieza de software que realmente crea la conexión persistente entre su servidor y la red Cloudflare. Comprender estos dos modos es clave para elegir la configuración adecuada para su entorno.

## Modo interno (predeterminado)

En modo interno, DockFlare asume toda la responsabilidad de administrar el agente `cloudflared`.

### Cómo funciona
Cuando se inicia DockFlare, automáticamente:
1. Cree un contenedor Docker dedicado que ejecute la imagen `cloudflare/cloudflared`.
2. Configure este contenedor de agente para conectarse a su cuenta de Cloudflare y usar el túnel especificado en su configuración de DockFlare.
3. Asegúrese de que el agente se esté ejecutando y reinícielo si falla.
4. Aplique automáticamente cualquier configuración relevante, como habilitar el punto final de métricas de Prometheus.

Este es el modo **predeterminado y recomendado** para la mayoría de los usuarios.

### Ventajas
* **Simplicidad:** Es una configuración de "configuración cero". DockFlare se encarga de todo por usted.
* **Compatibilidad garantizada:** DockFlare garantiza que el agente esté configurado de manera que pueda funcionar.
* **Gestión Centralizada:** Todo lo relacionado con tus túneles es gestionado por DockFlare.

### Contras
* **Menos control:** Tiene control limitado sobre la configuración del agente `cloudflared` más allá de lo que expone DockFlare.

---

## Modo externo `cloudflared`

En modo externo, usted mismo es responsable de ejecutar y administrar el agente `cloudflared`. DockFlare se conectará a este agente existente en lugar de crear el suyo propio.

### Cómo funciona
DockFlare **no** creará un contenedor `cloudflared`. En cambio, asumirá que tiene un agente `cloudflared` ejecutándose en algún lugar que pueda usar. Esto podría ser:
* Un proceso `cloudflared` que se ejecuta directamente en el sistema operativo host (por ejemplo, como un servicio `systemd`).
* Un contenedor `cloudflared` que usted mismo administra con un archivo `docker-compose.yml` separado o un comando de ejecución de Docker.
* Un agente `cloudflared` que se ejecuta en una máquina completamente diferente.

Este es un **modo avanzado** destinado a usuarios con necesidades específicas o configuraciones complejas existentes.

### Ventajas
* **Control máximo:** Usted tiene control total sobre el agente `cloudflared`, incluida su versión, argumentos de línea de comandos y ciclo de vida.
* **Integración con configuraciones existentes:** Perfecto si ya tiene un agente `cloudflared` ejecutándose para otros fines.
* **Desacoplamiento:** Desacopla el ciclo de vida de DockFlare del ciclo de vida del agente `cloudflared`.

### Contras
* **Complejidad:** Usted es responsable de garantizar que el agente `cloudflared` se esté ejecutando, configurado correctamente y conectado al túnel correcto.
* **Gastos generales de configuración:** Debe configurar DockFlare para usar este agente externo.

### Cómo habilitar el modo externo
Para habilitar el modo externo, debe configurar las siguientes variables de entorno para el contenedor DockFlare:

* `USE_EXTERNAL_CLOUDFLARED=true`: Habilita el modo externo.
* `EXTERNAL_TUNNEL_ID`: Debe configurarse en el UUID del túnel que su agente externo `cloudflared` está configurado para usar.

Cuando se configuran estas variables, DockFlare omitirá la administración interna de su agente y, en su lugar, enviará todas las configuraciones de reglas ingress al túnel especificado por `EXTERNAL_TUNNEL_ID`.
