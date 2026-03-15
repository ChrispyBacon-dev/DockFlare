# Arquitectura y refuerzo de seguridad de DockFlare

Este documento explica cómo DockFlare protege tanto el nodo Master como los agentes inscritos en DockFlare 3.0+. Complementa la auditoría de seguridad resumiendo las protecciones integradas en DockFlare y las prácticas operativas recomendadas.

## 1. Modelo de confianza del plano de control

- **El Master como fuente de verdad**: DockFlare Master almacena todas las credenciales de Cloudflare y las definiciones de políticas. Los agentes nunca gestionan tokens API por su cuenta; solo ejecutan instrucciones recibidas a través de un canal autenticado.
- **Claves API por agente**: la inscripción requiere una clave API única emitida por el Master. Las claves se almacenan en el almacén cifrado `agent_keys.dat` junto con metadatos como propietario, marcas temporales y estado, de modo que puedan rotarse o revocarse en cualquier momento.
- **Protección de la API del Master**: los endpoints administrativos, incluida la interfaz web y `/api/v2/*`, requieren una sesión válida o la clave API del Master. Los tokens se ocultan en respuestas y logs, y pueden rotarse sin reiniciar la stack.

## 2. Configuración cifrada y gestión de claves

- **`dockflare_config.dat` cifrado**: las credenciales de Cloudflare, las cuentas de la interfaz web, los valores predeterminados del túnel y la clave del Master se guardan en un blob cifrado protegido por `dockflare.key`.
- **Registro de agentes cifrado**: las claves API de los agentes y sus metadatos de auditoría viven en `agent_keys.dat`, cifrados con la misma clave Fernet. El material sensible ya no aparece en `state.json`.
- **Reinicio automático al restaurar**: cuando se restaura un archivo de respaldo, DockFlare escribe los artefactos cifrados, recarga el estado de ejecución, deja una marca de reinicio y termina. La política de reinicio de Docker vuelve a levantar el contenedor inmediatamente con la nueva configuración.
- **`state.json` en texto plano para observabilidad**: `state.json` se mantiene en texto plano para que los operadores puedan inspeccionar reglas y agentes. Los archivos cifrados siguen siendo la fuente autorizada para los secretos.

## 3. Garantías de copia de seguridad y restauración

- **Contenido del archivo**: cada archivo de copia de seguridad (`dockflare_backup_*.zip`) contiene `dockflare_config.dat`, `dockflare.key`, `agent_keys.dat`, `state.json` y un `manifest.json` con checksums y metadatos de versión. No se necesitan archivos adicionales para reconstruir un nodo Master.
- **Flujo de restauración automatizado**: restaurar desde el asistente de configuración o desde la página Settings escribe los artefactos, recarga las cachés de ejecución y fuerza un reinicio del contenedor para aplicar de inmediato la configuración cifrada.
- **Compatibilidad heredada**: la carga de un `state.json` independiente sigue estando soportada para troubleshooting o migraciones parciales. DockFlare importa el estado de ejecución, pero conserva la configuración cifrada existente para evitar reinicios accidentales de credenciales.

## 4. Seguridad de red y comunicaciones

- **Transporte por Cloudflare Tunnel**: los agentes no exponen puertos de entrada. Todo el tráfico pasa por el túnel de Cloudflare administrado por el Master, lo que reduce la superficie de ataque en hosts remotos.
- **Llamadas autenticadas de agentes**: las llamadas REST de los agentes incluyen su clave API y están vinculadas al ID de agente registrado. Cualquier token incorrecto o revocado se rechaza.
- **Capa Redis compartida**: DockFlare depende de Redis para caché, streaming de logs y señalización entre hilos. La stack Compose recomendada mantiene Redis en una red `dockflare-internal` dedicada, de modo que las cargas de trabajo en `cloudflare-net` no puedan alcanzarlo directamente. Si usa un Redis externo, protéjalo con autenticación y TLS.
- **Ejecución de mínimo privilegio**: tanto el Master como los agentes se ejecutan como el usuario `dockflare` (UID/GID 65532) y se comunican con Docker exclusivamente a través del socket proxy incluido, manteniendo al mínimo la superficie expuesta de la API.

## 5. Autenticación y autorización

- **Inicio de sesión reforzado en la interfaz web**: el asistente de configuración inicial obliga a crear una cuenta de administrador para la interfaz web. Es posible desactivar el acceso con contraseña, pero **se desaconseja firmemente** debido a las implicaciones de seguridad en la red Docker.
- **Gestión de sesiones**: las sesiones de Flask-Login están ligadas a la configuración cifrada. Restaurar un backup o rotar credenciales invalida automáticamente las sesiones existentes.
- **ACL de agentes**: cada registro de agente rastrea la asignación de túnel, las marcas temporales de heartbeat y los comandos pendientes. El Master solo entrega comandos a agentes que presentan el token correcto y un estado de inscripción válido.

### ⚠️ Importante: advertencia de seguridad sobre “Disable Password Login”

DockFlare incluye la opción **Disable Password Login**, pensada para despliegues avanzados en los que DockFlare ya está protegido por una capa de autenticación externa, como Cloudflare Access. **Desaconsejamos firmemente su uso** en la mayoría de los casos.

**Riesgos de seguridad cuando está habilitada:**
- **Todos los endpoints de la API quedan accesibles sin autenticación**
- **Exposición en la red Docker**: aunque DockFlare esté protegido por Cloudflare Access en Internet, los contenedores de la misma red Docker pueden saltarse esa autenticación externa y acceder directamente a la API
- **Sin aplicación interna de autenticación**: la aplicación asume que la autenticación externa se encarga de toda la seguridad

**Ejemplo de vector de ataque:**
```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

**Enfoque recomendado:**
En lugar de desactivar la autenticación por contraseña, use una de estas opciones seguras:
1. **Credenciales locales de DockFlare** - Autenticación simple por contraseña integrada en DockFlare
2. **Proveedores OAuth/OIDC** - Configure Google, GitHub, Azure AD u otros proveedores de identidad para disfrutar de single sign-on sin comprometer la seguridad

Ambas opciones ofrecen autenticación adecuada sin perder la comodidad del SSO. La opción OAuth le da esa experiencia sin asumir los riesgos de una autenticación desactivada.

**En resumen:** salvo que disponga de una arquitectura de seguridad muy específica, bien entendida y con aislamiento de red real, mantenga activado el acceso con contraseña y utilice OAuth por comodidad.

## 6. Auditoría y visibilidad operativa

- **Seguimiento de metadatos**: las claves de agente registran `created_at`, `last_used_at`, `bound_agent_id`, estado y eventos de revocación. `state.json` también refleja la última vez que se vio al agente, lo que facilita los chequeos rápidos de salud.
- **Streaming de logs**: los logs en tiempo real se transmiten mediante Redis pub/sub. Los valores sensibles, como tokens y claves, se redactan antes de llegar al cliente.
- **APIs de estado**: `/api/v2/overview` consolida el estado del túnel, de los agentes y de la configuración para sistemas de monitorización o flujos GitOps.

## 7. Recomendaciones de despliegue

| Área | Recomendación |
| --- | --- |
| Volúmenes Docker | Mantenga `/app/data` para la configuración cifrada, las claves y el estado. Mantenga también `/app/logs` si el logging a archivo está activado, y asegúrese de que los montajes del host sean escribibles por UID/GID 65532 o por los argumentos de compilación personalizados. |
| Redis | Ejecute `redis:7-alpine` junto a DockFlare en una red privada (`dockflare-internal`) o apunte `REDIS_URL` a una instancia reforzada con autenticación/TLS. Evite exponer Redis públicamente. Use `REDIS_DB_INDEX` para aislar los datos de DockFlare de otros contenedores que compartan la misma instancia de Redis. |
| Copias de seguridad | Descargue el `.zip` periódicamente y guárdelo junto con `dockflare.key`. Ambos archivos son necesarios para descifrar la configuración durante la restauración. |
| Agentes | Trate las claves API como credenciales sensibles. Despliegue los agentes junto con el socket proxy para que solo se expongan los endpoints Docker necesarios, y recuerde que el contenedor se ejecuta como el usuario sin privilegios `dockflare` (UID/GID 65532); ajuste los permisos del host o reconstruya con `DOCKFLARE_UID/DOCKFLARE_GID` adecuados. |
| Proxy inverso | Coloque DockFlare detrás de Cloudflare Access u otro IdP de confianza. Si desactiva el acceso con contraseña, asegúrese de que la autenticación aguas arriba se aplique siempre. |
| Monitorización | Genere alertas ante reinicios inesperados, heartbeats ausentes o emisión de nuevas claves fuera de ventanas de mantenimiento. |

## 8. Mejoras futuras (hoja de ruta)

- Protección opcional mediante passphrase para la clave Fernet en reposo.
- Rotación automatizada de claves de agentes con periodos de gracia para despliegues progresivos.
- Ámbitos granulares de comandos para separar operaciones de solo lectura de operaciones mutables.

---

DockFlare sigue evolucionando con la seguridad como prioridad. Revise las notas de versión para conocer mejoras adicionales y comparta ideas a través del issue tracker si necesita más controles.
