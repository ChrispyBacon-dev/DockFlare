# Cómo funciona DockFlare

DockFlare actúa como puente entre su entorno Docker y la red de Cloudflare, automatizando la publicación segura de servicios en Internet. Supervisa continuamente el host Docker y utiliza la API de Cloudflare para gestionar túneles, registros DNS y políticas de acceso en su nombre.

## Flujo de trabajo principal

El flujo principal puede resumirse en estos pasos:

1. **Monitorización de eventos de Docker**: DockFlare escucha eventos del socket de Docker, como `start` y `stop` de contenedores.

2. **Detección de etiquetas**: cuando se inicia un contenedor nuevo, DockFlare inspecciona sus etiquetas `dockflare.`. Si encuentra `dockflare.enable=true`, sabe que debe gestionarlo.

3. **Interacción con la API de Cloudflare**: en función de las etiquetas, DockFlare configura los recursos necesarios en Cloudflare:
   * **Cloudflare Tunnel**: añade una regla de ingress al túnel configurado. Esa regla apunta el hostname público a la dirección interna del contenedor, por ejemplo `http://my-app:8080`.
   * **Gestión de DNS**: crea un registro DNS CNAME en su zona de Cloudflare para apuntar el hostname público deseado, por ejemplo `my-app.example.com`, al túnel de Cloudflare.
   * **Políticas de acceso**: si ha definido etiquetas de control de acceso, DockFlare crea o actualiza una política de acceso reutilizable para proteger el servicio con reglas Zero Trust, por ejemplo exigiendo autenticación mediante su proveedor de identidad o aplicando un `bypass` público.

4. **Limpieza automática**: cuando un contenedor gestionado se detiene o se elimina, DockFlare ejecuta automáticamente una limpieza. Elimina la regla de ingress correspondiente del túnel de Cloudflare y, si ningún otro servicio utiliza ese hostname, también elimina el registro DNS y la aplicación de Access. Esto evita configuraciones obsoletas y mantiene limpio el entorno en Cloudflare.

## Componentes de un vistazo

| Componente | Responsabilidad |
| --- | --- |
| DockFlare Master | Aloja la interfaz web y la API, observa los eventos de Docker y orquesta los túneles, DNS y políticas de acceso de Cloudflare. Se ejecuta sin privilegios de root y solo se comunica con Docker a través del socket proxy. |
| Proxy de socket de Docker | Sidecar `tecnativa/docker-socket-proxy` que expone al Master la superficie mínima de la API de Docker (`containers`, `events`, etc.). Evita que el Master monte el socket Docker sin procesar. |
| Redis | Caché, colas, transmisión de registros y canal de heartbeat y retorno para agentes. Vive en la red privada `dockflare-internal`. |
| DockFlare Agents (opcional) | Agentes remotos que replican el comportamiento del Master en otros hosts, transmiten eventos de Docker y gestionan su propio `cloudflared`. |
| `cloudflared` | Mantiene la conexión del túnel con Cloudflare para el Master o para cada agente. |

## Modelo de configuración por capas

DockFlare utiliza un enfoque flexible y por capas que combina automatización con control detallado:

1. **Etiquetas Docker (capa base)**: es el método principal y automatizado. La configuración completa de un servicio, como hostname, URL interna y política de acceso, se define directamente en `docker-compose.yml` o en el comando `docker run`. Esa configuración es la fuente de verdad para los servicios automatizados.

2. **Grupos de acceso (capa de abstracción)**: para evitar repetir políticas complejas en muchos servicios, puede crear **Grupos de acceso** reutilizables desde la interfaz web. Son plantillas que agrupan reglas de acceso, como permitir correos corporativos o acceso desde países concretos, y se sincronizan con políticas reutilizables de Cloudflare Access. La opción `Public` o `Authenticated` del cuadro de diálogo controla si DockFlare emite una decisión `bypass` o `allow`. Después puede aplicar toda la política a un contenedor con una sola etiqueta, por ejemplo `dockflare.access.group=my-policy-group`.

3. **Ajustes desde la interfaz web (capa de control)**: la interfaz web ofrece el mayor nivel de control. Desde el panel puede:
   * **Sobrescribir** la política de acceso de cualquier servicio, tanto si fue definida por etiquetas como por un grupo de acceso. Estas sobrescrituras son persistentes y no se revierten al reiniciar el contenedor.
   * **Crear reglas de ingress manuales** para servicios que no se ejecutan en Docker, por ejemplo un servicio en otra máquina de la red.
   * **Revertir** la configuración de un servicio a lo definido en sus etiquetas Docker y descartar cualquier ajuste aplicado desde la interfaz web.

Este modelo por capas le permite automatizar la mayoría de servicios con etiquetas Docker sin perder la capacidad de gestionar excepciones o escenarios complejos desde la interfaz web.

---

## Arquitectura de políticas de Access (v3.0.3+)

### Sistema de políticas reutilizables

DockFlare utiliza ahora una **arquitectura de políticas reutilizables** alineada con las mejores prácticas de Cloudflare:

1. **Grupos de acceso** → se sincronizan con → **Políticas reutilizables de Cloudflare**
2. **Aplicaciones de Access** → referencian → **IDs de políticas reutilizables**
3. **Una única fuente de verdad** → se actualiza una vez y se aplica en todas partes

Esta arquitectura elimina la duplicación de políticas y le permite gestionarlas desde DockFlare o desde el panel de Cloudflare con sincronización bidireccional completa.

### Políticas gestionadas por el sistema

DockFlare gestiona automáticamente dos políticas principales para mantener la coherencia:

- **`public-default-bypass`**: política de bypass para acceso público
  - Política del sistema no eliminable
  - Se crea automáticamente durante la inicialización
  - Nombre en Cloudflare: `DockFlare-Default-Public-Access-Bypass`
  - Decisión: `bypass` con regla `everyone`
  - Utilizada por servicios que requieren acceso público sin aplicar la protección de zona
  - Evita políticas de bypass duplicadas en el panel de Cloudflare

- **`authenticated-default`**: política de autenticación predeterminada
  - Política del sistema no eliminable
  - Se crea automáticamente durante la inicialización
  - Nombre en Cloudflare: `DockFlare-Default-Authenticated-Access`
  - Decisión: `allow` con PIN de un solo uso más restricción por correo electrónico
  - Utilizada en escenarios básicos de acceso autenticado

### Migración de etiquetas heredadas

DockFlare migra automáticamente las etiquetas heredadas para usar políticas del sistema:

- `dockflare.access.policy=bypass` → usa `public-default-bypass`
- `dockflare.access.group=bypass` → usa `public-default-bypass`
- `dockflare.access.policy=authenticate` → usa `authenticated-default`

La migración ocurre de forma transparente durante el procesamiento y la reconciliación de contenedores. No requiere intervención manual.

### Políticas predeterminadas de zona

Las políticas wildcard a nivel de zona (`*.domain.com`) proporcionan seguridad por capas mediante prioridad:

1. **Política específica de hostname** (por ejemplo, `app.example.com`) - máxima prioridad
2. **Política wildcard de zona** (por ejemplo, `*.example.com`) - respaldo
3. **Sin política** = acceso público, sin Access App - comportamiento predeterminado

Esto garantiza que los servicios olvidados o no documentados sigan protegidos por la política de zona, actuando como red de seguridad.

**Ejemplo:**
- Política de zona: `*.internal.company.com` → requiere autenticación con correo corporativo
- Servicio específico: `public-demo.internal.company.com` → usa `public-default-bypass`
- Servicio olvidado: `test.internal.company.com` → queda protegido por la política de zona y requiere autenticación
