# Häufige Probleme

Die Siite listet einige der gängigen Probleme auf, auf die Benutzer stossen könnten, sowie Lösungswege dazu.

---

### Problem: Der DockFlare-Container startet nid oder befindet sich in einer Neustartschleife.

**Lösung:**
1.  **Docker-Logs überprüfen:** Der erste Schritt isch immer, die Logs des DockFlare-Containers zu prüfen. Führ diesen Befehl aus:
    ```bash
    docker logs dockflare
    ```
2.  **Nach Fehlern suchen:** Suech nach Fehlermeldungen. Häufige Ursachen si:
    *   Eine ungültige `docker-compose.yml` Datei (z.B. falsche Syntax, Probleme mit Volumen-Mounts).
    *   Probleme beim Docker Daemon direkt.
    *   Probleme mit der Konnektivität oder Berechtigungen beim Dienst `docker-socket-proxy` oder der `DOCKER_HOST`-Istellige.

---

### Problem: DNS-Einträge wärde in Cloudflare nid angelegt.

**Lösung:**
1.  **DockFlare-Logs überprüfen:** Suech nach Fehlermeldungen, die sich auf die Cloudflare-API beziehen. Die Protokolle verraten oft präzise, warum der API-Aufruf fehlschlug.
2.  **API-Token Berechtigungen prüfen:** Das isch die häufigste Ursache. lueg dass din Cloudflare API-Token die erforderlichen Rechte besitzt. Du bruchsch mindestens:
    *   `Zone:DNS:Edit` für jede Zone, die DockFlare verwalten soll.
    *   `Zone:Zone:Read`
3.  **Zonenkonfiguration verifizieren:**
    *   lueg dass die während der Einrichtung angegebene **Zone ID** korrekt isch.
    *   Wänn du das Label `dockflare.zonename` bruuche, prüef, öb der Zonenname fehlerfrei geschrieben isch.

---

### Problem: Eine Access Policy (Zero Trust) wird nid auf einen Dienst angewandt.

**Lösung:**
1.  **API-Token Berechtigungen prüfen:** din API-Token benötigt `Account:Access: Apps and Policies:Edit` Rechte.
2.  **UI-Overrides prüfen:** Lueg im Dashboard nach, öb die Regel dr Status "UI Override" het. D'UI isch stärker als d'Container-Labels.
3.  **Group ID checken:** Bei der Verwendung von `dockflare.access.group` beacht, dass der angegebene Bezeichner **strikt** dem im Dashboard konfigurierten Group Identifier der Policy entspricht!
4.  **Cloudflare Dashboard prüfen:** Es empfiehlt sich, über Cloudflare (Zero Trust) den direkten Status unter Anwendungen auszugeben, falls API Fehlermeldungen abweichend nid sichtbar blieben im Log.

---

### Problem: Ich erhalte einen `ERR_TOO_MANY_REDIRECTS` Fehler beim Aufruf meines Dienstes.

**Lösung:**
Dieser Fehler tritt fast immer aufgrund einer Fehlkonfiguration der SSL/TLS-Istellige zwischen dim Ursprungsdienst u Cloudflare auf.

1.  **Cloudflare SSL/TLS Modus prüfen:** Gang in dim Cloudflare-Dashboard zu den SSL/TLS-Istellige dinere Domain. lueg dass din Verschlüsselungsmodus auf **Full (Strict)** (Vollständig (Streng)) eingestellt isch.
2.  **Doppelte Redirects vermeiden:** Der "Flexible" SSL-Modus in Cloudflare cha dieses Problem verursachen, wenn auch dini Backend-Anwendung von HTTP auf HTTPS umleiten wott. Der Browser verfängt sich in einer Endlosschleife.
3.  **Bruuch `https` i dinere Dienst-URL:** Wänn dis Backend HTTPS unterstützt, bruuchsch `https://` i dim `dockflare.service`-Label (z.B. `dockflare.service=https://my-app:443`). So isch d'Verbindig vom `cloudflared` zu dim Dienst au verschlüsslet.

---

### Problem: Ein Dienst hinter Traefik/Proxmox funktioniert nur, wenn Cloudflares "Match SNI to Host" aktiviert isch.

**Lösung:**
1.  Bearbeit die manuelle Regel in DockFlare u aktivier **Match SNI to Host**.
2.  Speicher die Regel ab.
3.  Wänn du au Cloudflare-seitigi Routenfelder bruuche muesch (wo DockFlare nid abbildet), gang zu **Settings → General Settings** u aktivier **Preserve Unmanaged Cloudflare Ingress Fields**.

---

### Problem: Der verwaltete `cloudflared-agent` Container startet nid u meldet einen "stale network" (veraltetes Netzwerk) Fehler.

**Lösung:**
Das passiert, wenn das genutzte Docker Subnetz aus dem Compose Set abgerissen (gelöscht) u neu erschaffen wurde. DockFlare hat automatische Mechanismen hierfür.

1.  **DockFlare neustarten:** Das simple Neustarten von DockFlare (`docker compose restart dockflare`) behebt dieses Phänomen im Handumdrehen.
2.  **Wie dies agiert:** Beim Start überprüft DockFlare den Zustand seiner Agenten. Fällt hierbei exakt dieser Problemherd ins Gewicht, entfernt DockFlare verwaiste Tunnel-Instanzen u erstellt Ersatz direkt. Das isch ein Patch-Fix für neuere Generationen des Systems. (Versionserfordernis `v1.9.5` oder neuer).
