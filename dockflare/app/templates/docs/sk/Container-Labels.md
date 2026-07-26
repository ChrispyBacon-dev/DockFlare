# Referencia Docker labelov

DockFlare sa konfiguruje primárne cez Docker labely pripojené k tvojim kontajnerom. Táto stránka poskytuje komplexnú referenciu všetkých podporovaných labelov.

## Základná konfigurácia

Tieto labely riadia základné smerovanie a definíciu služby pre kontajner.

| Label | Popis | Príklad |
| :--- | :--- | :--- |
| `dockflare.enable` | **Povinné.** Hlavný vypínač. Musí byť nastavené na `true`, aby DockFlare kontajner spravoval. | `dockflare.enable=true` |
| `dockflare.hostname` | **Povinné.** Verejný hostname tvojej služby. | `dockflare.hostname=myservice.example.com` |
| `dockflare.service` | **Povinné.** Interná URL služby, na ktorú sa má Cloudflare Tunnel pripojiť. Môže byť `http`, `https`, `tcp`, `ssh`, `rdp`, `http_status:XXX` alebo `bastion`. | `dockflare.service=http://my-app-container:8080` |
| `dockflare.path` | URL cesta, ktorá sa má smerovať do tejto služby. Užitočné na vystavenie viacerých služieb na tom istom hostname. | `dockflare.path=/api` |
| `dockflare.zonename` | (Voliteľné) Explicitná Cloudflare zóna (doména), kde sa má vytvoriť DNS záznam. Ak je vynechané, DockFlare teraz zónu automaticky zistí podľa hostname a k nakonfigurovanej predvolenej (`CF_ZONE_ID`) sa uchýli len vtedy, keď auto-detekcia zlyhá. | `dockflare.zonename=another-domain.com` |
| `dockflare.no_tls_verify` | Ak je nastavené na `true`, vypne overovanie TLS certifikátu pre spojenie medzi `cloudflared` a tvojou origin službou. Užitočné pre originy so self-signed certifikátmi. | `dockflare.no_tls_verify=true` |
| `dockflare.originsrvname` | Nastaví konkrétny SNI (Server Name Indication) hostname pre TLS spojenie s originom. V Cloudflare dashboarde je to známe aj ako „Origin Server Name“. | `dockflare.originsrvname=internal.service.local` |
| `dockflare.httpHostHeader` | Prepíše hlavičku `Host` odosielanú z `cloudflared` do tvojej origin služby. | `dockflare.httpHostHeader=custom-host.internal` |
| `dockflare.http2_origin` | Ak je nastavené na `true`, zapne protokol HTTP/2 pre spojenie medzi `cloudflared` a tvojou origin službou. Potrebné pre gRPC služby. Platí len pre HTTP/HTTPS služby. | `dockflare.http2_origin=true` |
| `dockflare.disable_chunked_encoding` | Ak je nastavené na `true`, vypne chunked transfer encoding cez HTTP/1.1. Užitočné pre WSGI servery (Flask, Django, FastAPI) a ďalšie originy, ktoré chunked požiadavky správne nepodporujú. Platí len pre HTTP/HTTPS služby. | `dockflare.disable_chunked_encoding=true` |
| `dockflare.match_sni_to_host` | Ak je nastavené na `true`, Cloudflare počas TLS handshaku automaticky nastaví SNI tak, aby zodpovedalo hostname prichádzajúcej požiadavky. | `dockflare.match_sni_to_host=true` |

> **Tip:** Od DockFlare v3.0 môžeš pri väčšine záťaží `dockflare.zonename` vynechať. Master zistí správnu Cloudflare zónu porovnaním prípony hostname a k nakonfigurovanej predvolenej zóne sa uchýli len vtedy, keď nenájde zhodu. Label zadaj, keď zámerne chceš umiestniť záznam do inej zóny.

> **Poznámka:** Cloudflare možnosť **Match SNI to Host** je dostupná v konfigurácii manuálneho pravidla DockFlare v dashboarde. Momentálne sa nenastavuje cez Docker label.

---

## Konfigurácia prístupovej politiky

Tieto labely ti umožnia dynamicky vytvárať a spravovať Cloudflare Access aplikácie na zabezpečenie tvojich služieb.

**Poznámka:** Dôrazne sa odporúča používať na správu politík **prístupové skupiny** (`dockflare.access.group`). DockFlare 3.0.3 synchronizuje každú prístupovú skupinu do pomenovanej opakovane použiteľnej Cloudflare Access politiky, čím ti dáva opakované použitie one-to-many a obojsmerné úpravy. Použitie jednotlivých labelov je najlepšie pre jednorazové, unikátne konfigurácie. Ak sa použije `dockflare.access.group` alebo `dockflare.access.groups`, všetky ostatné labely `dockflare.access.*` sa ignorujú.

### Dôležité zmeny v v3.0.3

#### Systémová predvolená bypass politika

Od v3.0.3, keď použiješ `dockflare.access.policy=bypass` alebo `dockflare.access.group=bypass`, tvoja služba bude odkazovať na systémom spravovanú opakovane použiteľnú politiku `public-default-bypass` namiesto vytvárania inline politiky. Udrží to tvoj Cloudflare dashboard prehľadný.

- **Pred v3.0.3:** Každé bypass pravidlo vytvorilo samostatnú inline politiku
- **v3.0.3+:** Všetky bypass pravidlá zdieľajú jednu kanonickú politiku `public-default-bypass`

#### Migrácia starších labelov

DockFlare automaticky migruje staršie bypass labely na použitie centralizovanej systémovej politiky:

- `dockflare.access.policy=bypass` → používa systémovú politiku `public-default-bypass`
- `dockflare.access.group=bypass` → používa systémovú politiku `public-default-bypass`

Migrácia prebieha transparentne počas spracovania kontajnerov a synchronizácie. Tvoje kontajnery budú fungovať ďalej bez potreby akýchkoľvek zmien.

#### Zjednodušená konfigurácia prístupu

Pre zložité scenáre prístupu (overenie e-mailom/doménou, whitelisting IP atď.) sa teraz odporúča:

1. Vytvoriť prístupovú skupinu na stránke **Prístupové politiky**
2. Odkázať na ňu cez `dockflare.access.group=id-tvojej-skupiny`

Možnosti rýchleho vytvárania boli z UI odstránené, aby podporili tento osvedčený postup.

#### Label predvolenej politiky zóny

Label `dockflare.access.policy=default_tld` stále funguje a zdedí ochranu z wildcard politiky `*.domain.com` tvojej zóny. Ak žiadna politika zóny neexistuje, služba bude verejná (žiadna Access aplikácia).

**Odporúčanie:** Pre lepšiu bezpečnosť vytvor v UI predvolené politiky zóny pre všetky svoje domény.

| Label | Popis | Príklad |
| :--- | :--- | :--- |
| `dockflare.access.group` | ID jednej vopred nakonfigurovanej prístupovej skupiny, ktorá sa má uplatniť na túto službu. ID nájdeš na stránke „Prístupové politiky“ v UI DockFlare. | `dockflare.access.group=internal-tools-policy` |
| `dockflare.access.groups` | Čiarkou oddelený zoznam ID prístupových skupín, ktoré sa majú uplatniť. Umožní ti to navrstviť na jednu službu viacero politík. | `dockflare.access.groups=allow-team-a,allow-admins` |
| `dockflare.access.policy` | Primárny typ politiky. Môže byť `bypass` (verejné), `authenticate` (vyžaduje prihlásenie) alebo `default_tld` (zdedí z politiky `*.domain.com`). Ak nie je nastavené, služba bude verejná. Pre opakovane použiteľné politiky uprednostni prístupové skupiny; tieto labely sú pre špecializované prepisy. | `dockflare.access.policy=authenticate` |
| `dockflare.access.name` | Vlastný názov pre Cloudflare Access aplikáciu. Predvolene `DockFlare-{hostname}`. | `dockflare.access.name=My Web App Access` |
| `dockflare.access.session_duration` | Trvanie relácie pre overených používateľov (napr. `24h`, `30m`). Predvolene `24h`. | `dockflare.access.session_duration=1h` |
| `dockflare.access.app_launcher_visible` | Ak `true`, sprístupní aplikáciu v Cloudflare Access App Launcheri. | `dockflare.access.app_launcher_visible=true` |
| `dockflare.access.allowed_idps` | Čiarkou oddelený zoznam povolených UUID poskytovateľov identity (IdP). Nájdeš ich vo svojom Cloudflare Zero Trust dashboarde. | `dockflare.access.allowed_idps=uuid1,uuid2` |
| `dockflare.access.auto_redirect_to_identity` | Ak `true`, používatelia budú okamžite presmerovaní na prihlasovaciu stránku IdP namiesto úvodnej obrazovky Cloudflare Access. | `dockflare.access.auto_redirect_to_identity=true` |
| `dockflare.access.custom_rules` | JSON reťazec predstavujúci pole pravidiel Cloudflare Access politiky. Poskytuje maximálnu flexibilitu pre zložité, jednorazové politiky. | `dockflare.access.custom_rules='[{"email":{"email":"user@example.com"},"action":"allow"}]'` |

---

## Indexované labely pre viacero domén

DockFlare podporuje definovanie viacerých hostname pre jeden kontajner pomocou indexovaných labelov. Hodí sa to na vystavenie rôznych portov alebo ciest tej istej služby na rôznych verejných hostname.

Na použitie indexovaných labelov pridaj pred label celé číslo, počnúc `0`.

*   Indexovaný hostname (`<index>.hostname`) je vždy povinný.
*   Ostatné labely pri rovnakom indexe (napr. `<index>.service`, `<index>.path`) prepíšu základné (neindexované) labely pre ten konkrétny hostname.
*   Ak indexovaný label nie je zadaný, použije sa hodnota zodpovedajúceho základného labelu.

### Príklad

Tento príklad vystavuje dva hostname z jedného kontajnera:
1.  `app.example.com` smeruje na hlavné webové rozhranie na porte `80`.
2.  `api.example.com` smeruje na API na porte `3000` a je zabezpečené konkrétnou prístupovou skupinou.

```yaml
services:
  my-multi-service:
    image: my-app
    labels:
      - "dockflare.enable=true"

      # --- Definícia 0 ---
      - "dockflare.0.hostname=app.example.com"
      - "dockflare.0.service=http://my-multi-service:80"

      # --- Definícia 1 ---
      - "dockflare.1.hostname=api.example.com"
      - "dockflare.1.service=http://my-multi-service:3000"
      - "dockflare.1.access.group=api-access-policy"
```
