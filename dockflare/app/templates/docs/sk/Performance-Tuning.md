# Ladenie výkonu

Pre veľkú väčšinu používateľov ponúkajú predvolené nastavenia DockFlare dobrú rovnováhu medzi výkonom a využitím zdrojov. V naozaj veľkých alebo vysoko dynamických prostrediach však môžeš ťažiť z doladenia niektorých pokročilých parametrov súvisiacich s výkonom.

Tieto nastavenia sa konfigurujú cez premenné prostredia v súbore `docker-compose.yml`.

---

## `CLEANUP_INTERVAL_SECONDS`

Táto premenná riadi, ako často sa spúšťa úloha DockFlare na pozadí na čistenie expirovaných zdrojov (t. j. pravidiel zo zastavených kontajnerov, ktorým uplynula ochranná lehota).

*   **Predvolené:** `60` sekúnd
*   **Popis:** Kratší interval znamená, že zastarané zdroje sa z tvojej Cloudflare konfigurácie odstraňujú rýchlejšie. Dlhší interval znižuje frekvenciu kontrol na pozadí, čo môže mierne znížiť využitie zdrojov.
*   **Kedy ladiť:** Ak máš veľmi dynamické prostredie s mnohými krátko žijúcimi kontajnermi a chceš ich zdroje čistiť takmer okamžite, môžeš túto hodnotu znížiť (napr. na `30`). Pre väčšinu používateľov je predvolená hodnota v poriadku.

**Príklad:**
```yaml
environment:
  - CLEANUP_INTERVAL_SECONDS=30
```

---

## `MAX_CONCURRENT_DNS_OPS`

Táto premenná nastavuje maximálny počet súbežných DNS operácií (vytvorenie, odstránenie), ktoré DockFlare naraz vykoná.

*   **Predvolené:** `3`
*   **Popis:** Je to priama ladiaca páka výkonu pre prostredia s veľkým počtom služieb. Keď DockFlare naštartuje alebo keď sa naraz spustí veľa kontajnerov, toto nastavenie obmedzí, koľko paralelných požiadaviek sa pošle na Cloudflare API pre DNS zmeny.
*   **Kedy ladiť:** Ak spravuješ stovky služieb a všimneš si, že úvodný štart alebo hromadné nasadenie vytvára všetky DNS záznamy pomaly, môžeš skúsiť túto hodnotu zvýšiť (napr. na `5` alebo `10`). Maj na pamäti, že príliš vysoká hodnota môže viesť k obmedzeniu rýchlosti (rate limiting) na Cloudflare API.

**Príklad:**
```yaml
environment:
  - MAX_CONCURRENT_DNS_OPS=5
```

---

## `RECONCILIATION_BATCH_SIZE`

Toto riadi veľkosť dávky pre rôzne synchronizačné úlohy na pozadí.

*   **Predvolené:** `3`
*   **Popis:** Niektoré úlohy DockFlare na pozadí spracúvajú položky v dávkach, aby nepreťažili systém alebo Cloudflare API. Toto nastavenie riadi veľkosť týchto dávok.
*   **Kedy ladiť:** Ide o veľmi pokročilé nastavenie. Pre väčšinu používateľov by sa predvolená hodnota nemala meniť. Ak máš extrémne veľký počet pravidiel (mnoho stoviek alebo tisícov), môžeš experimentovať s mierne väčšou dávkou, no vo všeobecnosti to nie je potrebné.

**Príklad:**
```yaml
environment:
  - RECONCILIATION_BATCH_SIZE=5
```

---

## `SCAN_ALL_NETWORKS`

Táto premenná mení spôsob, akým DockFlare zisťuje IP adresu kontajnerov.

*   **Predvolené:** `false`
*   **Popis:** Predvolene DockFlare očakáva, že cieľový kontajner je na tej istej Docker sieti ako samotný DockFlare. Keď je `SCAN_ALL_NETWORKS` nastavené na `true`, DockFlare preskúma všetky siete, ku ktorým je kontajner pripojený, aby našiel zdieľanú sieť.
*   **Kedy ladiť:** Toto by sa malo zapnúť len vtedy, ak máš zložité Docker sieťové nastavenie, kde tvoje aplikačné kontajnery nie sú na tej istej sieti ako DockFlare. Maj na pamäti, že zapnutie tejto možnosti môže mať v prostrediach s veľmi veľkým počtom Docker sietí dopad na výkon, keďže si to od DockFlare vyžaduje viac inšpekčnej práce.

**Príklad:**
```yaml
environment:
  - SCAN_ALL_NETWORKS=true
```
