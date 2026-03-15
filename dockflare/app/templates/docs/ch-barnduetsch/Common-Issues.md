# Häufigi Problem

Die Syte sammlet e paar vo de Problem, wo bi DockFlare am meischte vorchöme, samt praktische Lösige.

---

### Problem: Dr DockFlare-Container startet nid oder hängt i nere Neustart-Schlaufe

**Lösung:**
1.  **Logs aa luege:** Zerscht luegsch immer d Logs vom DockFlare-Container aa:
    ```bash
    docker logs dockflare
    ```
2.  **Nach Fehlermäldige sueche:** Hüüfigi Ursach si:
    *   e fehlerhafti `docker-compose.yml`
    *   Problem mit em Docker-Daemon
    *   Problem mit em `docker-socket-proxy` oder dr `DOCKER_HOST`-Istellig

---

### Problem: DNS-Iiträg wärde i Cloudflare nid aagleit

**Lösung:**
1.  **DockFlare-Logs prüefe:** Suech nach Cloudflare-API-Fähler.
2.  **API-Token-Recht prüefe:** Meischtens fehlt öppis bi de Berechtige. Du bruuchsch mindestens:
    *   `Zone:DNS:Edit`
    *   `Zone:Zone:Read`
3.  **Zone-Konfiguration kontrolliere:**
    *   stimmt d **Zone ID**
    *   isch `dockflare.zonename` korrekt gschribe

---

### Problem: E Access Policy wird nid uf e Dienst aagwändet

**Lösung:**
1.  **API-Token-Recht prüefe:** Es bruucht `Account:Access: Apps and Policies:Edit`.
2.  **UI-Overrides prüefe:** I dr UI überstyre manuelli Overrides d Container-Labels.
3.  **Group ID verglyche:** `dockflare.access.group` muess exakt zur Group ID i dr UI passe.
4.  **Cloudflare Dashboard aa luege:** Im Zero-Trust-Dashboard gsehsch oft direkter, was bi dr App oder Policy grad gilt.

---

### Problem: Du bechunsch `ERR_TOO_MANY_REDIRECTS`

**Lösung:**
Das isch fasch immer e Fähler i de SSL/TLS-Istellige zwüsche dim Ursprung u Cloudflare.

1.  **SSL/TLS-Modus i Cloudflare prüefe:** Dä sött uf **Full (Strict)** stah.
2.  **Doppleti Redirects vermeide:** `Flexible` sorgt oft für Schlaufe, wänn dis Backend o no uf HTTPS umeleit.
3.  **`https` i dr Service-URL bruuche:** Wänn dis Backend HTTPS cha, nimm `https://` im `dockflare.service`-Label.

---

### Problem: E Dienst hinger Traefik oder Proxmox funktioniert nume mit "Match SNI to Host"

**Lösung:**
1.  Bearbeit d manuelli Regel i DockFlare u aktivier **Match SNI to Host**.
2.  Späicher d Regel.
3.  Wänn du zuesätzlechi Cloudflare-Fäuder bruuuchsch, aktivier under **Settings -> General Settings** d Option **Preserve Unmanaged Cloudflare Ingress Fields**.

---

### Problem: Dr verwaltete `cloudflared-agent` startet nid u meldet "stale network"

**Lösung:**
Das passiert meischtens, wänn es Docker-Subnetz us em Compose-Setup glöscht u neu erstellt worde isch. DockFlare het für das automatische Mechanisme.

1.  **DockFlare neu starte:** `docker compose restart dockflare` längt oft scho.
2.  **Was nachhär passiert:** Biim Start prüeft DockFlare sini Agente, räumt verwaisti Instanze uf u erstellt falls nötig Ersatz. Dä Fix isch ab `v1.9.5` drin.
