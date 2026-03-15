# Häufige Probleme

Diese Seite listet einige der gängigen Probleme auf, auf die Benutzer stoßen könnten, sowie Lösungswege dazu.

---

### Problem: Der DockFlare-Container startet nicht oder befindet sich in einer Neustartschleife.

**Lösung:**
1.  **Docker-Logs überprüfen:** Der erste Schritt ist immer, die Logs des DockFlare-Containers zu prüfen. Führen Sie diesen Befehl aus:
    ```bash
    docker logs dockflare
    ```
2.  **Nach Fehlern suchen:** Suchen Sie nach Fehlermeldungen. Häufige Ursachen sind:
    *   Eine ungültige `docker-compose.yml` Datei (z.B. falsche Syntax, Probleme mit Volumen-Mounts).
    *   Probleme beim Docker Daemon direkt.
    *   Probleme mit der Konnektivität oder Berechtigungen beim Dienst `docker-socket-proxy` oder der `DOCKER_HOST`-Einstellung.

---

### Problem: DNS-Einträge werden in Cloudflare nicht angelegt.

**Lösung:**
1.  **DockFlare-Logs überprüfen:** Suchen Sie nach Fehlermeldungen, die sich auf die Cloudflare-API beziehen. Die Protokolle verraten oft präzise, warum der API-Aufruf fehlschlug.
2.  **API-Token Berechtigungen prüfen:** Dies ist die häufigste Ursache. Stellen Sie sicher, dass Ihr Cloudflare API-Token die erforderlichen Rechte besitzt. Sie benötigen mindestens:
    *   `Zone:DNS:Edit` für jede Zone, die DockFlare verwalten soll.
    *   `Zone:Zone:Read`
3.  **Zonenkonfiguration verifizieren:**
    *   Stellen Sie sicher, dass die während der Einrichtung angegebene **Zone ID** korrekt ist.
    *   Wenn Sie das Label `dockflare.zonename` verwenden, prüfen Sie, ob der Zonenname fehlerfrei geschrieben ist.

---

### Problem: Eine Access Policy (Zero Trust) wird nicht auf einen Dienst angewandt.

**Lösung:**
1.  **API-Token Berechtigungen prüfen:** Ihr API-Token benötigt `Account:Access: Apps and Policies:Edit` Rechte.
2.  **UI-Overrides prüfen:** Sehen Sie im Dashboard nach, ob die Regel den Status "UI Override" hat. Die Benutzeroberfläche dominiert über Container-Labels.
3.  **Group ID checken:** Bei der Verwendung von `dockflare.access.group` beachten Sie, dass der angegebene Bezeichner **strikt** dem im Dashboard konfigurierten Group Identifier der Policy entspricht!
4.  **Cloudflare Dashboard prüfen:** Es empfiehlt sich, über Cloudflare (Zero Trust) den direkten Status unter Anwendungen auszugeben, falls API Fehlermeldungen abweichend nicht sichtbar blieben im Log.

---

### Problem: Ich erhalte einen `ERR_TOO_MANY_REDIRECTS` Fehler beim Aufruf meines Dienstes.

**Lösung:**
Dieser Fehler tritt fast immer aufgrund einer Fehlkonfiguration der SSL/TLS-Einstellungen zwischen Ihrem Ursprungsdienst und Cloudflare auf.

1.  **Cloudflare SSL/TLS Modus prüfen:** Gehen Sie in Ihrem Cloudflare-Dashboard zu den SSL/TLS-Einstellungen Ihrer Domain. Stellen Sie sicher, dass Ihr Verschlüsselungsmodus auf **Full (Strict)** (Vollständig (Streng)) eingestellt ist.
2.  **Doppelte Redirects vermeiden:** Der "Flexible" SSL-Modus in Cloudflare kann dieses Problem verursachen, wenn auch Ihre Backend-Anwendung von HTTP auf HTTPS umleiten möchte. Der Browser verfängt sich in einer Endlosschleife.
3.  **Nutzen Sie `https` in Ihrer Dienst-URL:** Wenn Ihr Backend HTTPS unterstützt, verwenden Sie `https://` in Ihrem `dockflare.service`-Label (z.B. `dockflare.service=https://my-app:443`). Damit wird die Verbindung von `cloudflared` zu Ihrem Dienst ebenfalls verschlüsselt.

---

### Problem: Ein Dienst hinter Traefik/Proxmox funktioniert nur, wenn Cloudflares "Match SNI to Host" aktiviert ist.

**Lösung:**
1.  Bearbeiten Sie die manuelle Regel in DockFlare und aktivieren Sie **Match SNI to Host**.
2.  Speichern Sie die Regel ab.
3.  Falls Sie auch Cloudflare-seitige Routenfelder erhalten müssen (die DockFlare nicht abbildet), gehen Sie zu **Settings → General Settings** und aktivieren Sie **Preserve Unmanaged Cloudflare Ingress Fields**.

---

### Problem: Der verwaltete `cloudflared-agent` Container startet nicht und meldet einen "stale network" (veraltetes Netzwerk) Fehler.

**Lösung:**
Dies passiert, wenn das genutzte Docker Subnetz aus dem Compose Set abgerissen (gelöscht) und neu erschaffen wurde. DockFlare hat automatische Mechanismen hierfür.

1.  **DockFlare neustarten:** Das simple Neustarten von DockFlare (`docker compose restart dockflare`) behebt dieses Phänomen im Handumdrehen.
2.  **Wie dies agiert:** Beim Start überprüft DockFlare den Zustand seiner Agenten. Fällt hierbei exakt dieser Problemherd ins Gewicht, entfernt DockFlare verwaiste Tunnel-Instanzen und erstellt Ersatz direkt. Dies ist ein Patch-Fix für neuere Generationen des Systems. (Versionserfordernis `v1.9.5` oder neuer).
