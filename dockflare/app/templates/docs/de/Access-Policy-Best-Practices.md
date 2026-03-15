# Best Practices & Beispiele für Zugriffsrichtlinien

Das stärkste Sicherheitsfeature von DockFlare sind die **Access Groups** (Zugriffsgruppen). Sie bieten eine zentralisierte, wiederverwendbare und wartbare Möglichkeit, Ihre Dienste mit Cloudflare Zero Trust abzusichern.

## Die "Goldene Regel": Verwenden Sie Access Groups

Die mit Abstand wichtigste Best Practice ist: **Verwenden Sie Access Groups für all Ihre gängigen Zugriffsrichtlinien**.

Access Groups sind Richtlinienvorlagen, die Sie in der DockFlare Web-UI erstellen. Anstatt komplexe Regeln mit mehreren Labels auf jedem Container zu definieren, erstellen Sie eine Richtlinie einmalig und wenden sie mit einem einzigen, sauberen Label an. DockFlare v3.0.3 synchronisiert nun jede Gruppe mit einer wiederverwendbaren Cloudflare Access Policy, sodass dieselben Entscheidungsregeln für mehrere Anwendungen gelten können.

---

## So erstellen und verwenden Sie Access Groups

Das Erstellen einer Access Group ist ein einfacher Prozess, der komplett innerhalb der DockFlare UI stattfindet.

### Schritt 1: Erstellen der Access Group

1.  Navigieren Sie zur Seite **Access Policies** über die Hauptnavigationsleiste in der DockFlare UI.
2.  Klicken Sie auf den Button **"Add Access Group"** (Zugriffsgruppe hinzufügen).
3.  Geben Sie Ihrer Gruppe eine **eindeutige und aussagekräftige ID**. Diese ID verwenden Sie später in Ihren Docker-Labels. Zum Beispiel: `admin-users`, `home-network`, `geo-block`.
4.  Wählen Sie den **Access Mode** (Zugriffsmodus) aus den Reitern oben im Modalfenster:
    *   **Authenticated** erfordert eine Benutzeranmeldung und gibt eine `allow`-Entscheidung aus.
    *   **Public** verwendet eine `bypass`-Entscheidung, sodass die Anwendung offen bleibt, Geo-Blockaden aber dennoch berücksichtigt werden.
5.  Füllen Sie die Eingabefelder aus, die für den gewählten Modus erscheinen (E-Mails für "Authenticated", optionale Länderliste für beide).
6.  Passen Sie optionale Einstellungen wie Sitzungsdauer, App-Launcher-Sichtbarkeit und die automatische Weiterleitung zum IdP (Identity Provider) an, falls Sie im "Authenticated"-Modus sind.
7.  Speichern Sie die Gruppe. DockFlare schreibt die Definition lokal und synchronisiert sie mit Cloudflare als `DockFlare-AccessGroup-<id>`.

### Schritt 2: Anwenden der Access Group

Sobald sie erstellt ist, haben Sie zwei Möglichkeiten, Ihre Access Group auf einen Dienst anzuwenden:

#### A) Mit einem Docker Label (Die empfohlene Methode)

Fügen Sie bei jedem neuen oder bestehenden Container einfach das Label `dockflare.access.group` mit der ID der von Ihnen erstellten Gruppe hinzu.

```yaml
services:
  grafana:
    image: grafana/grafana
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=monitoring.example.com"
      - "dockflare.service=http://grafana:3000"
      # Apply the entire policy with one simple label:
      - "dockflare.access.group=admin-users"
```
Sie können auch mehrere Gruppen anwenden, indem Sie `dockflare.access.groups` mit einer kommagetrennten Liste von IDs verwenden:
`dockflare.access.groups=admin-users,home-network`

#### Systemverwaltete Richtlinien

DockFlare bietet zwei integrierte Systemrichtlinien, die automatisch verfügbar sind:

- **`public-default-bypass`** - Öffentlicher Zugriff mit Bypass-Entscheidung (für wirklich öffentliche Dienste verwenden)
- **`authenticated-default`** - Standardauthentifizierung mit Einmal-PIN + E-Mail-Einschränkung

Diese Systemrichtlinien sind nicht löschbar und dienen als Basis für den Zonenschutz sowie die Migration alter Labels.

#### B) Über die Web-UI (Für manuelle Regeln oder Überschreibungen)

Sie können eine Access Group auch direkt aus dem Dashboard auf jede Regel anwenden:
1.  Suchen Sie die Ingress-Regel, die Sie ändern möchten, auf dem Haupt-Dashboard.
2.  Klicken Sie auf den Button **"Manage Rule"** (Regel verwalten).
3.  Wählen Sie im Bearbeitungsmodal Ihre gewünschte(n) Access Group(s) aus dem Dropdown-Menü "Access Groups".
4.  Speichern Sie die Änderungen.

Dies ist perfekt, um Richtlinien auf manuell erstellte Regeln (für Nicht-Docker-Dienste) anzuwenden oder um eine durch Docker-Labels definierte Richtlinie vorübergehend zu überschreiben.

---

## Richtlinienbeispiele

Hier sind einige gängige Richtlinienkonfigurationen, die Sie innerhalb einer Access Group erstellen können.

### Beispiel 1: Authentifizierung per E-Mail

Dies ist der häufigste Anwendungsfall: Sie erlauben nur bestimmten Benutzern Zugriff, die sich mit Ihrem konfigurierten Identity Provider authentifizieren können (z.B. Google, GitHub oder durch einen Einmal-PIN, der an ihre E-Mail gesendet wird).

*   **Gruppen-ID:** `admin-users`
*   **Modus:** *Authenticated*
*   **Zugelassene E-Mails:** `user1@example.com`, `user2@example.com`
*   **Sitzungsdauer:** `24h`

DockFlare erstellt eine wiederverwendbare Richtlinie mit einer `allow`-Entscheidung für die aufgelisteten E-Mails und einer grundsätzlichen `deny`-Regel für alle anderen. Wenden Sie die Gruppe mit `dockflare.access.group=admin-users` an.

### Beispiel 2: Eigene Heim-IP-Adresse zulassen

Diese Richtlinie beschränkt den Zugriff auf Ihr Heimnetzwerk, sodass Sie die Anmeldeaufforderung überspringen können, wenn Sie sich auf einer vertrauenswürdigen IP befinden, andernorts aber weiterhin eine Authentifizierung erzwungen wird.

1.  **Ermitteln Sie Ihre öffentliche IP:** Suchen Sie in Ihrem Browser nach "wie ist meine ip". Ihre öffentliche IP-Adresse wird angezeigt (z. B. `203.0.113.55`).
2.  **Erstellen Sie die Access Group:**
    *   **Gruppen-ID:** `home-network`
    *   **Modus:** *Authenticated*
    *   **Zugelassene E-Mails:** `you@example.com`
    *   **Bypass IPs:** Fügen Sie im entsprechenden Feld `203.0.113.55/32` hinzu

DockFlare generiert eine Richtlinie, die zuerst Ihren IP-Bereich umgeht (`bypass`) und dann die aufgelisteten E-Mails zur Authentifizierung auffordert. Alle anderen erhalten ein `deny`.

### Beispiel 3: Geo-Fencing (Mehrere Länder blockieren)

Diese Richtlinie hält Ihre Marketing-Website öffentlich zugänglich, schränkt aber den Traffic aus bestimmten Regionen ein.

*   **Gruppen-ID:** `public-eu`
*   **Modus:** *Public*
*   **Blockierte Länder:** `RU`, `CN`, `KP`

Die resultierende wiederverwendbare Richtlinie gibt für alle eine `bypass`-Entscheidung heraus, schließt jedoch die genannten Länder aus. Kombinieren Sie sie mit anderen Gruppen, wenn Sie weitere Filter schichten müssen (`dockflare.access.groups=public-eu,admin-users`).

---

## Zonen-Standardrichtlinien - Sicherheits-Best-Practice

### Was sind Zonen-Standardrichtlinien?

Zonen-Standardrichtlinien sind Wildcard `*.domain.com` Access-Anwendungen, die automatisch alle Subdomains einer DNS-Zone schützen, einschließlich derer, die Sie noch nicht explizit konfiguriert haben.

### Warum Sie diese benötigen

**Das Problem:** Wenn Sie vergessen, einem Dienst eine Access-Richtlinie hinzuzufügen, ist dieser standardmäßig öffentlich zugänglich.

**Die Lösung:** Eine Wildcard-Richtlinie auf Zonenebene fungiert als Sicherheitsnetz. Auch wenn Sie vergessen, `vergessener-dienst.ihredomain.com` zu konfigurieren, wird die Richtlinie für `*.ihredomain.com` eingreifen.

### So richten Sie sie ein

1. Navigieren Sie zur Seite **Access Policies**
2. Scrollen Sie zum Bereich **Zone Default Policies (*.tld Wildcards)**
3. Achten Sie auf Zonen mit dem Warnschild "Not Protected" ⚠️
4. Klicken Sie auf **Create Policy**
5. Wählen Sie eine geeignete Zugriffsgruppe aus:
   - **Für öffentliche Domains:** Nutzen Sie `public-default-bypass`
   - **Für interne Domains:** Nutzen Sie eine Authentifizierungsrichtlinie
   - **Für gemischte Nutzung:** Nutzen Sie Ihre strengste Richtlinie

### Best Practices

- ✅ **Erstellen Sie immer Zonenrichtlinien** für Produktionsdomains
- ✅ **Verwenden Sie Authentifizierungsrichtlinien** für interne/private Zonen
- ✅ **Verwenden Sie öffentlichen Bypass** nur für wirklich öffentliche Zonen
- ✅ **Überprüfen Sie regelmäßig** - checken Sie den Zonenschutzstatus monatlich
- ⚠️ **Beachten Sie die Priorität** - Spezifische Hostnamen-Richtlinien überschreiben Wildcard-Richtlinien

### Reihenfolge der Richtlinienpriorität

Cloudflare bewertet Access Policies in dieser Reihenfolge:

1. **Exakte Übereinstimmung des Hostnamens** (z.B. `app.example.com`) - Höchste Priorität
2. **Wildcard-Übereinstimmung** (z.B. `*.example.com`) - Fallback
3. **Keine Übereinstimmung** = Öffentlicher Zugriff (keine Access App) - Standard

Das bedeutet, dass Sie eine restriktive Zonen-Standardrichtlinie festlegen können und dennoch Ausnahmen für einzelne dedizierte Dienste erlauben dürfen.

---

## Externe Cloudflare-Richtlinien verwalten

### Verständnis der Richtlinientypen

DockFlare zeigt auf der Seite "Access Policies" drei Arten von Richtlinien an, jede mit einem visuellen Badge versehen:

- **🟦 DockFlare** - Von DockFlare erstellte und verwaltete Richtlinien (Präfix: `DockFlare-`)
- **🟪 External** - Außerhalb von DockFlare erstellte Richtlinien (manuell oder durch andere Tools)
- **🟧 System** - Nicht löschbare Systemrichtlinien (`public-default-bypass`, `authenticated-default`)

### Externe Richtlinien synchronisieren

Standardmäßig importiert DockFlare nur Richtlinien mit dem Präfix `DockFlare-`. Dies hält Ihre Richtlinienliste sauber und auf Ihre Container-Infrastruktur fokussiert.

**Um ALLE Cloudflare-Richtlinien zu synchronisieren** (einschließlich der manuell erstellten):

1. Setzen Sie die Umgebungsvariable: `SYNC_ALL_CLOUDFLARE_POLICIES=true`
2. Starten Sie DockFlare neu
3. Klicken Sie auf der Seite "Access Policies" auf **"Sync from Cloudflare"**

Externe Richtlinien werden dann mit einem violetten Badge **"External"** versehen.

### Warum Externe Richtlinien importieren?

**Vorteile:**
- Vollständige Sichtbarkeit Ihres gesamten Cloudflare Access Setups
- Wiederverwendung bestehender Richtlinien ohne Neuerstellung
- Zentrale Verwaltung in einer Oberfläche
- Anwendung jeder beliebigen Richtlinie auf jeden Dienst (ob von DockFlare verwaltet oder nicht)

**Nachteile:**
- Längere Richtlinienliste, wenn Sie viele externe Richtlinien haben
- Gefahr der versehentlichen Manipulation von Richtlinien, die von nicht in DockFlare enthaltenen Diensten genutzt werden

### Organisation Ihrer Richtlinien

**Pro-Tipp:** Benennen Sie externe Richtlinien in Cloudflare um, sodass sie das `DockFlare-`-Präfix nutzen.

Sie können externe Richtlinien organisieren, indem Sie diese im Cloudflare Dashboard umbenennen:

1. Öffnen Sie die Richtlinie in **Cloudflare Zero Trust**
2. Benennen Sie sie um, sodass das Präfix `DockFlare-` genutzt wird (z.B. `DockFlare-LegacyVPN` oder `DockFlare-ThirdPartyApp`)
3. Klicken Sie in DockFlare auf **"Sync from Cloudflare"**
4. Die Richtlinie erscheint nun als **von DockFlare verwaltete** Richtlinie (blauer Badge)

Dadurch können Sie:
- ✅ Alle von DockFlare einsehbaren Richtlinien mit konsistenter Benennung gruppieren
- ✅ Richtlinien sortieren oder nach Typ filtern
- ✅ Unterscheiden zwischen "von DockFlare verwaltet" und "nur in DockFlare sichtbar"

### Filtern von Richtlinien

Nutzen Sie das Dropdown-Menü **Filter**, um bestimmte Typen anzuzeigen:

- **All Policies** - Zeigt alles an (DockFlare, External, System)
- **DockFlare-Managed** - Zeigt nur Richtlinien mit blauer Plakette
- **External** - Zeigt nur Richtlinien mit violetter Plakette
- **System** - Zeigt nur Systemrichtlinien an

### Sicherheitsfunktionen

**Schutz von externen Richtlinien:**

Es wird eine Warnung in DockFlare angezeigt, wenn externe Richtlinien gelöscht oder geändert werden:

> ⚠️ WARNUNG: Dies ist eine EXTERNE Richtlinie, die nicht durch DockFlare erstellt wurde.
>
> Das Modifizieren dieser Richtlinie kann Dienste außerhalb von DockFlare beeinflussen.
>
> Sind Sie absolut sicher?

Das verhindert unbeabsichtigte Modifikationen an Konfigurationen, die durch andere Tools erstellt wurden.

### Best Practices

1. **Standard-Setup (Empfohlen):**
   - Behalten Sie `SYNC_ALL_CLOUDFLARE_POLICIES=false` bei (Standard)
   - Es werden nur von DockFlare verwaltete Richtlinien angezeigt
   - Eine aufgeräumte, fokussierte Liste von Richtlinien

2. **Fortgeschrittenes Setup (Power-User):**
   - Aktivieren Sie `SYNC_ALL_CLOUDFLARE_POLICIES=true`
   - Alle Richtlinien werden in einer Oberfläche angezeigt und verwaltet
   - Benennen Sie externe Richtlinien mit dem `DockFlare-` Präfix zur besseren Übersicht

3. **Hybrider Ansatz:**
   - Lassen Sie die Synchronisation im Allgemeinen ausgeschaltet
   - Benennen Sie wichtige Richtlinien manuell in Cloudflare auf `DockFlare-*` um
   - Diese erscheinen nach dem nächsten Sync sofort

4. **Regelwerk für Namensgebung:**
   ```
   DockFlare-AccessGroup-<id>     # Auto-generated by access groups
   DockFlare-<custom-name>         # Your renamed external policies
   <anything-else>                 # Pure external (only visible if sync enabled)
   ```
