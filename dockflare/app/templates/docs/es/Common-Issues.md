# Problemas comunes

Esta página enumera algunos de los problemas comunes que los usuarios pueden encontrar y cómo resolverlos.

---

### Problema: El contenedor DockFlare no se inicia o está en un ciclo de reinicio.

**Solución:**
1. **Verifique los registros de Docker:** El primer paso es siempre verificar los registros del contenedor DockFlare. Ejecute el siguiente comando:
    ```bash
    docker logs dockflare
    ```
2. **Buscar errores:** Busque cualquier mensaje de error. Las causas comunes incluyen:
    * Un archivo `docker-compose.yml` no válido (por ejemplo, sintaxis incorrecta, problemas de montaje de volumen).
    * Problemas con el propio demonio Docker.
    * Problemas de conectividad o permisos con el servicio docker-socket-proxy o la configuración `DOCKER_HOST`.

---

### Problema: los registros DNS no se crean en Cloudflare.

**Solución:**
1. **Verifique los registros de DockFlare:** Busque cualquier mensaje de error relacionado con la API de Cloudflare. Los registros a menudo le dirán exactamente por qué falló la llamada a la API.
2. **Verifique los permisos del token API:** Esta es la causa más común. Asegúrese de que su token API de Cloudflare tenga los permisos necesarios. Como mínimo, necesitas:
    * `Zone:DNS:Edit` para cada zona que desee que administre DockFlare.
    * `Zone:Zone:Read`
3. **Verificar configuración de zona:**
    * Asegúrese de que el **ID de zona** que proporcionó durante la configuración sea correcto.
    * Si está utilizando la etiqueta `dockflare.zonename`, verifique que el nombre de la zona esté escrito correctamente.

---

### Problema: No se aplica una política de acceso (confianza cero) a un servicio.

**Solución:**
1. **Verifique los permisos del token API:** Asegúrese de que su token API tenga el permiso `Account:Access: Apps and Policies:Edit`.
2. **Compruebe si hay ajustes desde la interfaz web:** En el panel de DockFlare, verifique si la regla tiene un estado de "UI Override". Los ajustes aplicados desde la interfaz web tienen prioridad sobre las etiquetas.
3. **Verifique la ID del grupo de acceso:** Si está utilizando `dockflare.access.group`, asegúrese de que la ID que especificó en la etiqueta **exactamente** coincida con la ID que creó para el grupo de acceso en la página "Access Policies".
4. **Consulte el panel de Cloudflare:** Inicie sesión en su panel de Cloudflare Zero Trust. Navegue hasta **Acceso -> Aplicaciones** para ver si se creó la aplicación de Access. A veces, Cloudflare mostrará un error que no es visible en la respuesta de la API.

---

### Problema: Recibo un error `ERR_TOO_MANY_REDIRECTS` al intentar acceder a mi servicio.

**Solución:**
Este error casi siempre ocurre debido a una mala configuración de SSL/TLS entre su servicio de origen y Cloudflare.

1. **Verifique el modo SSL/TLS de Cloudflare:** En su panel de control de Cloudflare, vaya a la configuración de SSL/TLS para su dominio. Asegúrese de que su modo de cifrado esté configurado en **Completo (estricto)**.
2. **Evite redirecciones dobles:** El modo SSL "Flexible" en Cloudflare puede causar este problema si su aplicación backend también intenta redirigir de HTTP a HTTPS. El navegador se queda atascado en un bucle.
3. **Use `https` en la URL de su servicio:** Si su servicio backend admite HTTPS, use `https://` en su etiqueta `dockflare.service` (por ejemplo, `dockflare.service=https://my-app:443`). Esto garantiza que la conexión de `cloudflared` a su servicio también esté cifrada.

---

### Problema: Un servicio detrás de Traefik/Proxmox solo funciona cuando "Match SNI to Host" de Cloudflare está habilitado.

**Solución:**
1. Edite la regla manual en DockFlare y habilite **Match SNI to Host**.
2. Guarde la regla y verifique la ruta en Cloudflare Zero Trust.
3. Si también necesita que DockFlare mantenga los campos de ruta del lado de Cloudflare que DockFlare no modela, vaya a **Settings → General Settings** y habilite **Preserve Unmanaged Cloudflare Ingress Fields**.

---

### Problema: El contenedor administrado `cloudflared-agent` no se inicia con un error de "red obsoleta".

**Solución:**
Esto puede suceder si la red Docker que estaba usando el agente se eliminó y se volvió a crear. DockFlare está diseñado para manejar esto automáticamente.

1. **Reinicie DockFlare:** Un simple reinicio del contenedor DockFlare (`docker compose restart dockflare`) debería resolver este problema.
2. **Cómo funciona:** Al iniciar, DockFlare verifica el estado de su agente administrado. Si detecta este problema específico, eliminará automáticamente el contenedor del agente roto y creará uno nuevo con la configuración correcta. Este fue un error específico corregido en la versión `v1.9.5`. Asegúrese de tener una versión reciente de DockFlare.
