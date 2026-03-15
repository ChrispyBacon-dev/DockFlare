# Content Security Policy (CSP)

## Was ist eine Content Security Policy?

Eine Content Security Policy (CSP - Inhaltssicherheitsrichtlinie) ist ein Websicherheitsstandard, der hilft, bestimmte Arten von Angriffen zu verhindern, insbesondere Cross-Site Scripting (XSS) und Data-Injection-Angriffe. Sie funktioniert so, dass sie dem Browser mitteilt, welche Inhaltsquellen (Skripte, Styles, Bilder usw.) vertrauenswürdig sind und auf einer Webseite geladen werden dürfen.

## Die CSP von DockFlare

Die DockFlare-Anwendung selbst verfügt über eine Weboberfläche. Um diese Oberfläche zu schützen und ihre Sicherheit zu gewährleisten, implementiert DockFlare eine strenge Content Security Policy für seine eigene Benutzeroberfläche (UI).

Dies ist ein wichtiges internes Sicherheitsmerkmal, das Sie, den Administrator, vor potenziellen browserbasierten Schwachstellen schützen soll, während Sie das DockFlare-Dashboard nutzen.

## Geltungsbereich der CSP

Es ist wichtig zu verstehen, dass die CSP von DockFlare **nur für die DockFlare Web UI selbst gilt**.

Sie hat **keine** Auswirkungen auf den Datenverkehr, der über Ihren Cloudflare Tunnel an Ihre eigenen Anwendungen geleitet wird, noch modifiziert oder fügt sie diesem Verkehr CSP-Header hinzu. Wenn Sie eine CSP für Ihre eigenen Anwendungen implementieren möchten, müssen Sie diese innerhalb der Anwendungen selbst konfigurieren (z. B. durch Setzen des HTTP-Headers `Content-Security-Policy` in Ihrem Webserver oder Anwendungscode).

## Konfiguration

Die CSP von DockFlare ist ein wesentlicher Bestandteil seiner Sicherheitsarchitektur und **kann nicht vom Benutzer konfiguriert werden**. Die Richtlinie wurde sorgfältig so ausgearbeitet, dass sie so restriktiv wie möglich ist, während die UI weiterhin korrekt funktioniert.

Wenn Sie sich eingehender darüber informieren möchten, wie Content Security Policies im Allgemeinen funktionieren, sind die [MDN Web Docs über CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) eine hervorragende Ressource.
