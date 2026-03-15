# Content Security Policy (CSP)

## Was isch eine Content Security Policy?

Eine Content Security Policy (CSP - Inhaltssicherheitsrichtlinie) isch ein Websicherheitsstandard, der hilft, bestimmte Arten von Angriffen zu verhindern, insbesondere Cross-Site Scripting (XSS) u Data-Injection-Angriffe. Das funktioniert so, dass sie dem Browser mitteilt, welche Inhaltsquellen (Skripte, Styles, Bilder usw.) vertrauenswürdig si u auf einer Webseite geladen wärde dürfen.

## Die CSP von DockFlare

DockFlare bringt e Web UI mit. Damit die UI sauber abgsicheret isch, setzt DockFlare für sini eigeni UI e strengi Content Security Policy.

Das isch ein wichtiges internes Sicherheitsmerkmal, das du, den Administrator, vor potenziellen browserbasierten Schwachstellen schützen soll, während du das DockFlare-Dashboard nutzen.

## Geltungsbereich der CSP

Es isch wichtig zu verstehen, dass die CSP von DockFlare **nur für die DockFlare Web UI selbst gilt**.

Du hesch **kener** Auswirkungen auf den Datenverkehr, der über dini Cloudflare Tunnel an dini eigenen Anwendungen geleitet wird, noch modifiziert oder fügt sie diesem Verkehr CSP-Header hinzu. Wänn du eine CSP für dini eigenen Anwendungen implementieren wotsch, muesch diese innerhalb der Anwendungen selbst konfigurieren (z. B. durch Setzen des HTTP-Headers `Content-Security-Policy` in dim Webserver oder Anwendungscode).

## Konfiguration

Die CSP von DockFlare isch ein wesentlicher Bestandteil seiner Sicherheitsarchitektur u **cha nid vom Benutzer konfiguriert wärde**. Die Richtlinie wurde sorgfältig so ausgearbeitet, dass sie so restriktiv wie möglich isch, während die UI weiterhin korrekt funktioniert.

Wänn du di eingehender darüber informieren wotsch, wie Content Security Policies im Allgemeinen funktionieren, si die [MDN Web Docs über CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) eine hervorragende Ressource.
