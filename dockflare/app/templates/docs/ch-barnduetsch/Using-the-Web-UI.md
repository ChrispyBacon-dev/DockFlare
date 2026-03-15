# Web UI bruuche

D DockFlare Web UI git dr d volle Kontroll über dini Ingress-Regle, Zuegriffsrichtlinie, Tunnel u Systemiistellige. S meischte chasch zwar über Docker-Labels steuere, aber i dr Web UI chasch Sache prüefe, manuell aapasse u Problem schnäll analysiere.

## Ds Dashboard

Nach em Aamälde landisch uf em Dashboard. Das isch d zentrali Übersichts-Syte für dini verwaltete Dienscht.

* **Verwalteti Ingress-Regle**: I dr Tabelle gsehsch aui Regle, wo DockFlare verwaltet, egal ob si us Docker chöme oder manuell aagleit worde sy.
  * **Hostname**: Dr öffentlechi Hostname vom Dienscht.
  * **Service**: Ds interne Ziel, wo Cloudflare dr Traffic häreschickt.
  * **Source**: Zeigt, ob d Regle us `Docker` chunnt oder `Manually` i dr UI aagleit worde isch.
  * **Status**: Zeigt, ob e Regle `active`, `pending_deletion` oder mit eme `UI Override` verseh isch.
  * **Access**: Zeigt d zuegwieseni Access Group, dr Modus u je nach Fall direkti Links zu Cloudflare.
  * **Manage Rule**: Öffnet d Bearbeitig vo dr jeweilige Regle.
* **Echtzyt-Logs**: Under dr Tabelle gsehsch e Log-Ansicht, wo d Usgabe vom DockFlare-Backend live streamt. Das isch bsunders nützlich für Debugging.

## Regle verwalte

I dr Web UI chasch Regle nid nume aaluege, sondern ou diräkt verwalte.

* **Manuelli Regle derzue tue**: Mit em Button **Add Manual Rule** chasch Regle für Dienscht aalege, wo nid i Docker loufe, zum Bispiel e Dienst uf eme angere Server oder eme Grät im LAN.
* **Regle bearbeite**: Mit **Manage Rule** chasch e einzelni Regle aapasse. Das isch vor allem praktisch, wänn du Docker-Labels temporär oder dauerhaft via UI überschrybe wotsch.
* **Uf Labels zrüggsetze**: Wänn e us Docker stammendi Regle e UI-Override het, chasch si mit **Revert to Labels** wieder uf dr Docker-Zuestand zrüggsetze.

## Access Policies

D Syte **Access Policies** isch dr Ort für wiederverwendbari **Access Groups**, **Identity Providers** u **Zone Default Policies**.

### Access Groups

Mit Access Groups chasch Richtlinie zentral verwalte u über Labels oder d UI mehfach wiederverwände.

I däm Bereich chasch:

* nöii Access Groups erstelle
* vorhande Access Groups bearbeite
* nid meh bruuchti Groups lösche
* über **Sync from Cloudflare** vorhandeni Richtlinie importiere
* Richtlinie diräkt im Cloudflare-Dashboard ufmache

**Wichtig:** D Systemrichtlinie `public-default-bypass` wird automatisch vo DockFlare erstellt u verwaltet.

### Zone Default Policies

Mit **Zone Default Policies** chasch ganzi Zonen mit ere Wildcard-Policy absichere, zum Bispiel `*.example.com`.

Das git dr:

* e schnälle Überblick, weli Zonen scho gschützt sy
* e One-Click-Möglichkeit, Wildcard-Policies z erstelle
* e Sicherheitsnetz, falls e einzelni Subdomain nid explizit konfiguriert isch

**Empfohlni Vorgah:** Erstell für alli Domains e Zonen-Standardrichtlinie. Für öffentlechi Domains passt häufig `public-default-bypass`, für interni oder sensitivi Domains söttsch e authentifizieri Richtlinie bruuchen.

Witeri Detail fingsch i [Best Practices & Bispiel für Zuegriffsrichtlinie](Access-Policy-Best-Practices.md).

## Iistellige

Uf dr Syte **Settings** fingsch d zentralen Administrative- u Systemiistellige.

* **Cloudflare Tunnels**: Zeigt aui Tunnel uf dim Account, derzue dr Status u d verbundene `cloudflared`-Agente.
* **Backup & Restore**: Do chasch es vollständigs DockFlare-Backup abelade oder es bestehends Archiv wiederhärstelle.
* **Sicherhäit**:
  * **Change Password**: Ändert ds Passwort für dr Zuegriff uf d Web UI.
  * **Disable Password Login**: Nur für sehr spezifischi Setups sinnvoll. Wänn du das aktiviersch, muesch ganz genau wüsse, wie dini vorglagereti Authentifizierig u dini Netzwerktrennig funktioniere.
* **Cloudflare Credentials**: Aktualisiert Account-ID u API-Token.
* **Core Configuration**: Enthaltet Grundiistellige wie Tunnelname oder d Grace Period.
