## Configuración del proveedor OAuth

> **📌 Importante:** Esta guía es para configurar la **autenticación de la interfaz web de DockFlare**. Si desea configurar OAuth/OIDC para **políticas de acceso de Cloudflare** que protejan sus servicios, consulte [Proveedores de identidad](Identity-Providers.md).

DockFlare le permite delegar la autenticación de usuarios en proveedores externos mediante el estándar OpenID Connect (OIDC). Esto habilita el inicio de sesión único (SSO) para la interfaz web de DockFlare y facilita la integración con proveedores de identidad como Google, Authentik, Okta y otros.

### Agregar un nuevo proveedor

Siga estos pasos para agregar un nuevo proveedor de OIDC:

1. **Vaya a Configuración:** Desde el panel principal, abra la página **Configuración**.
2. **Busque la sección OAuth:** Desplácese hasta la sección **Autenticación OAuth**.
3. **Agregue el proveedor:** Haga clic en **Agregar proveedor** para abrir el formulario de configuración.

Se le presentarán los siguientes campos:

* **Tipo de proveedor:** Se establece en `OpenID Connect (OIDC)`, el estándar moderno para autenticación federada.
* **URL del emisor:** Es el campo más importante. Se trata de la URL base de su proveedor OIDC, que DockFlare usa para descubrir automáticamente la configuración del proveedor. Por ejemplo, `https://accounts.google.com` o `https://authentik.yourdomain.com/application/o/dockflare/`.
* **ID del proveedor:** Un nombre corto, único y en minúsculas para este proveedor (por ejemplo, `google`, `authentik-corp`). Este identificador se usa internamente y en la URL de devolución de llamada.
* **Nombre para mostrar:** El nombre que aparecerá en el botón de inicio de sesión (por ejemplo, `Google`, `Corporate SSO`).
* **ID de cliente:** El identificador público de la aplicación DockFlare, que obtendrá en la consola para desarrolladores de su proveedor OIDC.
* **Secreto del cliente:** El secreto confidencial de la aplicación DockFlare, también obtenido en la consola de su proveedor OIDC.
* **Habilitar proveedor:** Esta casilla permite activar o desactivar el proveedor en cualquier momento.

Cuando haya completado los campos, haga clic en **Agregar proveedor** para guardar la configuración.

### Encontrar su URL de devolución de llamada

Una vez agregado el proveedor, la **URL de devolución de llamada** necesaria (también llamada "URI de redirección autorizada") aparecerá debajo de la entrada del proveedor en la página Configuración.

Debe copiar exactamente esa URL y añadirla a la lista de URL de devolución de llamada permitidas en la consola de administración de su proveedor.

---

### Ejemplo: configurar Google

Esta es una guía rápida para configurar Google como proveedor OAuth.

1. **Vaya a Google Cloud Console:** Abra la página [API y servicios > Credenciales](https://console.cloud.google.com/apis/credentials).
2. **Crear credenciales:** Haga clic en **+ CREAR CREDENCIALES** y seleccione **ID de cliente OAuth**.
3. **Configure la aplicación:**
    * Establezca el **Tipo de aplicación** en **Aplicación web**.
    * Asigne un nombre, por ejemplo, "DockFlare".
4. **Agregar URI de redireccionamiento:**
    * En **URI de redireccionamiento autorizado**, haga clic en **+ AGREGAR URI**.
    * Introduzca la URL de devolución de llamada proporcionada por DockFlare. Tendrá un formato similar a `https://your-dockflare-domain.com/auth/google/callback`.
5. **Crear y copiar:** Haga clic en **CREAR**. Aparecerá una ventana con su **ID de cliente** y su **Secreto del cliente**. Copie esos valores.
6. **Configure DockFlare:**
    * **URL del emisor:** `https://accounts.google.com`
    * **ID del proveedor:** `google`
    * **Nombre para mostrar:** `Google`
    * **ID de cliente:** `(Your Client ID from Google)`
    * **Secreto del cliente:** `(Your Client Secret from Google)`

Guarde el proveedor en DockFlare y ya podrá iniciar sesión con su cuenta de Google.

---

### Configurar DockFlare con OAuth y políticas de acceso

Si usa autenticación OAuth, probablemente quiera proteger la interfaz web de DockFlare con políticas de acceso y, al mismo tiempo, permitir que las devoluciones de llamada de OAuth funcionen correctamente. Esto es especialmente importante si su instancia de DockFlare tiene restricciones por IP u otros controles de acceso.

#### **Buena práctica: política de bypass para devoluciones de llamada OAuth**

Utilice etiquetas indexadas para crear reglas separadas para la interfaz principal y para las rutas de devolución de llamada de OAuth:

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    labels:
      # Main DockFlare interface with access policy
      - "dockflare.enable=true"
      - "dockflare.hostname=dockflare.example.com"
      - "dockflare.service=http://dockflare:5000"
      - "dockflare.access.group=team"  # your custom access policy

      # OAuth callback paths with bypass policy (required for OAuth to work)
      - "dockflare.0.hostname=dockflare.example.com"
      - "dockflare.0.path=/auth/google/callback"
      - "dockflare.0.service=http://dockflare:5000"
      - "dockflare.0.access.policy=bypass"

      # Add additional callback paths for other providers if needed
      - "dockflare.1.hostname=dockflare.example.com"
      - "dockflare.1.path=/auth/github/callback"
      - "dockflare.1.service=http://dockflare:5000"
      - "dockflare.1.access.policy=bypass"
```

#### **Por qué esta configuración es necesaria**

- **Protección de la interfaz principal**: el panel de DockFlare sigue protegido por la política de acceso que haya elegido
- **Funcionamiento de OAuth**: las devoluciones de llamada de OAuth pueden llegar a DockFlare sin quedar bloqueadas por la autenticación
- **Seguridad**: solo se omiten rutas de devolución de llamada concretas, no toda la aplicación
- **Flexibilidad**: funciona con cualquier combinación de políticas de acceso, ya sean basadas en IP, autenticación u otros criterios

#### **Notas importantes**

1. **Coincidencia exacta de ruta**: la ruta de devolución de llamada debe coincidir exactamente con la que espera su proveedor OAuth.
2. **Varios proveedores**: agregue una regla indexada independiente para cada proveedor OAuth que configure.
3. **Sin comodines**: evite usar rutas con comodines por seguridad; defina URL de devolución de llamada específicas.
4. **Pruebas**: después de configurar todo, pruebe tanto el acceso protegido a la interfaz principal como los flujos de inicio de sesión OAuth.
