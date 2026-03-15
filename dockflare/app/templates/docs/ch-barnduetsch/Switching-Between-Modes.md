# Zwüsche Modis wächsle

Du chasch DockFlare jederzeit zwüsche em **Interne** u em **Externe** `cloudflared`-Modus wächsle. Da findsch dr Ablauf, ohni dass du der unnötig Problem iifangsch.

E ausführleche Verglych vo beidne Modis findsch uf dr Syte [Interner vs. Externer `cloudflared`](Internal-vs-External-cloudflared.md).

---

## Wechsel vom Internen zum Externen Modus

Da Prozess heisst: Du richtsch zerscht dis eigets `cloudflared` ii u seisch nachhär DockFlare, dass es dä Tunnel söll bruuche.

**Schritt 1: Externs `cloudflared` iirichte**

Zerscht muesch dis eigets `cloudflared` starte. Das cha direkt uf em Host laufe oder i mene separate Docker-Container.

* lueg, dass es dr richtig Cloudflare-Tunnel bruucht
* schrib dr d **Tunnel ID** (UUID) uuf
* prüef im Cloudflare-Dashboard, dass dr Tunnel als `connected` aazeigt wird

**Schritt 2: DockFlare umstelle**

Nachhär passisch d Umgebigsvariable i dr `docker-compose.yml` aa:

In dinere `docker-compose.yml`:
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      - USE_EXTERNAL_CLOUDFLARED=true
      - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Schritt 3: Änderig übernäh**

Füehr `docker compose up -d` uus, zum DockFlare neu z erstelle.

Wänn dr aktualisierti Container wieder startet:
1. erkennt DockFlare, dass dr externi Modus aktiv isch
2. stoppt u entfernt es dr eiget verwaltete `cloudflared-agent`
3. schickt es sini Ingress-Konfiguration an dr Tunnel us `EXTERNAL_TUNNEL_ID`

Dini Dienscht wärde de über dis extern verwaltete `cloudflared` usgspiut.

---

## Wechsel vom Externen zum Internen Modus

Da Wächsu isch einfacher, wiu DockFlare nachhär wieder sälber `cloudflared` verwaltet.

**Schritt 1: Externi Variable use näh**

Nimm die Variable für dr externi Modus us dr `docker-compose.yml` use.

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # - USE_EXTERNAL_CLOUDFLARED=true
      # - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Schritt 2: Neu deploye**

Füehr wider `docker compose up -d` uus.

Wänn dr Container neu startet:
1. merkt DockFlare, dass dr externi Modus nüm aktiv isch
2. erstellt u startet es wieder en eigete interne `cloudflared-agent`
3. konfiguriert es dä mit em Tunnelname us dine DockFlare-Istellige

**Schritt 3: Externs `cloudflared` usschalte**

Sobald du sicher bisch, dass dr intern Agent sauber lauft u dr Traffic übernimmt, chasch dis externs `cloudflared` stoppe u use näh.
