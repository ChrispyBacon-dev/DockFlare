# Zugriff auf die Web UI

Sobald der DockFlare-Container erfolgreich gestartet wurde, chasch die Web UI aufrufen, um dini Istellige zu verwalten, den Status dinere Tunnel einzusehen u Ingress-Regeln manuell zu konfigurieren.

## Standard-URL

Standardmässig isch d'DockFlare-Web UI über Port `5000` erreichbar. Mach im Browser uf u rüef die URL uf:

```
http://<your-server-ip>:5000
```

Ersetz `<your-server-ip>` durch die IP-Adresse des Servers, auf dem DockFlare ausgeführt wird.

## Ersteinrichtung

Biim erschte Ufrruuf vo dr Web UI führt di dr **Assistent für d'Erstiirichtig** durch d'Konfiguration. Er hilft dir bi dene Schritt:

1.  Wiederherstellung us eme vorhandene DockFlare-Backup (`dockflare_backup_*.zip`). Wänn du die Option wählsch, importiert s'System dini verschlüssleti Konfiguration, dr Status u d'Agent-Schlüssel u startet dr Container nachhär automatisch neu.
2.  Erstell es Admin-Konto u es Passwort für d'Web UI.
3.  Gib dini Cloudflare-Konto-ID, Zonen-ID (optional) u dis API-Token aa.
4.  Bestätig d'Tunneleistellige u schliess s'Onboarding ab.

## Anmeldung

Nach dr Erstiirichtig gsehsch bi jedem Zuegriff uf d'Web UI e Aamäldebildschirm. Mäld di mit em Passwort aa, wo du während dr Iirichtig feschtgleit hesch.

## Passwort-Anmeldung deaktivieren

DockFlare het d'Istellige „Passwort-Aameldig deaktivieren“ für fortgeschritteni Deployments, wo DockFlare sowieso scho hinger ere externe Authentifizierigsschicht wie Cloudflare Access lauft. **Für d'meischte Setups röt mer aber klar dergege.**

### Warum es diese Istellige gibt

Wänn du DockFlare hinger Cloudflare Access oder eme angere Authentifizierungs-Proxy betreibsch, wo SSO scho vor em Zuegriff uf d'Aawändig erzwunge wird, chasch d'integrierti Passwort-Aameldig vo DockFlare abschalte, demit du di nid dopplet muesch aamelde.

### Sicherheitsrisiken bei aktivierter Option

- ⚠️ **Alle API-Endpunkte si ohne Authentifizierung erreichbar**, wenn diese Istellige aktiviert isch.
- ⚠️ **Sichtbarkeit im Docker-Netzwerk:** Selbst wenn DockFlare im öffentlichen Internet durch Cloudflare Access geschützt isch, chöi Container im selben Docker-Netzwerk die externe Authentifizierung umgehen u direkt auf die DockFlare-API zugreifen.
- ⚠️ **Keine eigene Durchsetzung der Authentifizierung:** Die Anwendung geht davon aus, dass die externe Authentifizierung den Schutz vollständig übernimmt.

### Beispiel für einen Angriffsweg

```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

Auch wenn DockFlare über Cloudflare Access vom Internet abgeschirmt isch, cha jeder Container im selben Docker-Netzwerk diesen Schutz umgehen u ohne Authentifizierung direkt auf die API-Endpunkte zugreifen.

### Empfohlene Vorgehensweise

Statt d'Passwort-Aameldig z'deaktiviere, nimmsch e vo dene sichere Optionä:

1. **Lokali DockFlare-Zuegangsdate** - Eifachi, i DockFlare integriereti Passwort-Authentifizierig
2. **OAuth/OIDC-Aabieter** - Konfigurier Google, GitHub, Azure AD oder angeri Identitätsaabieter für komfortables Single Sign-On ohni Sicherheitsverlust (siehe [OAuth-Anbieter-Einrichtung](OAuth-Provider-Setup.md))

Beidi Optionä gits der e sauberi Authentifizierig u trotz däm dr Komfort vo SSO. Mit OAuth hesch Single Sign-On, ohni d'Sicherheitsrisike vo ere deaktivierte Authentifizierig in Chouf z'näh.

### Fazit

Wänn du nid grad e sehr spezifischi u richtig guet verstandeni Sicherheitsarchitektur mit sauberer Netzwerkisolierig hesch, söttsch d'Passwort-Aameldig aktiviert lah u für meh Komfort OAuth bruuche.
