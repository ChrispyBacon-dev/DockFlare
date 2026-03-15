# Zonen-Standardrichtlinien – Wildcard-Schutz

## Übersicht

Zonen-Standardrichtlinien sind ein Security-Best-Practice-Feature, das Cloudflare Access Wildcard-Applications (`*.domain.com`) nutzt, um alle Subdomains einer DNS-Zone automatisch zu schützen.

## Das Problem, das dies löst

Ohne Zonen-Standardrichtlinien:
- bleiben vergessene Services öffentlich erreichbar
- sind neue Subdomains ungeschützt, bis sie manuell konfiguriert werden
- können Tippfehler in Hostnamen-Konfigurationen Zugriffskontrollen umgehen
- führt Dokumentations-Drift zu Sicherheitslücken

## So funktioniert es

### Priorität der Policies

Cloudflare bewertet Access Policies in dieser Reihenfolge:

1. **Exakte Hostname-Übereinstimmung** (z.B. `app.example.com`)
2. **Wildcard-Übereinstimmung** (z.B. `*.example.com`)
3. **Keine Übereinstimmung** = öffentlich (keine Access App)

### DockFlare-Implementierung

Der Bereich **Zone Default Policies** in DockFlare:
- listet alle Cloudflare DNS-Zonen
- zeigt den Schutzstatus über Badges an
- erlaubt die One-Click-Erstellung von `*.zone.com` Policies
- lässt Sie auswählen, welche Access Group die Zone schützt

## Einrichtungsleitfaden

### Schritt 1: Zonen überprüfen

1. Öffnen Sie die Seite **Access Policies**
2. Scrollen Sie zu **Zone Default Policies (*.tld Wildcards)**
3. Prüfen Sie den Schutzstatus:
   - 🛡️ **Grün "Protected"**: Zone hat eine Wildcard-Policy
   - ⚠️ **Gelb "Not Protected"**: Zone ist angreifbar

### Schritt 2: Zonen-Policies erstellen

Für jede ungeschützte Zone:

1. Klicken Sie auf **Create Policy**
2. Das Modal zeigt den Hostnamen `*.zone-name.com`
3. Wählen Sie eine passende Access Policy:
   - **Öffentliche Zonen**: `public-default-bypass`
   - **Interne Zonen**: Authentifizierungs-Policy
   - **Gemischte Zonen**: die restriktivste Policy
4. Klicken Sie auf **Create Zone Policy**

### Schritt 3: In Cloudflare verifizieren

1. Öffnen Sie das Cloudflare Zero Trust Dashboard
2. Navigieren Sie zu Access → Applications
3. Suchen Sie nach Applications mit dem Namen `Zone Default: *.domain.com`
4. Stellen Sie sicher, dass die Policy korrekt ist

## Sicherheitsempfehlungen

### Produktionsumgebungen

✅ **Aktivieren Sie Zonen-Standardrichtlinien immer**
- verhindert unbeabsichtigte Exponierung
- fängt Konfigurationsfehler ab
- schützt vor Subdomain-Discovery-Angriffen

### Policy-Auswahlstrategie

- **Öffentliche Content-Domains** (Blog, Marketing): `public-default-bypass`
- **Interne Tool-Domains**: E-Mail/Domain-Authentifizierung
- **Sensible Daten**: Authentifizierung mit MFA
- **Entwicklungszonen**: mit der restriktivsten Policy absichern

### Monitoring

Regelmäßig prüfen:
- welche Zonen Schutz aktiv haben (Seite **Access Policies**)
- Access-Application-Logs in Cloudflare
- Liste aktiver Subdomains vs. konfigurierte Policies

## Fehlerbehebung

### Fehler "Policy already exists"

Eine `*.domain.com` Access Application existiert bereits. Mögliche Ursachen:
- manuell in Cloudflare erstellt
- früher von DockFlare erstellt
- durch ein anderes Tool erstellt

**Lösung:** Verwalten Sie sie direkt in Cloudflare oder löschen und erstellen Sie sie über DockFlare neu.

### Service ist weiterhin ohne Authentifizierung erreichbar

Prüfen Sie die Policy-Priorität:
1. Verifizieren Sie, dass es eine spezifische Hostname-Policy für den Service gibt
2. Bestätigen Sie, dass die Zonen-Wildcard existiert und korrekt konfiguriert ist
3. Wenn der Service trotz Zonenschutz öffentlich bleiben soll, setzen Sie `dockflare.access.group=public-default-bypass`

### Zonenschutz für öffentliche Services umgehen

Wenn Sie eine Zonen-Policy haben, aber einzelne Services öffentlich bleiben müssen:

1. Fügen Sie dem Container das Bypass-Label hinzu:
   ```yaml
   labels:
     - "dockflare.access.group=public-default-bypass"
   ```
2. Dadurch wird eine exakte Hostname-Access-Application mit `bypass` erzeugt
3. Exakte Hostname-Policies haben Vorrang vor Wildcards
4. Der Service wird öffentlich, während die Zone insgesamt geschützt bleibt

### Zone wird nicht in der Liste angezeigt

Mögliche Ursachen:
- Zone existiert nicht in Ihrem Cloudflare-Account
- API-Token hat keine `Zone:Zone:Read` Berechtigung
- Zone ist pausiert oder gelöscht

**Lösung:** Prüfen Sie im Cloudflare Dashboard, ob die Zone existiert und ob das API-Token die nötigen Rechte hat.

## Best Practices

1. **Zonen-Policies zuerst erstellen**: bevor Sie Services hinzufügen
2. **Interne Zonen authentifizieren**: niemals `bypass` für interne Zonen verwenden
3. **Ausnahmen dokumentieren**: wenn eine Zone keinen Schutz braucht, dokumentieren Sie warum
4. **Regelmäßige Audits**: monatliche Prüfung des Schutzstatus
5. **Vor Produktion testen**: sicherstellen, dass die Wildcard-Policy nichts bricht
6. **Least Privilege**: die restriktivste Policy verwenden, die legitimen Zugriff noch erlaubt

## Beispielkonfigurationen

### Öffentliche Blog-Zone
```
Zone: blog.example.com
Policy: public-default-bypass
Result: All subdomains publicly accessible (*.blog.example.com)
```

### Interne Tools-Zone
```
Zone: internal.company.com
Policy: Company Email Authentication
Result: All subdomains require @company.com email (*.internal.company.com)
```

### Gemischte Dev-Zone
```
Zone: dev.company.com
Policy: Developer Team Authentication
Result: All dev services protected by default (*.dev.company.com)
Specific overrides: public-demo.dev.company.com → public-default-bypass
```

## Policy-Priorität verstehen

### Szenario 1: Spezifische Policy schlägt Wildcard

**Setup:**
- Zonen-Policy: `*.example.com` → Authentifizierung erforderlich
- Spezifische Policy: `blog.example.com` → `public-default-bypass`

**Ergebnis:**
- `blog.example.com` → öffentlich (spezifische Policy gewinnt)
- `api.example.com` → Auth erforderlich (Wildcard greift)
- `forgotten.example.com` → Auth erforderlich (Wildcard greift)

### Szenario 2: Wildcard als Safety Net

**Setup:**
- Zonen-Policy: `*.internal.company.com` → erfordert @company.com E-Mail
- Spezifische Policy: keine für `test-server.internal.company.com`

**Ergebnis:**
- `test-server.internal.company.com` → Auth erforderlich (Wildcard schützt)
- selbst wenn Sie es vergessen: die Zonen-Policy schützt es

### Szenario 3: Kein Schutz

**Setup:**
- Zonen-Policy: keine für `*.risky-domain.com`
- Spezifische Policy: `app.risky-domain.com` → Authentifizierung

**Ergebnis:**
- `app.risky-domain.com` → Auth erforderlich (spezifische Policy)
- `forgotten.risky-domain.com` → ⚠️ **PUBLIC** (keine Wildcard fängt es ab)

## Integration mit DockFlare-Labels

### Verwendung des Labels `default_tld`

Das Label `dockflare.access.policy=default_tld` weist DockFlare an, die Wildcard-Policy der Zone zu verwenden:

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

**Verhalten:**
- `*.internal.company.com` existiert → Policy wird geerbt
- keine Zonen-Policy → Service ist öffentlich (keine Access App wird erzeugt)

### Empfehlung

Statt sich auf `default_tld` zu verlassen:
1. Zonen-Standardrichtlinien in der UI erstellen
2. Wildcard-Policy alle Services automatisch schützen lassen
3. Spezifische Policies nur für Ausnahmen erstellen

Das sorgt für bessere Security-by-default.

## Weiterführende Dokumentation

- [Best Practices für Zugriffsrichtlinien](Access-Policy-Best-Practices.md)
- [Verwendung der Web-UI](Using-the-Web-UI.md)
- [Container-Labels](Container-Labels.md)
- [Wie DockFlare funktioniert](How-DockFlare-Works.md)
- [Sicherheitsarchitektur & Härtung](Security-Architecture.md)
