# Proveedores de identidad

> **📌 Importante:** Esta guía sirve para configurar **proveedores de identidad para las políticas de acceso de Cloudflare** con el fin de proteger sus servicios y aplicaciones. Si desea configurar OAuth/OIDC para **iniciar sesión en la interfaz web de DockFlare**, consulte [Configuración del proveedor OAuth](OAuth-Provider-Setup.md).

Los proveedores de identidad (IdP) habilitan la autenticación OAuth/OIDC para sus aplicaciones protegidas con Cloudflare Zero Trust. DockFlare facilita la gestión de los IdP y su integración en las políticas de acceso.

## Resumen

En lugar de depender únicamente de la autenticación basada en correo electrónico, puede utilizar proveedores OAuth populares como Google, GitHub, Azure AD y otros. Los usuarios se autentican con sus cuentas existentes, lo que ofrece una experiencia de inicio de sesión fluida y segura.

## Proveedores compatibles

DockFlare admite los siguientes proveedores de identidad:

- **Google** - Cuentas personales de Google
- **Google Workspace** - Cuentas de Google Workspace (G Suite) con restricción de dominio opcional
- **Microsoft Azure AD** - Microsoft Entra ID (Azure Active Directory)
- **Okta** - Okta Identity Cloud
- **GitHub** - GitHub OAuth
- **OpenID Connect genérico** - Cualquier proveedor compatible con OIDC

## Gestión de proveedores de identidad

### Agregar un proveedor de identidad

1. Vaya a la página **Políticas de acceso**.
2. En la sección **Proveedores de identidad**, haga clic en **Agregar proveedor**.
3. Complete los campos obligatorios:
   - **Nombre descriptivo**: nombre interno de DockFlare, por ejemplo `google-main` o `github-dev`
   - **Nombre para mostrar**: nombre que se muestra en el panel de Cloudflare
   - **Tipo de proveedor**: seleccione su proveedor OAuth
   - **Configuración**: credenciales específicas del proveedor, según las guías de configuración siguientes
4. Haga clic en **Crear proveedor**.
5. Pruebe el proveedor con la URL de prueba proporcionada.

### Sincronizar desde Cloudflare

Si ya ha configurado IdP en Cloudflare Zero Trust:

1. Haga clic en **Sincronizar desde Cloudflare** dentro de la sección Proveedores de identidad.
2. DockFlare importará todos los IdP existentes y generará automáticamente nombres descriptivos.
3. Puede cambiar esos nombres descriptivos para que resulten más fáciles de usar en etiquetas.

### Probar un proveedor de identidad

Después de crear un IdP, puede probarlo:

1. Haga clic en el menú **⋮** junto al proveedor.
2. Seleccione **Probar IdP**.
3. Se abrirá una nueva ventana para autenticarse.
4. Compruebe que el flujo de inicio de sesión funcione correctamente.

## Guías de configuración del proveedor

### Google (cuentas personales)

**Paso 1: Crear credenciales OAuth**

1. Vaya a [Google Cloud Console](https://console.cloud.google.com/).
2. Cree un nuevo proyecto o seleccione uno existente.
3. Vaya a **API y servicios** → **Credenciales**.
4. Haga clic en **Crear credenciales** → **ID de cliente OAuth**.
5. Seleccione **Aplicación web**.
6. Añada el URI de redirección autorizado:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Puede encontrar el nombre de su equipo en <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, en Configuración > Páginas personalizadas.</small>
7. Copie el **ID de cliente** y el **secreto de cliente**.

**Paso 2: Configurar en DockFlare**

- **ID de cliente**: pegue el valor desde Google Cloud Console
- **Secreto de cliente**: pegue el valor desde Google Cloud Console

---

### Google Workspace

Igual que la configuración de Google anterior, con un campo opcional adicional:

- **Apps Domain**: (opcional) restrinja el acceso a un dominio concreto, por ejemplo `example.com`

Si se especifica, solo podrán autenticarse usuarios con direcciones de correo `@example.com`.

---

### Microsoft Azure AD

**Paso 1: Registrar la aplicación en Azure**

1. Vaya al [Portal de Azure](https://portal.azure.com/).
2. Vaya a **Azure Active Directory** → **Registros de aplicaciones**.
3. Haga clic en **Nuevo registro**.
4. Asigne un nombre a la aplicación, por ejemplo `DockFlare Access`.
5. En **URI de redirección**, seleccione **Web** e introduzca:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Puede encontrar el nombre de su equipo en <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, en Configuración > Páginas personalizadas.</small>
6. Haga clic en **Registrar**.
7. Copie el **ID de aplicación (cliente)**.
8. Copie el **ID de directorio (tenant)**.
9. Vaya a **Certificados y secretos** → **Nuevo secreto de cliente**.
10. Cree un secreto y copie el **valor**.

**Paso 2: Configurar en DockFlare**

- **ID de aplicación (cliente)**: pegue el valor desde Azure
- **ID de directorio (tenant)**: pegue el valor desde Azure
- **Secreto de cliente**: pegue el valor desde Azure

---

### GitHub

**Paso 1: Crear la aplicación OAuth**

1. Vaya a [Configuración de desarrollador de GitHub](https://github.com/settings/developers).
2. Haga clic en **Nueva aplicación OAuth**.
3. Complete los detalles:
   - **Nombre de la aplicación**: DockFlare Access
   - **URL de la página principal**: `https://your-domain.com`
   - **URL de devolución de llamada de autorización**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>Puede encontrar el nombre de su equipo en <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, en Configuración > Páginas personalizadas.</small>
4. Haga clic en **Registrar aplicación**.
5. Copie el **ID de cliente**.
6. Haga clic en **Generar un nuevo secreto de cliente** y cópielo.

**Paso 2: Configurar en DockFlare**

- **ID de cliente**: pegue el valor desde GitHub
- **Secreto de cliente**: pegue el valor desde GitHub

---

### Okta

**Paso 1: Crear una aplicación en Okta**

1. Inicie sesión en su [Consola de administración de Okta](https://admin.okta.com/).
2. Vaya a **Aplicaciones** → **Crear integración de aplicaciones**.
3. Seleccione **OIDC - OpenID Connect**.
4. Elija **Aplicación web**.
5. Configure:
   - **URI de redirección de inicio de sesión**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>Puede encontrar el nombre de su equipo en <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, en Configuración > Páginas personalizadas.</small>
6. Haga clic en **Guardar**.
7. Copie el **ID de cliente** y el **secreto de cliente**.
8. Anote su **dominio de Okta**, por ejemplo `https://dev-12345.okta.com`.

**Paso 2: Configurar en DockFlare**

- **URL de la cuenta de Okta**: su dominio de Okta, por ejemplo `https://dev-12345.okta.com`
- **ID de cliente**: pegue el valor desde Okta
- **Secreto de cliente**: pegue el valor desde Okta

---

### OpenID Connect genérico

Para cualquier proveedor compatible con OIDC:

**Paso 1: Obtener la configuración del proveedor**

En la documentación de su IdP, obtenga:
- URL de autorización
- URL del token
- URL de JWKS (JSON Web Key Set)
- ID de cliente
- Secreto de cliente

**Paso 2: Configurar en DockFlare**

- **URL de autorización**: endpoint OAuth de autorización del proveedor
- **URL del token**: endpoint del token del proveedor
- **URL de JWKS**: endpoint JWKS del proveedor, utilizado para verificar firmas
- **ID de cliente**: el valor proporcionado por su proveedor
- **Secreto de cliente**: el valor proporcionado por su proveedor

---

## Uso de proveedores de identidad en las políticas de acceso

### En grupos de acceso

1. Vaya a **Políticas de acceso** → **Políticas de acceso avanzadas**.
2. Haga clic en **Crear nuevo grupo** o edite un grupo existente.
3. En la sección **Reglas de política**:
   - **Proveedores de identidad**: seleccione uno o más IdP
   - **Correos o dominios permitidos**: **obligatorio cuando se usan IdP**. Especifique las direcciones de correo autorizadas.
4. Guarde el grupo.

### Modos de autenticación

Tiene dos opciones:

1. **Solo correo electrónico**: introduzca direcciones de correo y no seleccione ningún IdP. Los usuarios se autentican mediante un PIN de un solo uso.
2. **IdP + correo electrónico (obligatorio)**: seleccione uno o más IdP e introduzca correos permitidos. Los usuarios deben autenticarse mediante el IdP seleccionado y además figurar en la lista de correos autorizados.

**⚠️ Aviso de seguridad:** cuando utilice proveedores de identidad, **debe** especificar las direcciones de correo permitidas. Esto evita accesos no autorizados. Por ejemplo, sin restricciones por correo, seleccionar `Google` como IdP permitiría el acceso a cualquier persona con una cuenta de Google.

### En etiquetas de Docker

Utilice el nombre descriptivo en las etiquetas de sus contenedores:

```yaml
services:
  myapp:
    image: myapp:latest
    labels:
      dockflare.enable: "true"
      dockflare.hostname: "app.example.com"
      dockflare.access.group: "my-access-group"
```

El grupo de acceso `my-access-group` resolverá automáticamente los nombres descriptivos de IdP a UUID de Cloudflare.

---

## Mejores prácticas

### Convenciones de nombres

Utilice nombres descriptivos y claros:
- ✅ `google-main`, `github-dev`, `azure-work`
- ❌ `idp1`, `test`, `new`

### Seguridad

- **Rote los secretos periódicamente**: actualice los secretos de cliente con regularidad
- **Limite el alcance**: para Google Workspace y Azure AD, restrinja el acceso a dominios concretos siempre que sea posible
- **Pruebe antes de producción**: pruebe siempre los IdP antes de aplicarlos a servicios de producción
- **Supervise el uso**: revise los registros de Cloudflare para detectar intentos de acceso no autorizados

### Múltiples entornos

Cree IdP separados para distintos entornos:
- `google-dev` - Entorno de desarrollo
- `google-staging` - Entorno de staging
- `google-prod` - Entorno de producción

### Requisitos de correo con IdP

**IMPORTANTE:** la autenticación mediante IdP siempre requiere restricciones por correo electrónico por motivos de seguridad.

**Ejemplo de grupo de acceso:**
- **Proveedores de identidad**: `google-main`
- **Correos permitidos**: `admin@example.com, user@example.com, @contractor-domain.com`

Esta configuración permite el acceso a usuarios que:
- Se autentican mediante el IdP `google-main` (Google OAuth) **Y**
- Tienen una dirección de correo que coincide con `admin@example.com`, `user@example.com` o cualquier dirección de `@contractor-domain.com`

**Cómo funciona:**
1. El usuario hace clic en iniciar sesión en la aplicación protegida.
2. Se redirige al inicio de sesión de Google OAuth.
3. Después de autenticarse con Google, Cloudflare comprueba si el correo está en la lista permitida.
4. Solo se concede acceso si el correo coincide con la lista autorizada.

---

## Solución de problemas

### Error "URI de redirección no válido"

**Causa**: el URI de redirección configurado en el proveedor OAuth no coincide con el esperado por Cloudflare.

**Solución**: asegúrese de haber añadido exactamente este URI:
```
https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
```
<small>Puede encontrar el nombre de su equipo en <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, en Configuración > Páginas personalizadas.</small>

Sustituya `<your-team>` por el nombre de su equipo de Cloudflare Zero Trust.

---

### "La prueba del IdP falló"

**Causa**: credenciales incorrectas o configuración errónea.

**Solución**:
1. Verifique que el ID de cliente y el secreto de cliente sean correctos.
2. Compruebe que la aplicación OAuth esté habilitada en su proveedor.
3. En Azure AD, verifique tanto el ID de cliente como el ID de tenant.
4. Pruebe el proveedor con la URL de prueba de Cloudflare.

---

### "No se puede eliminar el IdP gestionado por el sistema"

**Causa**: se está intentando eliminar el proveedor integrado de PIN de un solo uso.

**Solución**: el proveedor `onetimepin` está gestionado por el sistema y no se puede eliminar. Es necesario para la autenticación OTP basada en correo electrónico.

---

### "IdP no encontrado en la etiqueta de Docker"

**Causa**: se está usando el UUID de Cloudflare en lugar del nombre descriptivo en la etiqueta.

**Solución**: utilice el nombre descriptivo, por ejemplo `google-main`, en lugar del UUID en la configuración del grupo de acceso.

---

## Documentación relacionada

- [Mejores prácticas de políticas de acceso](Access-Policy-Best-Practices.md)
- [Políticas predeterminadas de zona](Zone-Default-Policies.md)
- [Etiquetas de contenedor](Container-Labels.md)
- [Arquitectura de seguridad](Security-Architecture.md)

---
