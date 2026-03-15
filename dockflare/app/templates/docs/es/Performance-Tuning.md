# Ajuste de rendimiento

Para la gran mayoría de usuarios, la configuración predeterminada de DockFlare proporciona un buen equilibrio entre rendimiento y utilización de recursos. Sin embargo, en entornos muy grandes o altamente dinámicos, puede resultar beneficioso ajustar algunos de los parámetros avanzados relacionados con el rendimiento.

Estas configuraciones se configuran a través de variables de entorno en su archivo `docker-compose.yml`.

---

## `CLEANUP_INTERVAL_SECONDS`

Esta variable controla la frecuencia con la que se ejecuta la tarea en segundo plano de DockFlare para limpiar recursos caducados (es decir, reglas de contenedores detenidos cuyo período de gracia ha transcurrido).

* **Predeterminado:** `60` segundos
* **Descripción:** Un intervalo más corto significa que los recursos obsoletos se eliminan más rápidamente de su configuración de Cloudflare. Un intervalo más largo reduce la frecuencia de las verificaciones de antecedentes, lo que puede reducir ligeramente el uso de recursos.
* **Cuándo realizar el ajuste:** Si tiene un entorno muy dinámico con muchos contenedores de corta duración y desea que sus recursos se limpien casi de inmediato, puede reducir este valor (por ejemplo, a `30`). Para la mayoría de los usuarios, el valor predeterminado está bien.

**Ejemplo:**
```yaml
environment:
  - CLEANUP_INTERVAL_SECONDS=30
```

---

## `MAX_CONCURRENT_DNS_OPS`

Esta variable establece el número máximo de operaciones DNS simultáneas (crear, eliminar) que DockFlare realizará al mismo tiempo.

* **Predeterminado:** `3`
* **Descripción:** Esta es una perilla de ajuste directo del rendimiento para entornos con una gran cantidad de servicios. Cuando se inicia DockFlare o cuando se inician muchos contenedores a la vez, esta configuración limita la cantidad de solicitudes paralelas que se realizan a la API de Cloudflare para cambios de DNS.
* **Cuándo realizar el ajuste:** Si administra cientos de servicios y observa que el inicio inicial o una implementación masiva tardan en crear todos los registros DNS, puede intentar aumentar este valor (por ejemplo, a `5` o `10`). Tenga en cuenta que establecer esto demasiado alto podría provocar una limitación de la tasa de API de Cloudflare.

**Ejemplo:**
```yaml
environment:
  - MAX_CONCURRENT_DNS_OPS=5
```

---

## `RECONCILIATION_BATCH_SIZE`

Esto controla el tamaño del lote para varias tareas de conciliación en segundo plano.

* **Predeterminado:** `3`
* **Descripción:** Algunas tareas en segundo plano en DockFlare procesan elementos en lotes para evitar sobrecargar el sistema o la API de Cloudflare. Esta configuración controla el tamaño de esos lotes.
* **Cuándo sintonizar:** Esta es una configuración muy avanzada. Para la mayoría de los usuarios, el valor predeterminado no se debe cambiar. Si tiene una cantidad extremadamente grande de reglas (muchos cientos o miles), puede experimentar con un tamaño de lote ligeramente mayor, pero generalmente no es necesario.

**Ejemplo:**
```yaml
environment:
  - RECONCILIATION_BATCH_SIZE=5
```

---

## `SCAN_ALL_NETWORKS`

Esta variable cambia la forma en que DockFlare descubre la dirección IP de los contenedores.

* **Predeterminado:** `false`
* **Descripción:** De forma predeterminada, DockFlare espera que el contenedor de destino esté en la misma red Docker que el propio DockFlare. Cuando `SCAN_ALL_NETWORKS` se establece en `true`, DockFlare inspeccionará todas las redes a las que está conectado un contenedor para encontrar una red compartida.
* **Cuándo realizar el ajuste:** Esto solo debe habilitarse si tiene una configuración de red Docker compleja donde los contenedores de aplicaciones no están en la misma red que DockFlare. Tenga en cuenta que habilitar esto puede tener un impacto en el rendimiento en entornos con una gran cantidad de redes Docker, ya que requiere más trabajo de inspección por parte de DockFlare.

**Ejemplo:**
```yaml
environment:
  - SCAN_ALL_NETWORKS=true
```
