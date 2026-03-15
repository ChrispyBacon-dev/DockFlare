# Content Security Policy (CSP)

## Was isch e Content Security Policy?

E Content Security Policy, kurz CSP, isch e Web-Sicherheitsstandard. Si seit em Browser, weli Quelle für Skript, Styles, Bilder u angeri Inhalte erlaubt si. So chasch du Angrif wie Cross-Site Scripting (XSS) oder ähnlechi Injections besser verhindere.

## Die CSP von DockFlare

DockFlare bringt e Web UI mit. Damit die UI sauber abgsicheret isch, setzt DockFlare für sini eigeti Oberfläche e strengi CSP.

Das isch es wichtigs Sicherheitsmerkmal, wo di bim Schaffe i dr UI vor browserbasierte Schwachstelle schützt.

## Geltungsbereich der CSP

Wichtig isch: D CSP vo DockFlare gilt **nume für d DockFlare Web UI sälber**.

Dr Traffic, wo über dini Cloudflare Tunnel zu dine eigete Aawändige geit, wird vo DockFlare weder veränderet no mit zusätzliche CSP-Headers ergänzt. Wänn du für dini eigete App e CSP wotsch, muesch du die i dim Webserver oder App-Code sälber setze.

## Konfiguration

D CSP vo DockFlare isch Teil vo dr Sicherheitsarchitektur u **cha nid vom Benutzer aagpasst wärde**. Si isch so gstaltet, dass d UI mögli streng abgsicheret isch u glych no korrekt funktioniert.

Wänn du meh drüber wotsch wüsse, si d [MDN Web Docs über CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) e gueti Quelle.
