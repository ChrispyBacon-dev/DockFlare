# Política de seguridad de contenido (CSP)

## ¿Qué es una política de seguridad de contenidos?

Una Política de seguridad de contenido (CSP) es un estándar de seguridad web que ayuda a prevenir ciertos tipos de ataques, sobre todo ataques de secuencias de comandos entre sitios (XSS) y de inyección de datos. Funciona diciéndole al navegador qué fuentes de contenido (scripts, estilos, imágenes, etc.) son confiables y se permite cargar en una página web.

## CSP de DockFlare

La propia aplicación DockFlare incluye una interfaz web. Para proteger esta interfaz y garantizar su seguridad, DockFlare implementa una Política de seguridad de contenido (CSP) estricta en la propia interfaz web.

Esta es una característica de seguridad interna importante diseñada para protegerlo a usted, el administrador, de posibles vulnerabilidades basadas en el navegador cuando utiliza el panel de DockFlare.

## Alcance del CSP

Es importante comprender que el CSP de DockFlare se aplica **solo a la interfaz web de DockFlare**.

**No** afecta, modifica ni agrega ningún encabezado CSP al tráfico que se envía a través de su túnel de Cloudflare a sus propias aplicaciones. Si desea implementar un CSP en sus propias aplicaciones, debe configurarlo dentro de las aplicaciones mismas (por ejemplo, configurando el encabezado HTTP `Content-Security-Policy` en su servidor web o código de aplicación).

## Configuración

El CSP de DockFlare es una parte integral de su postura de seguridad y **no es configurable por el usuario**. La política está cuidadosamente diseñada para ser lo más restrictiva posible y, al mismo tiempo, permitir que la interfaz web funcione correctamente.

Si está interesado en obtener más información sobre cómo funcionan las políticas de seguridad de contenido en general, [MDN Web Docs on CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) es un recurso excelente.
