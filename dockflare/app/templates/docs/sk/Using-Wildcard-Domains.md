# Použitie domén s wildcardom

DockFlare podporuje použitie domén s wildcardom (napr. `*.example.com`) na smerovanie prevádzky viacerých subdomén do jednej služby. Hodí sa to najmä pre aplikácie spracúvajúce dynamické subdomény, ako sú multi-tenant služby alebo osobné dashboardy typu Heimdall.

## Ako to funguje

Keď použiješ wildcard hostname, Cloudflare Tunnel bude smerovať všetku prevádzku pre ktorúkoľvek subdoménu bez konkrétnejšieho DNS záznamu do služby, ktorú zadáš.

Napríklad ak nastavíš `*.apps.example.com`, prevádzka pre `service1.apps.example.com`, `service2.apps.example.com` a tak ďalej sa bude smerovať do toho istého cieľového kontajnera.

## Dôležité upozornenia

Na rozdiel od bežných hostname DockFlare **nedokáže automaticky vytvárať DNS záznamy pre domén s wildcardomy**. Wildcard DNS záznam musíš vytvoriť ručne v Cloudflare dashboarde.

DockFlare bude naďalej spravovať **ingress pravidlo** v tvojom Cloudflare tuneli, no úvodné nastavenie DNS je manuálny krok.

## Postup krok za krokom

Takto správne nastavíš domén s wildcardomu s DockFlare, na príklade `*.plex.example.com`.

### Krok 1: Ručne vytvor wildcard DNS záznam

1.  Prihlás sa do svojho **Cloudflare dashboardu**.
2.  Prejdi do nastavení DNS pre svoju doménu.
3.  Klikni na **Add record** a vytvor CNAME záznam s týmito údajmi:
    *   **Type:** `CNAME`
    *   **Name:** `*.plex` (alebo len `*`, ak je tvoja hlavná doména `plex.example.com`)
    *   **Target:** Verejný hostname tvojho tunela. Nájdeš ho v Cloudflare Zero Trust dashboarde pod **Access -> Tunnels**. Bude vyzerať približne ako `your-tunnel-uuid.cfargotunnel.com`.
    *   **Proxy status:** Uisti sa, že je **Proxied** (oranžový obláčik).

    Tento manuálny DNS záznam povie Cloudflare, aby posielal všetku prevádzku pre `*.plex.example.com` do tvojho tunela.

### Krok 2: Nastav svoju službu s wildcard labelom

Teraz nastav svoju službu v súbore `docker-compose.yml` s wildcard hostname labelom.

```yaml
services:
  my-proxy-manager:
    image: nginxproxymanager/nginx-proxy-manager
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      # Tu použi wildcard hostname
      - "dockflare.hostname=*.plex.example.com"
      - "dockflare.service=http://my-proxy-manager:81"
```

### Krok 3: Nasaď a over

1.  Ulož súbor `docker-compose.yml` a spusti `docker compose up -d`.
2.  DockFlare zaznamená kontajner a vytvorí v tvojom Cloudflare tuneli ingress pravidlo pre hostname `*.plex.example.com`.
3.  Over si to v webovom rozhraní DockFlare aj v konfigurácii svojho tunela v Cloudflare dashboarde.

Teraz sa každá požiadavka na subdoménu ako `sonarr.plex.example.com` alebo `radarr.plex.example.com` bude smerovať cez tvoj Cloudflare Tunnel do kontajnera `my-proxy-manager`, ktorý potom prevádzku spracuje.
