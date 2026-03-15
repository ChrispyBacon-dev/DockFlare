# ¡Bienvenido a la documentación de DockFlare!

DockFlare es un potente controlador ingress autohospedado que simplifica la administración de Cloudflare Tunnel y Zero Trust. Utiliza etiquetas Docker para la configuración automatizada y, al mismo tiempo, proporciona una interfaz web sólida para definiciones manuales de servicios y ajustes de políticas.

Esta documentación proporciona información completa sobre DockFlare. Ya seas un usuario nuevo o experimentado, encontrarás todo lo que necesitas saber para aprovechar DockFlare al máximo.

## Tabla de contenidos

* **[Inicio](Home.md)**
* **Primeros pasos**
    * [Requisitos previos](Prerequisites.md)
    * [Inicio rápido (Docker Compose)](Quick-Start-Docker-Compose.md)
    * [Acceso a la interfaz web](Accessing-the-Web-UI.md)
* **Conceptos básicos**
    * [Cómo funciona DockFlare](How-DockFlare-Works.md)
    * [Agente DockFlare y arquitectura multiservidor](Multi-Server-Agent.md)
    * [Mejores prácticas de política de acceso](Access-Policy-Best-Practices.md)
    * [Políticas predeterminadas de zona](Zone-Default-Policies.md)
    * [Interno vs Externo `cloudflared`](Internal-vs-External-cloudflared.md)
    * [Persistencia del estado](State-Persistence.md)
* **Configuración**
    * [Etiquetas de contenedor](Container-Labels.md)
    * [Proveedores de identidad](Identity-Providers.md)
    * [Configuración del proveedor OAuth](OAuth-Provider-Setup.md)
* **Guía de uso**
    * [Uso básico (dominio único)](Basic-Usage-Single-Domain.md)
    * [Uso de varios dominios (etiquetas indexadas)](Using-Multiple-Domains-Indexed-Labels.md)
    * [Uso de dominios comodín](Using-Wildcard-Domains.md)
    * [Administración de zonas DNS](Managing-DNS-Zones.md)
    * [Comprensión de la eliminación ordenada](Understanding-Graceful-Deletion.md)
    * [Uso de la interfaz web](Using-the-Web-UI.md)
    * [Copia de seguridad y restauración](Backup-and-Restore.md)
* **Temas avanzados**
    * [Modo `cloudflared` externo](External-cloudflared-Mode.md)
    * [Cambiar entre modos](Switching-Between-Modes.md)
    * [Monitoreo con Prometheus y Grafana](Monitoring-with-Prometheus-&-Grafana.md)
    * [Ajuste de rendimiento](Performance-Tuning.md)
    * [Política de seguridad de contenido (CSP)](Content-Security-Policy.md)
    * [Arquitectura y refuerzo de seguridad](Security-Architecture.md)
* **Solución de problemas**
    * [Problemas comunes](Common-Issues.md)
    * [Depuración y registros](Debugging-&-Logs.md)
    * [Comprobaciones de estado](Health-Checks.md)
    * [Utilidades CLI](CLI-Utilities.md)
* **[Contribuir](Contributing.md)**
* **[Licencia](License.md)**
