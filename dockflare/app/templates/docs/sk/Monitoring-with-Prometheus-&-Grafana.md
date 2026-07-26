# Monitoring: Prometheus a Grafana

Agent `cloudflared`, ktorého DockFlare spravuje, dokáže vystaviť širokú škálu výkonnostných a stavových metrík vo formáte Prometheus. Zberom a vizualizáciou týchto metrík získaš cenný prehľad o prevádzke, latencii a chybovosti svojho tunela.

Táto príručka vysvetľuje, ako zapnúť metrics endpoint, a ponúka rýchle nastavenie monitorovacieho stacku pomocou Prometheus a Grafana.

## Krok 1: Zapni metrics endpoint v DockFlare

Prvým krokom je povedať DockFlare, aby na svojom spravovanom agentovi `cloudflared` zapol Prometheus metrics endpoint.

Urobíš to nastavením premennej prostredia `CLOUDFLARED_METRICS_PORT` pre svoj DockFlare kontajner.

**Príklad `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... ďalšie nastavenia
    environment:
      # Zapne metrics endpoint na porte 2000 vnútri kontajnera
      - CLOUDFLARED_METRICS_PORT=2000
```
Keď s touto premennou reštartuješ DockFlare, automaticky znovu vytvorí svojho spravovaného agenta `cloudflared` so zapnutým metrics serverom na zadanom porte.

**Poznámka:** Táto funkcia je dostupná len v predvolenom **internom režime**. Ak používaš [externý režim](External-cloudflared-Mode.md), za zapnutie metrics endpointu na svojom vlastnom agentovi `cloudflared` zodpovedáš ty.

## Krok 2: Nastav monitorovací stack

Ak zatiaľ nemáš monitorovací stack, rýchlo si ho postavíš pomocou Docker Compose. Repozitár DockFlare poskytuje príklad nastavenia v adresári `/examples`.

Kompletný návod na kopírovanie, ako nastaviť Prometheus a Grafana na monitorovanie DockFlare, nájdeš v súbore **[`grafana quick setup.md`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/grafana%20quick%20setup.md)** v repozitári.

Táto príručka ťa prevedie:
1.  Vytvorením potrebnej adresárovej štruktúry.
2.  Pridaním služieb Prometheus a Grafana do tvojho `docker-compose.yml`.
3.  Nakonfigurovaním Prometheus na zber metrík z agenta `cloudflared`.
4.  Automatickým pripravením Grafany s dátovým zdrojom Prometheus.

## Krok 3: Importuj hotový Grafana dashboard

Aby bola vizualizácia jednoduchá, DockFlare poskytuje hotový Grafana dashboard navrhnutý tak, aby dokonale spolupracoval s metrikami vystavenými agentom `cloudflared`.

1.  Dashboard je dostupný ako **[`dashboard.json`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/dashboard.json)** v adresári `/examples` repozitára.
2.  Stiahni tento súbor.
3.  Prihlás sa do svojej inštancie Grafany.
4.  Prejdi do sekcie „Dashboards“ a klikni na „Import“.
5.  Nahraj súbor `dashboard.json`.
6.  Vyber svoj dátový zdroj Prometheus a importuj dashboard.

Teraz budeš mať kompletný prehľad o výkone svojho Cloudflare tunela vrátane počtu požiadaviek, chybovosti, latencie pripojenia a ďalších.

![Grafana Dashboard Example](../static/images/grafana_dashboard_example.png)
