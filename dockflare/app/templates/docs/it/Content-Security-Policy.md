# Politica di sicurezza dei contenuti (CSP)

## Che cos'è una politica di sicurezza dei contenuti?

Una Content Security Policy (CSP) è uno standard di sicurezza web che aiuta a prevenire determinati tipi di attacchi, in particolare Cross-Site Scripting (XSS) e attacchi di data injection. Funziona dicendo al browser quali fonti di contenuto (script, stili, immagini, ecc.) sono attendibili e possono essere caricate su una pagina web.

## CSP di DockFlare

L'applicazione DockFlare stessa include un'interfaccia web. Per proteggere questa interfaccia e garantirne la sicurezza, DockFlare implementa una rigorosa Content Security Policy sulla propria interfaccia web.

Questa è un'importante funzionalità di sicurezza interna progettata per proteggere te, l'amministratore, da potenziali vulnerabilità basate sul browser quando utilizzi la dashboard DockFlare.

## Campo di applicazione del CSP

È importante comprendere che il CSP di DockFlare si applica **solo all'interfaccia web di DockFlare**.

**Non** influisce, modifica o aggiunge alcuna intestazione CSP al traffico che viene inviato tramite proxy attraverso il tuo tunnel Cloudflare alle tue applicazioni. Se desideri implementare un CSP sulle tue applicazioni, devi configurarlo all'interno delle applicazioni stesse (ad esempio, impostando l'intestazione HTTP `Content-Security-Policy` nel tuo server web o nel codice dell'applicazione).

## Configurazione

Il CSP di DockFlare è parte integrante della sua strategia di sicurezza e **non è configurabile dall'utente**. La policy è stata progettata per essere il più restrittiva possibile, pur consentendo il corretto funzionamento dell'interfaccia web.

Se sei interessato a saperne di più sul funzionamento generale delle policy di sicurezza dei contenuti, [MDN Web Docs on CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) è un'eccellente risorsa.
