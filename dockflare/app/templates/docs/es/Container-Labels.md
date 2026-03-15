# Referencia de etiquetas de contenedores

DockFlare se configura principalmente a través de etiquetas Docker adjuntas a sus contenedores. Esta página proporciona una referencia completa para todas las etiquetas compatibles.

## Configuración básica

Estas etiquetas controlan el enrutamiento fundamental y la definición de servicio de un contenedor.

| Etiqueta | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `dockflare.enable` | **Obligatorio.** El interruptor principal. Debe configurarse en `true` para que DockFlare administre el contenedor. | `dockflare.enable=true` |
| `dockflare.hostname` | **Obligatorio.** El nombre de host público de su servicio. | `dockflare.hostname=myservice.example.com` |
| `dockflare.service` | **Obligatorio.** La URL interna del servicio al que debe conectarse Cloudflare Tunnel. Puede ser `http`, `https`, `tcp`, `ssh`, `rdp`, `http_status:XXX` o `bastion`. | `dockflare.service=http://my-app-container:8080` |
| `dockflare.path` | La ruta URL para dirigirse a este servicio. Útil para exponer múltiples servicios en el mismo nombre de host. | `dockflare.path=/api` |
| `dockflare.zonename` | (Opcional) Zona (dominio) explícita de Cloudflare donde se debe crear el registro DNS. Si se omite, DockFlare ahora detecta automáticamente la zona según el nombre de host y solo recurre al valor predeterminado configurado (`CF_ZONE_ID`) cuando falla la detección automática. | `dockflare.zonename=another-domain.com` |
| `dockflare.no_tls_verify` | Si se establece en `true`, deshabilita la verificación del certificado TLS para la conexión entre `cloudflared` y su servicio de origen. Útil para orígenes con certificados autofirmados. | `dockflare.no_tls_verify=true` |
| `dockflare.originsrvname` | Establece un nombre de host de indicación de nombre de servidor (SNI) específico para la conexión TLS al origen. Esto también se conoce como "Nombre del servidor de origen" en el panel de Cloudflare. | `dockflare.originsrvname=internal.service.local` |
| `dockflare.httpHostHeader` | Anula el encabezado `Host` enviado desde `cloudflared` a su servicio de origen. | `dockflare.httpHostHeader=custom-host.internal` |
| `dockflare.http2_origin` | Si se establece en `true`, habilita el protocolo HTTP/2 para la conexión entre `cloudflared` y su servicio de origen. Requerido para los servicios gRPC. Solo se aplica a servicios HTTP/HTTPS. | `dockflare.http2_origin=true` |
| `dockflare.disable_chunked_encoding` | Si se establece en `true`, deshabilita la codificación de transferencia fragmentada a través de HTTP/1.1. Útil para servidores WSGI (Flask, Django, FastAPI) y otros orígenes que no admiten adecuadamente solicitudes fragmentadas. Solo se aplica a servicios HTTP/HTTPS. | `dockflare.disable_chunked_encoding=true` |

> **Consejo:** A partir de DockFlare v3.0, puede omitir `dockflare.zonename` para la mayoría de las cargas de trabajo. El Master detecta la zona correcta de Cloudflare al hacer coincidir el sufijo del nombre de host y solo vuelve a la zona predeterminada configurada cuando no puede encontrar una coincidencia. Proporcione la etiqueta cuando intencionalmente desee colocar un registro en una zona diferente.

> **Nota:** La opción **Hacer coincidir SNI con el host** de Cloudflare está disponible en la configuración manual de reglas de DockFlare en el panel. Actualmente no está configurado a través de una etiqueta de Docker.

---

## Configuración de la política de acceso

Estas etiquetas le permiten crear y administrar dinámicamente aplicaciones de Cloudflare Access para proteger sus servicios.

**Nota:** Se recomienda encarecidamente utilizar **Grupos de acceso** (`dockflare.access.group`) para administrar políticas. DockFlare 3.0.3 sincroniza cada grupo de acceso con una política de acceso de Cloudflare reutilizable con nombre, lo que le brinda reutilización de uno a muchos y ediciones bidireccionales. El uso de etiquetas individuales es mejor para configuraciones únicas y únicas. Si se utiliza `dockflare.access.group` o `dockflare.access.groups`, todas las demás etiquetas `dockflare.access.*` se ignoran.

### Cambios importantes en v3.0.3

#### Política de omisión predeterminada del sistema

A partir de v3.0.3, cuando utilice `dockflare.access.policy=bypass` o `dockflare.access.group=bypass`, su servicio hará referencia a la política reutilizable `public-default-bypass` administrada por el sistema en lugar de crear una política en línea. Esto mantiene limpio su panel de Cloudflare.

- **Antes de v3.0.3:** Cada regla de omisión creaba una política en línea separada
- **v3.0.3+:** Todas las reglas de omisión comparten una política canónica `public-default-bypass`

#### Migración de etiquetas heredadas

DockFlare migra automáticamente las etiquetas de derivación heredadas para utilizar la política del sistema centralizado:

- `dockflare.access.policy=bypass` → Utiliza la política del sistema `public-default-bypass`
- `dockflare.access.group=bypass` → Utiliza la política del sistema `public-default-bypass`

La migración se produce de forma transparente durante el procesamiento y la conciliación del contenedor. Sus contenedores seguirán funcionando sin necesidad de cambios.

#### Configuración de acceso simplificado

Para escenarios de acceso complejos (autenticación de correo electrónico/dominio, lista blanca de IP, etc.), ahora se recomienda:

1. Cree un grupo de acceso en la página **Políticas de acceso**
2. Referenciarlo con `dockflare.access.group=your-group-id`

Se eliminaron las opciones de creación rápida de la interfaz web para fomentar este flujo de trabajo recomendado.

#### Etiqueta de política predeterminada de zona

La etiqueta `dockflare.access.policy=default_tld` aún funciona y heredará la protección de la política de comodines `*.domain.com` de su zona. Si no existe una política de zona, el servicio será público (sin aplicación Access).

**Recomendación:** Cree políticas de zona predeterminadas para todos sus dominios en la interfaz web para mejorar la seguridad.

| Etiqueta | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `dockflare.access.group` | El ID de un único grupo de acceso preconfigurado para aplicar a este servicio. Puede encontrar ese identificador en la página "Access Policies" de la interfaz web de DockFlare. | `dockflare.access.group=internal-tools-policy` |
| `dockflare.access.groups` | Una lista separada por comas de ID de grupo de acceso que se aplicarán. Esto le permite superponer varias políticas en un solo servicio. | `dockflare.access.groups=allow-team-a,allow-admins` |
| `dockflare.access.policy` | El tipo de política principal. Puede ser `bypass` (público), `authenticate` (requiere inicio de sesión) o `default_tld` (hereda de una política `*.domain.com`). Si no se configura, el servicio será público. Prefiera grupos de acceso para políticas reutilizables; estas etiquetas son para anulaciones especializadas. | `dockflare.access.policy=authenticate` |
| `dockflare.access.name` | Un nombre personalizado para la aplicación Cloudflare Access. El valor predeterminado es `DockFlare-{hostname}`. | `dockflare.access.name=My Web App Access` |
| `dockflare.access.session_duration` | La duración de la sesión para usuarios autenticados (por ejemplo, `24h`, `30m`). El valor predeterminado es `24h`. | `dockflare.access.session_duration=1h` |
| `dockflare.access.app_launcher_visible` | Si es `true`, hace que la aplicación sea visible en el iniciador de aplicaciones de Cloudflare Access. | `dockflare.access.app_launcher_visible=true` |
| `dockflare.access.allowed_idps` | Una lista separada por comas de UUID de proveedores de identidad (IdP) permitidos. Puede encontrarlos en su panel de Cloudflare Zero Trust. | `dockflare.access.allowed_idps=uuid1,uuid2` |
| `dockflare.access.auto_redirect_to_identity` | Si es `true`, los usuarios serán redirigidos inmediatamente a la página de inicio de sesión del IdP en lugar de a la página de presentación de Cloudflare Access. | `dockflare.access.auto_redirect_to_identity=true` |
| `dockflare.access.custom_rules` | Una cadena JSON que representa una serie de reglas de política de acceso de Cloudflare. Esto proporciona la máxima flexibilidad para políticas complejas y únicas. | `dockflare.access.custom_rules='[{"email":{"email":"user@example.com"},"action":"allow"}]'` |

---

## Etiquetas indexadas para múltiples dominios

DockFlare admite la definición de múltiples nombres de host para un solo contenedor utilizando etiquetas indexadas. Esto es útil para exponer diferentes puertos o rutas del mismo servicio en diferentes nombres de host públicos.

Para utilizar etiquetas indexadas, anteponga la etiqueta con un número entero, comenzando desde `0`.

* Siempre se requiere un nombre de host indexado (`<index>.hostname`).
* Otras etiquetas en el mismo índice (por ejemplo, `<index>.service`, `<index>.path`) anularán las etiquetas base (no indexadas) para ese nombre de host específico.
* Si no se proporciona una etiqueta indexada, volverá al valor de la etiqueta base correspondiente.

### Ejemplo

Este ejemplo expone dos nombres de host de un único contenedor:
1. `app.example.com` enruta a la interfaz web principal en el puerto `80`.
2. `api.example.com` enruta a la API en el puerto `3000` y está protegido con un grupo de acceso específico.

```yaml
services:
  my-multi-service:
    image: my-app
    labels:
      - "dockflare.enable=true"

      # --- Definition 0 ---
      - "dockflare.0.hostname=app.example.com"
      - "dockflare.0.service=http://my-multi-service:80"

      # --- Definition 1 ---
      - "dockflare.1.hostname=api.example.com"
      - "dockflare.1.service=http://my-multi-service:3000"
      - "dockflare.1.access.group=api-access-policy"
```
