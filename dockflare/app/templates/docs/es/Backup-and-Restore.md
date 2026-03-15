# Copia de seguridad y restauración

DockFlare 3.0 incorpora un archivo de copia de seguridad completo para que pueda mover un Master a hardware nuevo, recuperarse de una falla o preparar actualizaciones sin tener que tocar directamente el directorio de datos sin procesar.

## Lo que se guarda
- `dockflare.key`: la clave Fernet que permite descifrar todos los archivos protegidos.
- `dockflare_config.dat`: credenciales cifradas de Cloudflare, cuentas de la interfaz web y ajustes de tiempo de ejecución.
- `agent_keys.dat`: claves API de los agentes cifradas y metadatos de auditoría.
- `state.json`: una copia JSON en texto claro de reglas, agentes y grupos de acceso.
- `manifest.json`: sumas de verificación e información de versión del archivo, generadas automáticamente.

Todos estos archivos se agrupan en un único `dockflare_backup_YYYYMMDD_HHMMSS.zip`. Conserve juntos el ZIP y los archivos extraídos; sin `dockflare.key`, los artefactos cifrados no se pueden utilizar.

## Crear una copia de seguridad
1. Abra **Settings → Backup & Restore** en la interfaz web del Master.
2. Haga clic en **Download Backup (.zip)**.
3. Guarde el archivo en un lugar seguro. Trátelo como una credencial sensible: contiene todo lo necesario para administrar su cuenta de Cloudflare mediante DockFlare.

Se pueden crear copias de seguridad mientras el Master está en ejecución. Cada archivo incluye un manifiesto con hashes SHA-256, por lo que resulta fácil detectar descargas dañadas.

## Restaurar en un Master existente
1. Vaya a **Settings → Backup & Restore**.
2. Cargue el `.zip` a través de **Restore from Backup**.
3. Confirme la advertencia: la restauración sobrescribe la configuración, las claves del agente y las reglas.

DockFlare vuelve a escribir los archivos cifrados, recarga `state.json` y, si es necesario, establece una marca de reinicio. El contenedor se detiene unos segundos después para que Docker pueda iniciarlo de nuevo con la configuración restaurada. Después, la interfaz vuelve a estar disponible con las credenciales recuperadas.

Los archivos `state.json` heredados se siguen aceptando para restauraciones parciales. Cargar un archivo JSON simple solo reemplaza las reglas y deja intacta la configuración cifrada.

## Restaurar durante el asistente de configuración
En las instalaciones nuevas ahora aparece un enlace **Restore from Backup** antes del paso 1 del wizard Pre-Flight.

1. Cargue el ZIP de respaldo.
2. DockFlare escribe en disco los artefactos cifrados y el estado.
3. El contenedor se reinicia automáticamente; cuando vuelva a estar disponible, inicie sesión con la cuenta de administrador restaurada.

Este flujo es la forma más rápida de clonar un Master de producción o recuperarlo después de borrar el volumen de datos. No es necesario volver a ejecutar el asistente ni introducir de nuevo las credenciales de Cloudflare.

## Después de la restauración
- Visite **Settings → Backup & Restore** para confirmar la marca de tiempo más reciente del manifiesto.
- Revise **Agentes → Descripción general** para asegurarse de que los agentes registrados vuelvan a conectarse. Vuelva a emitir claves de agente si las ha rotado.
- Active una reconciliación si restauró el sistema en un entorno diferente (`Actions → Reconcile Now`).

Mantenga copias de seguridad sin conexión de forma periódica y combínelas, si es posible, con el control de versiones de su stack Compose para poder reconstruir toda la implementación con rapidez.
