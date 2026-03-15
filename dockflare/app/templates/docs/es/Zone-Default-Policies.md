# Políticas predeterminadas de zona: protección con comodines

## Descripción general

Las políticas predeterminadas de zona son una característica de mejores prácticas de seguridad que utiliza aplicaciones comodín de Cloudflare Access (`*.domain.com`) para proteger todos los subdominios de una zona DNS automáticamente.

## El problema que esto resuelve

Sin políticas predeterminadas de zona:
- Los servicios olvidados se exponen públicamente.
- Los nuevos subdominios no tienen protección hasta que se configuran manualmente
- Los errores tipográficos en las configuraciones de nombres de host evitan los controles de acceso.
- La desviación de la documentación genera lagunas de seguridad

## Cómo funciona

### Prioridad de política

Cloudflare evalúa las políticas de acceso en este orden:

1. **Coincidencia exacta del nombre de host** (por ejemplo, `app.example.com`)
2. **Coincidencia comodín** (p. ej., `*.example.com`)
3. **No hay coincidencia** = Acceso público (sin aplicación de acceso)

### Implementación de DockFlare

Sección **Políticas predeterminadas de zona** de DockFlare:
- Enumera todas tus zonas DNS de Cloudflare
- Muestra el estado de protección con insignias visuales
- Permite la creación con un solo clic de políticas `*.zone.com`
- Te permite elegir qué grupo de acceso protege la zona.

## Guía de configuración

### Paso 1: Revise sus zonas

1. Vaya a la página **Políticas de acceso**
2. Desplácese hasta **Políticas predeterminadas de zona (*.tld comodines)**
3. Revisar el estado de protección:
   - 🛡️ **Verde "Protegido"** - La zona tiene una política de comodines
   - ⚠️ **Amarillo "No protegido"** - La zona es vulnerable

### Paso 2: Crear políticas de zona

Para cada zona desprotegida:

1. Haga clic en el botón **Crear política**
2. Modal muestra `*.zone-name.com` nombre de host
3. Seleccione la Política de acceso adecuada:
   - **Zonas públicas** → `public-default-bypass`
   - **Zonas internas** → Política de autenticación
   - **Zonas mixtas** → Política más restrictiva
4. Haga clic en **Crear política de zona**

### Paso 3: Verificar en Cloudflare

1. Abra el panel de Cloudflare Zero Trust
2. Vaya a Acceso → Aplicaciones
3. Busque aplicaciones denominadas `Zone Default: *.domain.com`
4. Verifique que la política sea correcta

## Recomendaciones de seguridad

### Entornos de producción

✅ **Habilite siempre las políticas predeterminadas de zona**
- Previene la exposición accidental
- Detecta errores de configuración
- Protege contra ataques de descubrimiento de subdominios

### Estrategia de selección de políticas

- **Dominios de contenido público** (blogs, marketing): `public-default-bypass`
- **Dominios de herramientas internas**: autenticación de dominio/correo electrónico
- **Dominios de datos confidenciales**: autenticación habilitada para MFA
- **Dominios de desarrollo**: bloquear con la política más estricta

### Monitoreo

Revisar periódicamente:
- Qué zonas tienen protección (página **Políticas de acceso**)
- Acceda a los registros de aplicaciones en Cloudflare
- Lista de subdominios activos vs políticas configuradas

## Solución de problemas

### Error "La política ya existe"

Ya existe una aplicación de acceso `*.domain.com`. Esto podría ser:
- Creado manualmente en Cloudflare
- Creado por DockFlare anteriormente
- Creado por otra herramienta

**Solución:** Administrelo directamente en Cloudflare, o elimínelo y vuelva a crearlo a través de DockFlare.

### Servicio aún accesible sin autenticación

Verifique la prioridad de la política:
1. Verifique que el servicio tenga una política de nombre de host específica
2. Confirme que el comodín de zona existe y está configurado correctamente
3. Si el servicio debe ser público a pesar de la protección de la zona, agregue la etiqueta `dockflare.access.group=public-default-bypass`

### Protección de zona de exclusión para servicios públicos

Si tiene una política de autenticación a nivel de zona pero necesita servicios específicos para permanecer público:

1. Agregue la etiqueta de derivación al contenedor:
   ```yaml
   labels:
     - "dockflare.access.group=public-default-bypass"
   ```
2. Esto crea una aplicación de acceso con nombre de host exacto con decisión de omisión
3. Las políticas de nombres de host exactos anulan las políticas de comodines
4. El servicio se vuelve accesible al público mientras la zona permanece protegida
3. Verifique los registros de acceso de Cloudflare para conocer el orden de evaluación de políticas
4. Asegúrese de que el registro DNS apunte al túnel correcto.

### Zona que no se muestra en la lista

Posibles causas:
- La zona DNS no está en tu cuenta de Cloudflare
- El token API carece del permiso `Zone:Zone:Read`
- La zona está pausada o eliminada

**Solución:** Verifique que la zona exista en el panel de Cloudflare y que el token API tenga los permisos correctos.

## Mejores prácticas

1. **Crear políticas de zona primero** - Antes de agregar servicios
2. **Usar autenticación para zonas internas** - Nunca usar anulación
3. **Documente excepciones**: si una zona no necesita protección, documente el motivo.
4. **Auditorías periódicas** - Revisión mensual del estado de protección de la zona
5. **Prueba antes de la producción**: verifica que la política de comodines no interrumpa los servicios existentes
6. **Principio de privilegio mínimo**: utilice la política más restrictiva que aún permita el acceso legítimo

## Configuraciones de ejemplo

### Zona de blogs públicos
```
Zone: blog.example.com
Policy: public-default-bypass
Result: All subdomains publicly accessible (*.blog.example.com)
```

### Zona de herramientas internas
```
Zone: internal.company.com
Policy: Company Email Authentication
Result: All subdomains require @company.com email (*.internal.company.com)
```

### Zona de Desarrollo Mixto
```
Zone: dev.company.com
Policy: Developer Team Authentication
Result: All dev services protected by default (*.dev.company.com)
Specific overrides: public-demo.dev.company.com → public-default-bypass
```

## Comprender la prioridad política

### Escenario 1: Política específica anula el comodín

**Configuración:**
- Política de zona: `*.example.com` → Requiere autenticación
- Política específica: `blog.example.com` → `public-default-bypass`

**Resultado:**
- `blog.example.com` → Público (política específica gana)
- `api.example.com` → Requiere autenticación (el comodín lo capta)
- `forgotten.example.com` → Requiere autenticación (el comodín lo capta)

### Escenario 2: comodín como red de seguridad

**Configuración:**
- Política de zona: `*.internal.company.com` → Requiere correo electrónico @company.com
- Política específica: Ninguna para `test-server.internal.company.com`

**Resultado:**
- `test-server.internal.company.com` → Requiere autenticación (el comodín la protege)
- Incluso si olvidaste configurarlo, la política de zona lo protege.

### Escenario 3: Sin protección

**Configuración:**
- Política de zona: Ninguna para `*.risky-domain.com`
- Política específica: `app.risky-domain.com` → Autenticación

**Resultado:**
- `app.risky-domain.com` → Requiere autenticación (política específica)
- `forgotten.risky-domain.com` → ⚠️ **PUBLIC** (sin comodín para detectarlo)

## Integración con etiquetas DockFlare

### Usando la etiqueta `default_tld`

La etiqueta `dockflare.access.policy=default_tld` le dice a DockFlare que use la política de comodines de la zona:

```yaml
services:
  my-service:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=new-app.internal.company.com"
      - "dockflare.service=http://my-service:80"
      - "dockflare.access.policy=default_tld"
```

**Comportamiento:**
- Si `*.internal.company.com` existe → Hereda esa política
- Si no existe una política de zona → El servicio es público (no se crea ninguna aplicación de acceso)

### Recomendación

En lugar de confiar en la etiqueta `default_tld`:
1. Cree políticas predeterminadas de zona en la interfaz web.
2. Deje que la política de comodines proteja automáticamente todos los servicios.
3. Cree únicamente políticas específicas para excepciones.

Esto garantiza una mejor seguridad de forma predeterminada.

## Documentación relacionada

- [Mejores prácticas de política de acceso](Access-Policy-Best-Practices.md)
- [Uso de la interfaz web](Using-the-Web-UI.md)
- [Etiquetas de contenedor](Container-Labels.md)
- [Cómo funciona DockFlare](How-DockFlare-Works.md)
- [Arquitectura de seguridad](Security-Architecture.md)
