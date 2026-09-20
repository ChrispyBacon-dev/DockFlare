# Requisitos previos y configuración de la Suite de correo

Antes de activar la Suite de correo electrónico, asegúrese de que su entorno y su cuenta de Cloudflare estén correctamente configurados.

## Requisitos de Cloudflare

1.  **Gestión de dominio:** Su dominio debe estar activo en Cloudflare.
2.  **Email Routing (Entrante):** Cloudflare Email Routing está disponible en todos los planes, incluido el gratuito. DockFlare configura automáticamente los registros MX, SPF y DMARC necesarios.
3.  **Email Sending (Saliente):** Cloudflare Email Sending se encuentra actualmente en Beta. DockFlare configura automáticamente los registros de firma DKIM y el subdominio de envío. Sin embargo, el envío a direcciones externas requiere:
    - Un **Cloudflare Workers Paid Plan** (5 $/mes).
    - La activación manual de **CF Email Sending (Beta)** en el Panel de Cloudflare bajo **Email → Email Sending**.
    - Sin estos pasos, el correo saliente queda restringido a direcciones Cloudflare verificadas.
4.  **Almacenamiento R2:** R2 debe estar habilitado en su panel de Cloudflare. R2 incluye un nivel gratuito de 10 GB, pero es posible que deba agregar un método de pago para activarlo.

## Permisos del token API

La Suite de correo requiere permisos adicionales en su token API de DockFlare existente. Actualícelo en **Perfil de usuario > Tokens de API** añadiendo los siguientes permisos:

| Ámbito | Permiso específico | Nivel de acceso | Propósito |
| :--- | :--- | :--- | :--- |
| **Cuenta** | **Workers Scripts** | **Edición** | Despliegue de workers entrantes/salientes |
| **Cuenta** | **Workers KV Storage** | **Edición** | Aplicación de cuotas en tiempo real en el edge |
| **Cuenta** | **R2 Storage** | **Edición** | Creación y gestión de buckets de tránsito |
| **Cuenta** | **Access: Apps and Policies** | **Edición** | Crear una excepción para la ruta del webhook de correo entrante cuando Webmail está protegido por Cloudflare Access |
| **Zona** | **Email Routing** | **Edición** | Activación del enrutamiento y gestión de reglas |
| **Zona** | **DNS** | **Edición** | Creación de registros MX, SPF, DMARC y DKIM |

> **Nota de seguridad:** Se recomienda encarecidamente restringir los «Recursos de cuenta» y «Recursos de zona» de este token únicamente a la cuenta y los dominios específicos que desea usar con DockFlare.

## Requisitos del sistema

*   **DockFlare:** v3.1.0 o posterior.
*   **Docker:** v20.10+.
*   **Docker Compose:** v2.20+ (requerido para soporte de `profiles`).
*   **Almacenamiento:** Asegúrese de tener suficiente espacio en disco en la máquina host para el volumen `mail_data`, que almacenará todas las bases de datos de correo y los archivos adjuntos.
