# Acceso a la interfaz web

Una vez que el contenedor DockFlare se haya iniciado correctamente, podrá acceder a la interfaz web para administrar su configuración, ver el estado de sus túneles y configurar manualmente reglas ingress.

## URL predeterminada

De forma predeterminada, se puede acceder a la interfaz web de DockFlare en el puerto `5000`. Para entrar, abra el navegador y vaya a la siguiente URL:

```
http://<your-server-ip>:5000
```

Reemplace `<your-server-ip>` con la dirección IP del servidor donde se ejecuta DockFlare.

## Configuración por primera vez

La primera vez que acceda a la interfaz web, el **asistente de configuración inicial** lo guiará. Este asistente le ayuda a:

1. Restaurar desde un archivo de copia de seguridad de DockFlare existente (`dockflare_backup_*.zip`). Si elige esta opción, el sistema importa sus claves cifradas de configuración, estado y agente y luego reinicia automáticamente el contenedor para aplicarlas.
2. Crear una cuenta de administrador y una contraseña para la interfaz web.
3. Proporcione su ID de cuenta de Cloudflare, ID de zona (opcional) y token de API.
4. Confirme la configuración del túnel y complete los pasos de incorporación.

## Iniciar sesión

Después de la configuración inicial, verá una pantalla de inicio de sesión cada vez que acceda a la interfaz web. Utilice la contraseña que creó durante el proceso de configuración para iniciar sesión.

## Deshabilitar el inicio de sesión con contraseña

DockFlare incluye la configuración "Disable Password Login" destinada a implementaciones avanzadas donde DockFlare está protegido por una capa de autenticación externa (como Cloudflare Access). **Recomendamos encarecidamente no utilizar esta función** para la mayoría de las implementaciones.

### Por qué existe esta configuración

Si ejecuta DockFlare detrás de Cloudflare Access u otro proxy de autenticación que aplique SSO antes de llegar a la aplicación, puede desactivar el inicio de sesión con contraseña integrado de DockFlare para evitar la doble autenticación.

### Riesgos de seguridad cuando está habilitado

- ⚠️ **Todos los puntos finales de API se vuelven accesibles sin autenticación** cuando esta configuración está habilitada
- ⚠️ **Exposición de la red Docker:** Incluso si DockFlare está detrás de Cloudflare Access en la Internet pública, los contenedores en la misma red Docker pueden evitar la autenticación externa y acceder a la API de DockFlare directamente.
- ⚠️ **Sin aplicación de autenticación:** La aplicación asume que la autenticación externa se encarga de la seguridad.

### Ejemplo de vector de ataque

```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

Incluso cuando DockFlare está protegido por Cloudflare Access desde Internet, cualquier contenedor que se ejecute en la misma red Docker puede evitar esa protección y acceder directamente a los puntos finales API de DockFlare sin autenticación.

### Enfoque recomendado

En lugar de desactivar la autenticación de contraseña, utilice una de estas opciones seguras:

1. **Credenciales locales de DockFlare**: autenticación de contraseña simple integrada en DockFlare
2. **Proveedores de OAuth/OIDC**: configure Google, GitHub, Azure AD u otros proveedores de identidad para un inicio de sesión único sencillo sin sacrificar la seguridad (consulte [Configuración del proveedor de OAuth](OAuth-Provider-Setup.md)).

Ambas opciones proporcionan una autenticación adecuada y al mismo tiempo mantienen la comodidad del SSO. La opción OAuth le brinda la experiencia de inicio de sesión único sin los riesgos de seguridad de la autenticación deshabilitada.

### Conclusión

A menos que tenga una arquitectura de seguridad muy específica y bien entendida con aislamiento de red, mantenga habilitado el inicio de sesión con contraseña y use OAuth para su comodidad.
