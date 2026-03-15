# Comprender la Graceful Deletion

Cuando detienes un contenedor administrado por DockFlare, puedes notar que su nombre de host público correspondiente no se desconecta inmediatamente. Esto se debe a una función llamada **Graceful Deletion**.

## ¿Qué es la Graceful Deletion?

En lugar de eliminar instantáneamente la regla ingress de Cloudflare y el registro DNS en el momento en que se detiene un contenedor, DockFlare marca la regla como **"eliminación pendiente"** e inicia un temporizador.

Los recursos de Cloudflare asociados (la regla ingress y el registro DNS) solo se eliminarán permanentemente después de que expire este temporizador, conocido como **período de gracia**.

## ¿Por qué es útil?

Esta característica está diseñada para evitar interrupciones del servicio en escenarios operativos comunes:

* **Actualizaciones de contenedor:** Cuando actualiza una imagen de contenedor (`docker compose up -d`), Docker normalmente detiene el contenedor antiguo e inicia uno nuevo. Sin un período de gracia, su servicio estaría inaccesible por un corto tiempo. Con Graceful Deletion, el registro DNS y la regla ingress permanecen activos, y DockFlare simplemente los vuelve a asociar con el nuevo contenedor, lo que resulta en cero tiempo de inactividad.
* **Reinicios temporales:** Si necesita detener un contenedor por un momento para cambiar una configuración y luego reiniciarlo, el período de gracia garantiza que su configuración pública permanezca intacta.

## La variable `GRACE_PERIOD_SECONDS`

La duración de este período de gracia está controlada por la variable de entorno `GRACE_PERIOD_SECONDS`, que puede configurar en su archivo `docker-compose.yml`.

* El valor predeterminado es `600` segundos (10 minutos).
* Puede ajustar este valor para adaptarlo a sus necesidades. Un período más corto hace que la limpieza sea más rápida, mientras que un período más largo proporciona una ventana más grande para el reinicio del contenedor.

**Ejemplo:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      - GRACE_PERIOD_SECONDS=3600 # Set a 1-hour grace period
```

## Cómo funciona en la práctica

1. **Contenedor detenido:** Ejecutas `docker stop my-app`.
2. **Pendiente de eliminación:** DockFlare detecta el evento de detención. En la interfaz web, la regla para `my-app.example.com` ahora mostrará su estado como **"pending_deletion"** y mostrará la hora a la que está programada su eliminación.
3. **Los dos escenarios:**
    * **Escenario A: El período de gracia vence:** Si el contenedor permanece detenido y el período de gracia (por ejemplo, 10 minutos) expira, se ejecutará la tarea de limpieza en segundo plano de DockFlare. Eliminará la regla ingress de su túnel Cloudflare y eliminará el registro DNS CNAME.
    * **Escenario B: Reinicios del contenedor:** Si inicia el contenedor nuevamente (`docker start my-app`) **antes** de que expire el período de gracia, DockFlare detectará el evento de inicio. Verá que la regla está pendiente de eliminación, cancelará la eliminación y cambiará su estado nuevamente a **"activo"**. Su servicio continúa funcionando sin problemas.
