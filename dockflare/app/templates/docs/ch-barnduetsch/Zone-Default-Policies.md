# Zone-Standardrichtlinie – Wildcard-Schutz

## Überblick

Zone-Standardrichtlinie sy es Security-Best-Practice-Feature. Si nutze Cloudflare Access Wildcard-Applications wie `*.domain.com`, zum aui Subdomains vo nere DNS-Zone standardmässig z schütze.

## Was Problem das löst

Ohni Zone-Standardrichtlinie:

* blybe vergässeni Services öffentlich erreichbar
* sy nöii Subdomains ungeschützt, bis si manuell konfiguriert wärde
* chöi Tippfähler i Hostname-Konfiguratione Sicherheitskontrolle umgah
* entstöh mit dr Zyt Lücke zwüsche Doku u effektive Schutz

## So funktioniert's

### Priorität vo de Policies

Cloudflare bewertet Access Policies i dere Reihiefolg:

1. **Exakti Hostname-Übereinstimmig** – zum Bispil `app.example.com`
2. **Wildcard-Übereinstimmig** – zum Bispil `*.example.com`
3. **Kei Übereinstimmig** – dr Host blybt öffentlich, wänn kei Access App existiert

### Wie DockFlare das umsetzt

Dr Bereich **Zone Default Policies** i DockFlare:

* listet aui Cloudflare DNS-Zone uf
* zeigt dr Schutzstatus mit Badges
* erlaubt d Erstellige vo `*.zone.com`-Policies mit wenige Klicks
* laht di wähle, weli Access Group e Zone schützt

## Iirichtig

### Schritt 1: Zone prüefe

1. Gang uf d Syte **Access Policies**
2. Scroll bis **Zone Default Policies (*.tld Wildcards)**
3. Prüef dr Schutzstatus:
   * 🛡️ **Protected** – d Zone het scho e Wildcard-Policy
   * ⚠️ **Not Protected** – d Zone isch no ungeschützt

### Schritt 2: Zonen-Policy erstelle

Für jedi ungeschützte Zone:

1. Klick uf **Create Policy**
2. Im Modal gsehsch dr Hostname `*.zone-name.com`
3. Wähl e passendi Access Policy:
   * **Öffentlechi Zonen**: `public-default-bypass`
   * **Interne Zonen**: e authentifizieri Policy
   * **Gemischti Zonen**: d restriktivsti sinnvolle Policy
4. Klick uf **Create Zone Policy**

### Schritt 3: I Cloudflare kontrolliere

1. Mach ds Cloudflare Zero Trust Dashboard uf
2. Gang zu **Access → Applications**
3. Suech nach em Name `Zone Default: *.domain.com`
4. Prüef, öb d Policy korrekt hinterleit isch

## Sicherheitsempfählig

### Für Produktivumgebige

✅ **Zone-Standardrichtlinie immer aktiviere**

* verhinderet unbeabsichtigt exponierti Dienscht
* fängt Konfigurationsfähler ab
* schützt vor unentdeckte oder vergässene Subdomains

### Policy-Uuswahl

* **Öffentlechi Content-Domains**: `public-default-bypass`
* **Interne Tool-Domains**: Mail-/Domain-Authentifizierig
* **Sensibli Date**: Authentifizierig mit MFA
* **Entwickligszone**: immer mit dr restriktivste sinnvolle Policy absichere

### Monitoring

Prüef regelmässig:

* weli Zonen e aktive Schutz hei
* d Access-Application-Logs i Cloudflare
* d aktivi Subdomains im Verglych zu de konfigurierten Policies

## Problem löse

### Fähler `Policy already exists`

Es git scho e `*.domain.com` Access Application. Das cha passiere, wänn si:

* manuell i Cloudflare erstellt worde isch
* früecher scho mal vo DockFlare erstellt worde isch
* vo eme angere Tool aagleit worde isch

**Lösig:** Verwalt si diräkt i Cloudflare oder lösch si u erstell si über DockFlare neu.

### Service isch immer no ohni Authentifizierig erreichbar

Prüef d Priorität:

1. Lueg, dass es e spezifischi Hostname-Policy für dä Service git
2. Bestätig, dass d Zonen-Wildcard existiert u korrekt konfiguriert isch
3. Wänn dr Service trotz Zone-Schutz öffentlich blybe söll, setz `dockflare.access.group=public-default-bypass`

### Öffentlechi Services trotz Zonenschutz

Wänn du e Zonen-Policy hesch, aber einzelni Services bewusst öffentlich blybe müesse:

1. Gib em Container ds Bypass-Label:
   ```yaml
   labels:
     - "dockflare.access.group=public-default-bypass"
   ```
2. Dadermit entsteht e exakti Hostname-Access-Application mit `bypass`
3. Exakti Hostname-Policies hei Vorrang vor Wildcards
4. Dr Service blybt öffentlich, während d Zone als Ganzes gschützt blybt

### Zone wird nid azeigt

Mögligi Ursach:

* d Zone existiert nid i dim Cloudflare-Account
* dr API-Token het kei `Zone:Zone:Read`-Berechtigung
* d Zone isch pausiert oder glöscht

**Lösig:** Prüef im Cloudflare Dashboard, öb d Zone existiert u öb dr API-Token die nötige Rächt het.

## Best Practices

1. **Zonen-Policies zersch erstelle** – bevor du Services derzue tuesch
2. **Interni Zonen authentifiziere** – nie `bypass` für interni Zonen bruuchen
3. **Usnahme dokumentiere** – wänn e Zone kei Schutz bruucht, halt fescht warum
4. **Regelmässigi Audits** – prüef dr Schutzstatus regelmässig
5. **Vor Produktion teste** – lueg, dass d Wildcard-Policy nüt kaputt macht
6. **Least Privilege** – nimm d restriktivsti Policy, wo legitime Zuegriff no erlaubt

## Bispiel

### Öffentlechi Blog-Zone

```
Zone: blog.example.com
Policy: public-default-bypass
Result: Aui Subdomains öffentlich erreichbar (*.blog.example.com)
```

### Interni Tools-Zone

```
Zone: internal.company.com
Policy: Company Email Authentication
Result: Aui Subdomains verlange e @company.com-Mailadresse (*.internal.company.com)
```

### Gemischti Dev-Zone

```
Zone: dev.company.com
Policy: Developer Team Authentication
Result: Aui Dev-Services sy standardmässig gschützt (*.dev.company.com)
Specific overrides: public-demo.dev.company.com → public-default-bypass
```

## Policy-Priorität verstah

### Szenario 1: Spezifischi Policy schlägt Wildcard

**Setup:**

* Zonen-Policy: `*.example.com` → Auth nötig
* Spezifischi Policy: `blog.example.com` → `public-default-bypass`

**Ergebnis:**

* `blog.example.com` → öffentlich
* `api.example.com` → Auth nötig
* `forgotten.example.com` → Auth nötig

### Szenario 2: Wildcard als Sicherheitsnetz

**Setup:**

* Zonen-Policy: `*.internal.company.com` → `@company.com` nötig
* Spezifischi Policy: kei für `test-server.internal.company.com`

**Ergebnis:**

* `test-server.internal.company.com` → Auth nötig
* O wänn dr Service vergässe geit, greift d Wildcard-Policy

### Szenario 3: Kei Schutz

**Setup:**

* Zonen-Policy: kei für `*.risky-domain.com`
* Spezifischi Policy: `app.risky-domain.com` → Authentifizierig

**Ergebnis:**

* `app.risky-domain.com` → Auth nötig
* `forgotten.risky-domain.com` → öffentlich, will kei Wildcard greift

## Zämehang mit DockFlare-Labels

### Label `default_tld`

Mit `dockflare.access.policy=default_tld` weist du DockFlare aa, d Wildcard-Policy vo dr Zone z bruuche:

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

**Verhalte:**

* Wänn `*.internal.company.com` existiert, wird die Policy geerbt
* Wänn kei Zonen-Policy existiert, blybt dr Service öffentlich

### Empfählig

Statt di uf `default_tld` z verla:

1. Erstell Zone-Standardrichtlinie diräkt i dr UI
2. Lah d Wildcard-Policy standardmässig aui Services absichere
3. Erstell spezifischi Policies nume für Usnahme

So hesch besseres Security-by-default.
