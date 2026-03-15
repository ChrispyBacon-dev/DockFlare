# Debugging & Logs

Wänn öppis mit DockFlare nid stimmt, si d Logs dis wichtigschte Wärchzüg. Am meischte bringsch use, wänn du d Logs vom DockFlare-Container u vom verwaltete `cloudflared`-Agent aaluegsch.

## 1. Logs vom DockFlare-Container aluege

D wichtigste Informationsquelle si d Logs vom DockFlare-Container sälber. Dört gsehsch i Echtzyt, was DockFlare grad macht.

### Was du det drin gsehsch
* Start- u Stop-Ereignis vo Container
* Verarbeitung vo `dockflare.*`-Labels
* Cloudflare-API-Ufrüef
* Erfolgs- u Fehlermäldige
* Hintergrundjob wie Cleanup oder Abgliich

### So luegsch d Logs aa
Bruuch im Terminal die Docker-Befähl:
```bash
# View the full log history
docker logs dockflare

# Follow the logs in real-time
docker logs -f dockflare
```

## 2. Echtzyt-Logs i dr Web UI

Im DockFlare-Dashboard git s unde uf dr Hauptsyte e **Echtzyt-Log-Viewer**.

Dä Viewer zeigt dir die glyche Logs wie `docker logs -f dockflare`, aber direkt i dr UI. Das isch praktisch, wänn du schnell wotsch luege, was grad passiert, ohni zwüsche Browser u Terminal z wechsle.

## 3. Logs vom `cloudflared`-Agent aluege

Wänn s Problem eher bi dr Verbindig zwüsche dim Server u Cloudflare ligt, luegsch am beschte d Logs vom `cloudflared`-Agent aa.

### So luegsch d Agenten-Logs aa
Zerscht muesch dr Containername usefinde. Standardmässig heisst er `cloudflared-agent-<tunnel-name>`, wobe `<tunnel-name>` dr Tunnelname us dine DockFlare-Istellige isch.

Mit `docker ps` gsehsch dr exakti Name.

Sobald du de Name hesch, führ us:
```bash
# Replace with the actual container name
docker logs cloudflared-agent-dockflare-tunnel
```

Die Logs si bsunders nützlich für:
* Verbindigsproblem zum Cloudflare-Edge
* Authentifizierigsfehler mit em Tunnel-Token
* Protokoll- oder Routing-Problem bim wytergleitete Traffic

**Hinwys:** Das gilt nume im standardmässige **Interne Modus**. Im [Externe Modus](External-cloudflared-Mode.md) muesch du d Logs vo dim eigete `cloudflared`-Prozess aa luege.

## 4. O s Cloudflare-Dashboard prüefe

Vergiss am Schluss o s Cloudflare-Dashboard nid:
* **DNS:** Prüef, öb d CNAME-Iiträg korrekt aagleit worde si.
* **Zero Trust -> Tunnels:** Lueg dr Status vom Tunnel u vo de Ingress-Regle aa.
* **Zero Trust -> Applications:** Prüef d Access-Apps u dä "Last Seen"-Status.
