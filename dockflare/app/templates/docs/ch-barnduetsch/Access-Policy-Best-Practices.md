# Best Practices für Zuegriffsrichtlinie

Ds stärksti Sicherheitswärkzüg i DockFlare si d **Access Groups**. Si gäbe dir wiederverwendbari, zentral verwalteti Zugriffsregle für dini Dienscht.

## Die "Goldene Regel": Bruuch Access Groups

D wichtigschti Regel isch eifach: **Bruuch Access Groups für aui häufige Zugriffs-Fäll**.

Statt uf jedem Container mehri einzelni Labels für E-Mail, Land oder Bypass z pflege, leisch du e Gruppe einisch a u weist sie nachhär mit `dockflare.access.group` zue.

---

## So erstellsch u bruuchsch du Access Groups

E Access Group isch schnäu gmacht u passiert komplett i dr DockFlare-UI.

### Schritt 1: Access Group aalege

1. Gang uf **Access Policies**
2. Klick uf **Add Access Group**
3. Gib ere Gruppe e sauberi ID wie `admin-users`, `home-network` oder `geo-block`
4. Wähl dr Modus:
   * **Authenticated** für Login-geschützte Zugäng
   * **Public** für öffentliche Dienscht mit `bypass`
5. Trag d nötige Date ii
6. Speicher d Gruppe

### Schritt 2: Access Group aa hänge

Du chasch d Gruppe uf zwöi Art aa hänge:

#### A) Mit em Docker-Label

Das isch dr empfohlni Wäg. Trag eifach `dockflare.access.group=<id>` ii.

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
Für mehri Gruppe git s `dockflare.access.groups` mit ere kommagtrennti Liste:
`dockflare.access.groups=admin-users,home-network`

#### Systemverwaltete Richtlinien

DockFlare het zwöi integrierte Systemrichtlinie:

- **`public-default-bypass`** - Öffentlicher Zugriff mit Bypass-Entscheidung (für wirklich öffentliche Dienste bruuche)
- **`authenticated-default`** - Standardauthentifizierung mit Einmal-PIN + E-Mail-Einschränkung

Die si nid löschbar u diene als Basis für Zoneschutz u d Migration vo alte Labels.

#### B) Direkt i dr Web UI

Du chasch d Gruppe o direkt im Dashboard zuewyse:
1. Regel sueche
2. **Manage Rule** ufmache
3. Access Group(s) uswähle
4. speichere

Das isch praktisch für manuell aagleiti Regle oder temporäri Overrides.

---

## Richtlinienbeispiele

Hier si einige gängige Richtlinienkonfigurationen, die du innerhalb einer Access Group erstellen chöi.

### Beispiel 1: Authentifizierung per E-Mail

Das isch der häufigste Anwendungsfall: du erlauben nur bestimmten Benutzern Zugriff, die sich mit dim konfigurierten Identity Provider authentifizieren chöi (z.B. Google, GitHub oder durch einen Einmal-PIN, der an ihre E-Mail gesendet wird).

*   **Gruppen-ID:** `admin-users`
*   **Modus:** *Authenticated*
*   **Zugelassene E-Mails:** `user1@example.com`, `user2@example.com`
*   **Sitzungsdauer:** `24h`

DockFlare erstellt e wiederverwendbari Richtlinie mit ere `allow`-Entscheidig für die uufglischtete E-Mails u ere grundsätzliche `deny`-Regle für alli andere. Wend d'Gruppe mit `dockflare.access.group=admin-users` aa.

### Beispiel 2: Eigene Heim-IP-Adresse zulassen

Diese Richtlinie beschränkt den Zugriff auf din Heimnetzwerk, sodass du die Anmeldeaufforderung überspringen chöi, wenn du di auf einer vertrauenswürdigen IP befinden, andernorts aber weiterhin eine Authentifizierung erzwungen wird.

1.  **Ermitteln du dini öffentliche IP:** Suech in dim Browser nach "wie isch meine ip". dini öffentliche IP-Adresse wird angezeigt (z. B. `203.0.113.55`).
2.  **Erstell die Access Group:**
    *   **Gruppen-ID:** `home-network`
    *   **Modus:** *Authenticated*
    *   **Zugelassene E-Mails:** `you@example.com`
    *   **Bypass IPs:** Füg im entsprechenden Feld `203.0.113.55/32` hinzu

DockFlare generiert eine Richtlinie, die zuerst dini IP-Bereich umgeht (`bypass`) u dann die aufgelisteten E-Mails zur Authentifizierung auffordert. Alle anderen erhalten ein `deny`.

### Beispiel 3: Geo-Fencing (Mehrere Länder blockieren)

Diese Richtlinie hält dini Marketing-Website öffentlich zugänglich, schränkt aber den Traffic aus bestimmten Regionen ein.

*   **Gruppen-ID:** `public-eu`
*   **Modus:** *Public*
*   **Blockierte Länder:** `RU`, `CN`, `KP`

Die resultierende wiederverwendbare Richtlinie gibt für alle eine `bypass`-Entscheidung heraus, schliesst jedoch die genannten Länder aus. Kombinier sie mit anderen Gruppen, wenn du weitere Filter schichten müesse (`dockflare.access.groups=public-eu,admin-users`).

---

## Zonen-Standardrichtlinien - Sicherheits-Best-Practice

### Was si Zonen-Standardrichtlinien?

Zonen-Standardrichtlinien si Wildcard `*.domain.com` Access-Aawändige, wo automatisch alli Subdomains vo nere DNS-Zone schütze, inkl. die, wo du no nid explizit konfiguriert hesch.

### Warum du diese benötigen

**Das Problem:** Wänn du vergessen, einem Dienst eine Access-Richtlinie hinzuzufügen, isch dieser standardmässig öffentlich zugänglich.

**Die Lösung:** Eine Wildcard-Richtlinie auf Zonenebene fungiert als Sicherheitsnetz. Auch wenn du vergessen, `vergessener-dienst.ihredomain.com` zu konfigurieren, wird die Richtlinie für `*.ihredomain.com` eingreifen.

### So richtsch si ii

1. Navigier zur Seite **Access Policies**
2. Scroll zum Bereich **Zone Default Policies (*.tld Wildcards)**
3. Acht auf Zonen mit dem Warnschild "Not Protected" ⚠️
4. Klick uf **Create Policy**
5. Wähl eine geeignete Zugriffsgruppe aus:
   - **Für öffentliche Domains:** Bruuch `public-default-bypass`
   - **Für interne Domains:** Bruuch eine Authentifizierungsrichtlinie
   - **Für gemischte Nutzung:** Bruuch dini strengste Richtlinie

### Best Practices

- ✅ **Erstell immer Zonenrichtlinien** für Produktionsdomains
- ✅ **Bruuch Authentifizierungsrichtlinien** für interne/private Zonen
- ✅ **Bruuch öffentlichen Bypass** nur für wirklich öffentliche Zonen
- ✅ **Lueg regelmässig** - check dr Zonenschutzstatus monätlich
- ⚠️ **Beacht die Priorität** - Spezifische Hostnamen-Richtlinien überschreiben Wildcard-Richtlinien

### Reihenfolge der Richtlinienpriorität

Cloudflare bewertet Access Policies in dieser Reihenfolge:

1. **Exakte Übereinstimmung des Hostnamens** (z.B. `app.example.com`) - Höchste Priorität
2. **Wildcard-Übereinstimmung** (z.B. `*.example.com`) - Fallback
3. **Keine Übereinstimmung** = Öffentlicher Zugriff (kener Access App) - Standard

Das bedeutet, dass du eine restriktive Zonen-Standardrichtlinie festlegen chöi u dennoch Ausnahmen für einzelne dedizierte Dienste erlauben dürfen.

---

## Externe Cloudflare-Richtlinien verwalten

### Verständnis der Richtlinientypen

DockFlare zeigt auf der Seite "Access Policies" drei Arten von Richtlinien an, jede mit einem visuellen Badge versehen:

- **🟦 DockFlare** - Von DockFlare erstellte u verwaltete Richtlinien (Präfix: `DockFlare-`)
- **🟪 External** - Ausserhalb von DockFlare erstellte Richtlinien (manuell oder durch andere Tools)
- **🟧 System** - Nicht löschbare Systemrichtlinien (`public-default-bypass`, `authenticated-default`)

### Externe Richtlinien synchronisieren

Standardmässig importiert DockFlare nur Richtlinien mit dem Präfix `DockFlare-`. Das hält dini Richtlinienliste sauber u auf dini Container-Infrastruktur fokussiert.

**Um ALLE Cloudflare-Richtlinien zu synchronisieren** (einschliesslich der manuell erstellten):

1. Setz die Umgebungsvariable: `SYNC_ALL_CLOUDFLARE_POLICIES=true`
2. Start DockFlare neu
3. Klick uf der Seite "Access Policies" auf **"Sync from Cloudflare"**

Externe Richtlinien wärde dann mit einem violetten Badge **"External"** versehen.

### Warum Externe Richtlinien importieren?

**Vorteile:**
- Vollständige Sichtbarkeit din gesamten Cloudflare Access Setups
- Wiederverwendung bestehender Richtlinien ohne Neuerstellung
- Zentrale Verwaltig in einer Oberfläche
- Anwendung jeder beliebigen Richtlinie auf jeden Dienst (öb von DockFlare verwaltet oder nid)

**Nachteile:**
- Längeri Richtlinienliste, wänn du vil externi Richtlinie hesch
- Gefahr der versehentlichen Manipulation von Richtlinien, die von nid in DockFlare enthaltenen Diensten genutzt wärde

### Organisation dinere Richtlinien

**Pro-Tipp:** Benenn externe Richtlinien in Cloudflare um, sodass sie das `DockFlare-`-Präfix nutzen.

Du chasch externe Richtlinien organisieren, indem du diese im Cloudflare Dashboard umbenennen:

1. Mach uf die Richtlinie in **Cloudflare Zero Trust**
2. Benenn sie um, sodass das Präfix `DockFlare-` genutzt wird (z.B. `DockFlare-LegacyVPN` oder `DockFlare-ThirdPartyApp`)
3. Klick in DockFlare auf **"Sync from Cloudflare"**
4. Die Richtlinie erscheint nun als **von DockFlare verwaltete** Richtlinie (blauer Badge)

Dadurch chasch:
- ✅ Alle von DockFlare einsehbaren Richtlinien mit konsistenter Benennung gruppieren
- ✅ Richtlinien sortieren oder nach Typ filtern
- ✅ Unterscheiden zwischen "von DockFlare verwaltet" u "nur in DockFlare sichtbar"

### Filtern von Richtlinien

Bruuch das Dropdown-Menü **Filter**, um bestimmte Typen anzuzeigen:

- **All Policies** - Zeigt alles an (DockFlare, External, System)
- **DockFlare-Managed** - Zeigt nur Richtlinien mit blauer Plakette
- **External** - Zeigt nur Richtlinien mit violetter Plakette
- **System** - Zeigt nur Systemrichtlinien an

### Sicherheitsfunktionen

**Schutz von externen Richtlinien:**

Es wird eine Warnung in DockFlare angezeigt, wenn externe Richtlinien gelöscht oder geändert wärde:

> ⚠️ WARNUNG: Das isch eine EXTERNE Richtlinie, die nid durch DockFlare erstellt wurde.
>
> Das Modifizieren dieser Richtlinie cha Dienste ausserhalb von DockFlare beeinflussen.
>
> Bisch du der ganz sicher?

Das verhindert unbeabsichtigte Modifikationen an Konfigurationen, die durch andere Tools erstellt wurden.

### Best Practices

1. **Standard-Setup (Empfohlen):**
   - Bhalt `SYNC_ALL_CLOUDFLARE_POLICIES=false` bi (Standard)
   - Es wärde nur von DockFlare verwaltete Richtlinien angezeigt
   - Eine aufgeräumte, fokussierte Liste von Richtlinien

2. **Fortgschrittenes Setup (Power-User):**
   - Aktivier `SYNC_ALL_CLOUDFLARE_POLICIES=true`
   - Alle Richtlinien wärde in einer Oberfläche angezeigt u verwaltet
   - Benenn externi Richtlinie mit em `DockFlare-` Präfix für bessere Überblick

3. **Hybrider Ansatz:**
   - Lass die Synchronisation im Allgemeinen ausgeschaltet
   - Benenn wichtige Richtlinien manuell in Cloudflare auf `DockFlare-*` um
   - Diese erscheinen nach dem nächsten Sync sofort

4. **Regelwerk für Namensgebung:**
   ```
   DockFlare-AccessGroup-<id>     # Auto-generated by access groups
   DockFlare-<custom-name>         # Your renamed external policies
   <anything-else>                 # Pure external (only visible if sync enabled)
   ```
