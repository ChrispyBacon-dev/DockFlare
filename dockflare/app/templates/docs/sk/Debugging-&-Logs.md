# Ladenie a logy

Pri riešení problémov s DockFlare sú tvojimi hlavnými nástrojmi logy generované DockFlare kontajnerom a jeho spravovaným agentom `cloudflared`.

## 1. Kontrola logov DockFlare kontajnera

Najdôležitejším zdrojom informácií je výstup logov zo samotného DockFlare kontajnera. Tieto logy poskytujú podrobný pohľad v reálnom čase na to, čo DockFlare robí.

### Čo v logoch nájdeš:
*   Detekciu udalostí spustenia/zastavenia Docker kontajnerov.
*   Spracovanie labelov `dockflare.*`.
*   Volania na Cloudflare API.
*   Správy o úspechu alebo podrobné chybové odpovede z Cloudflare API.
*   Stav úloh na pozadí, ako je čistenie zdrojov.

### Ako si logy zobraziť:
Na zobrazenie logov použi v termináli tento Docker príkaz:
```bash
# Zobraz celú históriu logov
docker logs dockflare

# Sleduj logy v reálnom čase
docker logs -f dockflare
```

## 2. Používanie logov v reálnom čase vo webovom rozhraní

Pre pohodlie obsahuje dashboard DockFlare **prehliadač logov v reálnom čase** v spodnej časti hlavnej stránky.

Tento prehliadač streamuje presne tie isté logy, aké by si videl cez `docker logs -f dockflare`, no ponúka jednoduchý spôsob, ako sledovať dianie práve teraz bez opustenia prehliadača. Hodí sa najmä na sledovanie akcií, ktoré DockFlare vykoná hneď po tom, ako spustíš alebo zastavíš kontajner.

## 3. Kontrola logov agenta `cloudflared`

Ak máš podozrenie, že problém je v spojení medzi tvojím serverom a sieťou Cloudflare, môžeš skontrolovať logy kontajnera agenta `cloudflared` priamo.

### Ako si zobraziť logy agenta:
Najprv musíš nájsť názov kontajnera agenta. Predvolene sa volá `cloudflared-agent-<nazov-tunela>`, kde `<nazov-tunela>` je názov tunela nakonfigurovaný v nastaveniach DockFlare.

Presný názov nájdeš cez `docker ps`.

Keď máš názov, spusti:
```bash
# Nahraď skutočným názvom kontajnera
docker logs cloudflared-agent-dockflare-tunnel
```

Tieto logy sú užitočné na diagnostiku:
*   Chýb pripojenia na Cloudflare edge.
*   Problémov s overením tokenu tunela.
*   Chýb na úrovni protokolu pre prevádzku, ktorá sa presmerúva.

**Poznámka:** Toto platí len ak používaš predvolený **interný režim**. Ak používaš [externý režim](External-cloudflared-Mode.md), musíš skontrolovať logy vlastného procesu agenta `cloudflared`.

## 4. Kontrola Cloudflare dashboardu

Napokon nezabudni použiť ako ladiaci nástroj aj Cloudflare dashboard.
*   **Stránka DNS:** Skontroluj, či sa CNAME záznamy vytvorili podľa očakávania.
*   **Zero Trust dashboard:** Prejdi na **Access -> Tunnels** a skontroluj stav svojho tunela a jeho ingress pravidiel.
*   **Zero Trust dashboard:** Prejdi na **Access -> Applications** a skontroluj konfiguráciu a stav svojich Zero Trust politík. Stav „Last Seen“ na politikách môže byť veľmi informatívny.
