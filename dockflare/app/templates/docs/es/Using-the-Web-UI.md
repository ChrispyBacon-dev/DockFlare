# Uso de la interfaz web

La interfaz web de DockFlare es una herramienta potente para administrar, supervisar y configurar sus servicios. Proporciona una experiencia clara para tareas que van más allá de la simple configuración mediante etiquetas de Docker.

## El panel (página principal)

La primera página que ve después de iniciar sesión es el panel principal. Es el lugar central para consultar el estado de todos sus servicios administrados.

* **Tabla de reglas ingress administradas:** Esta tabla enumera todas las reglas ingress que administra DockFlare, ya sea que provengan de un contenedor Docker o se hayan creado manualmente.
    * **Nombre de host:** El nombre de host público del servicio.
    * **Servicio:** La URL de destino interna.
    * **Fuente:** Indica si la regla proviene de `Docker` o si se creó manualmente en la interfaz web.
    * **Estado:** Muestra si la regla es `active`, `pending_deletion` o tiene un `UI Override`.
    * **Acceso:** Muestra el grupo de acceso aplicado y la insignia de modo. Espere ver etiquetas `Public` o `Authenticated`, nombres de grupos en cascada y enlaces rápidos al panel de Cloudflare cuando se sincronicen las políticas reutilizables.
    * **Administrar regla:** Este botón le permite editar cualquier regla.
* **Registros en tiempo real:** Debajo de la tabla, encontrará un visor en tiempo real que muestra los registros del backend de DockFlare, lo cual resulta muy útil para depurar.

## Gestión de reglas

La interfaz web le brinda control total sobre sus reglas ingress.

* **Add Manual Rule:** El botón "Add Manual Rule" le permite crear reglas ingress para servicios que no se ejecutan en Docker (por ejemplo, un servicio en otra máquina en su LAN). El formulario le permite especificar el nombre de host, la URL del servicio y, opcionalmente, aplicar un grupo de acceso.
* **Manage Rule:** El botón "Manage Rule" junto a cada regla abre un cuadro de diálogo en el que puede cambiar su configuración. También es ahí donde puede aplicar un ajuste de la interfaz web a una regla creada originalmente a partir de etiquetas de Docker.
* **Revert to Labels:** Si una regla de Docker tiene un ajuste aplicado desde la interfaz web, aparecerá el botón "Revert to Labels", que permite descartar los cambios manuales y dejar que la regla vuelva a controlarse mediante sus etiquetas de Docker.

## Página de políticas de acceso

Esta página es la ubicación central para administrar sus **Grupos de acceso** reutilizables y proteger sus zonas DNS con políticas de comodines.

### Políticas de acceso avanzado

Desde la sección Grupos de acceso, puedes:
* **Cree** nuevos grupos de acceso utilizando el modo de dos pestañas (Autenticado vs Público). Los banners de orientación se actualizan por pestaña para que sepa cuándo DockFlare emitirá una decisión de Cloudflare `allow` o `bypass`.
* **Editar** grupos de acceso existentes. El modal aplica la validación específica del modo (se requieren correos electrónicos para autenticar) y mantiene la configuración geográfica/IP visible para ambos modos.
* **Eliminar** Grupos de acceso que ya no están en uso (las políticas del sistema como `public-default-bypass` no se pueden eliminar).
* **Sincronización desde Cloudflare** para importar políticas reutilizables de DockFlare existentes desde su cuenta.
* Utilice el menú de acciones al lado de cada entrada para abrir la política coincidente directamente en el panel de Cloudflare a través del acceso directo al ícono de Cloudflare.

**Nota:** DockFlare crea y administra automáticamente la política del sistema `public-default-bypass`. Todos los servicios que utilizan el acceso "Omitir" hacen referencia a esta política única, lo que mantiene limpio su panel de Cloudflare.

### Políticas predeterminadas de zona (*.tld comodines)

La segunda sección muestra **Políticas predeterminadas de zona**: una característica de prácticas recomendadas de seguridad que protege todos los subdominios:

* **Estado de protección:** Las insignias visuales muestran qué zonas DNS tienen políticas comodín `*.domain.com` (Protegidas 🛡️) y cuáles no (No protegidas ⚠️).
* **Crear política de zona:** Haga clic en "Crear política" en cualquier zona desprotegida para crear una aplicación de acceso comodín.
* **Seleccione política:** Elija qué grupo de acceso debe proteger todos los subdominios de la zona (puede ser omisión pública, autenticación o cualquier política personalizada).
* **Red de seguridad:** Incluso si olvida agregar una política a un servicio concreto, la política comodín de la zona seguirá protegiéndolo.

**Mejores prácticas:** Cree políticas de zona predeterminadas para todos sus dominios. Para dominios públicos, utilice la política de omisión predeterminada. Para dominios internos/privados, utilice una política de autenticación. Esto garantiza que ningún subdominio quede expuesto accidentalmente.

Para obtener más detalles, consulte la guía [Mejores prácticas y ejemplos de políticas de acceso](Access-Policy-Best-Practices.md).

## Página de configuración

La página Configuración contiene varias opciones administrativas y de configuración:

* **Túneles de Cloudflare:** Esta sección enumera todos los túneles de Cloudflare que se encuentran en su cuenta, su estado y sus agentes `cloudflared` conectados. También puede ver todos los registros DNS CNAME que apuntan a cualquiera de sus túneles.
* **Copia de seguridad y restauración:** Descargue un archivo de copia de seguridad completo de DockFlare (`.zip`) que contenga configuración cifrada, claves de agente y estado, o cargue un archivo previamente exportado para restaurar la instancia.
* **Seguridad:**
    * **Change Password:** Cambie la contraseña de acceso a la interfaz web.
    * **Disable Password Login:** Para casos de uso avanzados en los que DockFlare está protegido detrás de otro proxy de autenticación. **⚠️ Advertencia:** Esto crea un riesgo de seguridad por la exposición de la red Docker: cualquier contenedor en la misma red Docker puede eludir la autenticación externa y acceder directamente a la API de DockFlare. Recomendamos encarecidamente utilizar proveedores de OAuth/OIDC para obtener la comodidad del single sign-on sin sacrificar la seguridad. Consulte [Acceso a la interfaz web](Accessing-the-Web-UI.md) para conocer todas las implicaciones de seguridad.
* **Credenciales de Cloudflare:** Le permite actualizar su ID de cuenta de Cloudflare y su token API después de la configuración inicial.
* **Configuración principal:** Le permite cambiar configuraciones como el nombre del túnel y el período de gracia de la regla.
