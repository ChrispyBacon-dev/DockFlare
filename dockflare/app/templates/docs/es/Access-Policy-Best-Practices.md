# Mejores prácticas y ejemplos de políticas de acceso

La función de seguridad más potente de DockFlare son los **Grupos de acceso**. Proporcionan una forma centralizada, reutilizable y fácil de mantener para proteger sus servicios con Cloudflare Zero Trust.

## La "regla de oro": utilice grupos de acceso

La recomendación más importante es **utilizar grupos de acceso para todas sus políticas de acceso habituales**.

Los grupos de acceso son plantillas de políticas que usted crea en la interfaz web de DockFlare. En lugar de definir reglas complejas con varias etiquetas en cada contenedor, crea una política una vez y la aplica con una etiqueta sencilla y clara. DockFlare v3.0.3 sincroniza cada grupo con una política de acceso reutilizable de Cloudflare para que el mismo conjunto de decisiones pueda servir a varias aplicaciones.

---

## Cómo crear y utilizar grupos de acceso

Crear un grupo de acceso es un proceso sencillo que se realiza completamente dentro de la interfaz web de DockFlare.

### Paso 1: crear el grupo de acceso

1. Vaya a la página **Access Policies** desde la barra de navegación principal en la interfaz web de DockFlare.
2. Haga clic en el botón **"Add Access Group"**.
3. Asigne a su grupo un **ID único y descriptivo**. Este ID es el que usará en sus etiquetas de Docker. Por ejemplo: `admin-users`, `home-network`, `geo-block`.
4. Elija el **Access Mode** en las pestañas en la parte superior del modal:
    * **Authenticated** requiere que los usuarios inicien sesión y emite una decisión `allow`.
    * **Public** utiliza una decisión `bypass` para que la aplicación permanezca abierta y al mismo tiempo respete los filtros geográficos.
5. Complete los campos que aparecen para el modo seleccionado (correos electrónicos para Authenticated, lista de países opcional para ambos).
6. Ajuste las configuraciones opcionales como la duración de la sesión, la visibilidad del Iniciador de aplicaciones y la redirección automática de IdP si está en modo autenticado.
7. Guarde el grupo. DockFlare escribe la definición localmente y la sincroniza con Cloudflare como `DockFlare-AccessGroup-<id>`.

### Paso 2: Aplicar el grupo de acceso

Una vez creado, tiene dos formas de aplicar su grupo de acceso a un servicio:

#### A) Con una etiqueta Docker (la forma recomendada)

Para cualquier contenedor nuevo o existente, simplemente agregue la etiqueta `dockflare.access.group` con el ID del grupo que creó.

```yaml
services:
  grafana:
    image: grafana/grafana
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=monitoring.example.com"
      - "dockflare.service=http://grafana:3000"
      # Apply the entire policy with one simple label:
      - "dockflare.access.group=admin-users"
```
También puede aplicar varios grupos utilizando `dockflare.access.groups` con una lista de ID separados por comas:
`dockflare.access.groups=admin-users,home-network`

#### Políticas administradas por el sistema

DockFlare proporciona dos políticas de sistema integradas que están disponibles automáticamente:

- **`public-default-bypass`** - Acceso público con decisión de omisión (uso para servicios verdaderamente públicos)
- **`authenticated-default`** - Autenticación predeterminada con PIN de un solo uso + restricción de correo electrónico

Estas políticas del sistema no se pueden eliminar y sirven como base para la protección de zonas y la migración de etiquetas heredadas.

#### B) A través de la interfaz web (para reglas manuales o ajustes)

También puede aplicar un grupo de acceso a cualquier regla directamente desde el panel:
1. Busque la regla ingress que desea modificar en el panel principal.
2. Haga clic en el botón **"Manage Rule"**.
3. En el modo de edición, seleccione los grupos de acceso que desee en el menú desplegable "Access Groups".
4. Guarde los cambios.

Esto es ideal para aplicar políticas a reglas creadas manualmente, por ejemplo para servicios que no se ejecutan en Docker, o para sustituir temporalmente una política definida por etiquetas de Docker.

---

## Ejemplos de políticas

A continuación se muestran algunas configuraciones de políticas comunes que puede crear dentro de un grupo de acceso.

### Ejemplo 1: Autenticar por correo electrónico

Este es el caso de uso más común: permitir solo usuarios específicos que puedan autenticarse con su proveedor de identidad configurado (por ejemplo, Google, GitHub o un PIN de un solo uso enviado a su correo electrónico).

* **ID de grupo:** `admin-users`
* **Modo:** *Autenticado*
* **Correos electrónicos permitidos:** `user1@example.com`, `user2@example.com`
* **Duración de la sesión:** `24h`

DockFlare crea una política reutilizable con una decisión `allow` para los correos electrónicos enumerados y una regla alternativa `deny` para todos los demás. Aplicar el grupo con `dockflare.access.group=admin-users`.

### Ejemplo 2: Permitir la dirección IP de su hogar

Esta política restringe el acceso a su red doméstica, lo que le permite omitir el mensaje de inicio de sesión cuando se encuentra en una IP confiable mientras aplica la autenticación en otro lugar.

1. **Encuentre su IP pública:** En su navegador, busque "cuál es mi ip". Se mostrará su dirección IP pública (por ejemplo, `203.0.113.55`).
2. **Cree el grupo de acceso:**
    * **ID de grupo:** `home-network`
    * **Modo:** *Autenticado*
    * **Correos electrónicos permitidos:** `you@example.com`
    * **Omitir IP:** agregue `203.0.113.55/32` al campo de lista de IP permitidas

DockFlare genera una política que primero omite su rango de IP y luego requiere que los correos electrónicos enumerados se autentiquen. Todos los demás reciben una decisión de denegación.

### Ejemplo 3: Geocercado (bloqueo de varios países)

Esta política mantiene público su sitio de marketing y al mismo tiempo limita el tráfico de regiones específicas.

* **ID de grupo:** `public-eu`
* **Modo:** *Público*
* **Países bloqueados:** `RU`, `CN`, `KP`

La política reutilizable resultante emite una decisión de Cloudflare `bypass` para todos, excepto los países enumerados. Combínelo con otros grupos si necesita superponer controles adicionales (`dockflare.access.groups=public-eu,admin-users`).

---

## Políticas predeterminadas de zona: mejores prácticas de seguridad

### ¿Qué son las políticas predeterminadas de zona?

Las políticas predeterminadas de zona son aplicaciones de acceso comodín `*.domain.com` que protegen TODOS los subdominios de una zona DNS, incluidos aquellos que aún no ha configurado explícitamente.

### Por qué los necesitas

**El problema:** Si olvida agregar una política de acceso a un servicio, se expone públicamente de forma predeterminada.

**La solución:** Una política comodín a nivel de zona actúa como red de seguridad. Incluso si olvida configurar `forgotten-service.yourdomain.com`, la política `*.yourdomain.com` seguirá protegiéndolo.

### Cómo configurarlos

1. Vaya a la página **Políticas de acceso**
2. Desplácese hasta la sección **Políticas predeterminadas de zona (*.tld comodines)**
3. Busque zonas con el distintivo "No protegido" ⚠️
4. Haga clic en **Crear política**
5. Seleccione el grupo de acceso apropiado:
   - **Para dominios públicos:** Utilice `public-default-bypass`
   - **Para dominios internos:** Utilice una política de autenticación
   - **Para uso mixto:** Utilice su póliza más restrictiva

### Mejores prácticas

- ✅ **Crear siempre políticas de zona** para dominios de producción
- ✅ **Usar políticas de autenticación** para zonas internas/privadas
- ✅ **Use acceso público por omisión** solo para zonas verdaderamente públicas
- ✅ **Revisar periódicamente** - comprobar el estado de protección de la zona mensualmente
- ⚠️ **Recordar prioridad** - Las políticas de nombres de host específicas anulan las políticas de comodines

### Orden de prioridad de políticas

Cloudflare evalúa las políticas de acceso en este orden:

1. **Coincidencia exacta del nombre de host** (p. ej., `app.example.com`): máxima prioridad
2. **Coincidencia con comodines** (p. ej., `*.example.com`): respaldo
3. **No hay coincidencia** = Acceso público (sin aplicación de acceso) - Predeterminado

Esto significa que puede tener una política predeterminada de zona restrictiva y aun así crear excepciones específicas para servicios individuales.

---

## Gestión de políticas externas de Cloudflare

### Comprensión de los tipos de políticas

DockFlare muestra tres tipos de políticas en la página Políticas de acceso, cada una con una insignia visual:

- **🟦 DockFlare** - Políticas creadas y administradas por DockFlare (prefijo: `DockFlare-`)
- **🟪 Externo** - Políticas creadas fuera de DockFlare (manual u otras herramientas)
- **🟧 Sistema** - Políticas del sistema no eliminables (`public-default-bypass`, `authenticated-default`)

### Sincronización de políticas externas

De forma predeterminada, DockFlare solo importa políticas con el prefijo `DockFlare-`. Esto mantiene su lista de políticas limpia y centrada en la infraestructura de contenedores.

**Para sincronizar TODAS las políticas de Cloudflare** (incluidas las creadas manualmente):

1. Establezca la variable de entorno: `SYNC_ALL_CLOUDFLARE_POLICIES=true`
2. Reinicie DockFlare
3. Haga clic en **"Sincronizar desde Cloudflare"** en la página Políticas de acceso.

Las políticas externas aparecerán con una insignia violeta **"Externa"**.

### ¿Por qué importar políticas externas?

**Ventajas:**
- Visibilidad completa de toda su configuración de Cloudflare Access
- Reutilizar políticas existentes sin recrearlas
- Gestión centralizada en una interfaz
- Aplicar cualquier política a cualquier servicio (administrado por DockFlare o no)

**Desventajas:**
- Lista de políticas más larga si tiene muchas políticas externas
- Riesgo de modificar accidentalmente las políticas utilizadas por servicios que no son de DockFlare

### Organización de sus políticas

**Consejo:** Cambie el nombre de las políticas externas en Cloudflare para usar el prefijo `DockFlare-`

Puede organizar políticas externas cambiándoles el nombre en el panel de Cloudflare:

1. Abra la política en **Cloudflare Zero Trust**
2. Cambie el nombre para usar el prefijo `DockFlare-` (por ejemplo, `DockFlare-LegacyVPN` o `DockFlare-ThirdPartyApp`)
3. Haga clic en **"Sincronizar desde Cloudflare"** en DockFlare
4. La política ahora aparece como una política **administrada por DockFlare** (insignia azul)

Esto le permite:
- ✅ Agrupe todas las políticas visibles de DockFlare con nombres consistentes
- ✅ Filtrar y ordenar pólizas por tipo
- ✅ Distinguir "administrado por DockFlare" de "apenas visible en DockFlare"

### Políticas de filtrado

Utilice el menú desplegable **Filtro** para ver tipos de políticas específicas:

- **Todas las políticas** - Muestra todo (DockFlare, Externo, Sistema)
- **DockFlare-Managed** - Muestra solo políticas con insignia azul
- **Externo**: muestra solo políticas con insignia violeta
- **Sistema** - Muestra solo políticas del sistema

### Funciones de seguridad

**Protección de política externa:**

Al eliminar o editar políticas externas, DockFlare muestra una advertencia:

> ⚠️ ADVERTENCIA: Esta es una política EXTERNA no creada por DockFlare.
>
> La modificación de esta política puede afectar los servicios fuera de DockFlare.
>
> ¿Estás absolutamente seguro?

Esto evita cambios accidentales en las políticas administradas por otras herramientas o configuraciones manuales.

### Mejores prácticas

1. **Configuración predeterminada (recomendada):**
   - Mantener `SYNC_ALL_CLOUDFLARE_POLICIES=false` (predeterminado)
   - Sólo aparecen políticas administradas por DockFlare
   - Lista de políticas limpia y enfocada

2. **Configuración avanzada (usuarios avanzados):**
   - Habilitar `SYNC_ALL_CLOUDFLARE_POLICIES=true`
   - Ver y administrar TODAS las políticas en un solo lugar
   - Cambiar el nombre de las políticas externas al prefijo `DockFlare-` para la organización

3. **Enfoque híbrido:**
   - Mantener la sincronización desactivada de forma predeterminada
   - Cambiar manualmente el nombre de políticas externas importantes a `DockFlare-*` en Cloudflare
   - Aparecerán automáticamente después de la próxima sincronización.

4. **Convención de nomenclatura de políticas:**
   ```
   DockFlare-AccessGroup-<id>     # Auto-generated by access groups
   DockFlare-<custom-name>         # Your renamed external policies
   <anything-else>                 # Pure external (only visible if sync enabled)
   ```
