# Prepínanie medzi režimami

DockFlare môžeš kedykoľvek prepnúť medzi **interným** (predvoleným) a **externým** režimom `cloudflared`. Táto príručka vysvetľuje postup na hladký prechod.

Podrobné porovnanie oboch režimov nájdeš na stránke [Interný vs. externý `cloudflared`](Internal-vs-External-cloudflared.md).

---

## Prechod z interného na externý režim

Tento proces zahŕňa nastavenie vlastného agenta `cloudflared` a následné povedanie DockFlare, aby ho použil.

**Krok 1: Nastav svojho externého agenta `cloudflared`**

Najprv musíš nastaviť a spustiť vlastného agenta `cloudflared`. Môže to byť proces na hostiteľskom OS alebo ďalší Docker kontajner.

*   Uisti sa, že je nakonfigurovaný na použitie konkrétneho Cloudflare tunela.
*   Poznač si **Tunnel ID** (UUID).
*   Spusti agenta a potvrď, že beží správne a v tvojom Cloudflare dashboarde sa zobrazuje ako „connected“.

**Krok 2: Prekonfiguruj a reštartuj DockFlare**

Ďalej musíš aktualizovať premenné prostredia svojho DockFlare kontajnera, aby prešiel do externého režimu.

V tvojom `docker-compose.yml`:
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... ďalšie nastavenia
    environment:
      # Zapni externý režim
      - USE_EXTERNAL_CLOUDFLARED=true
      # Zadaj ID svojho bežiaceho tunela
      - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Krok 3: Nasaď zmenu**

Spusti `docker compose up -d`, aby sa DockFlare kontajner znovu vytvoril s novými premennými prostredia.

Keď aktualizovaný DockFlare kontajner naštartuje:
1.  Zistí, že `USE_EXTERNAL_CLOUDFLARED` je `true`.
2.  **Zastaví a odstráni** svoj vlastný spravovaný kontajner `cloudflared-agent`.
3.  Začne posielať všetky svoje konfigurácie ingress pravidiel tunelu zadanému cez `EXTERNAL_TUNNEL_ID`.

Tvoje služby teraz bude obsluhovať tvoj externe spravovaný agent `cloudflared`.

---

## Prechod z externého na interný režim

Tento proces je jednoduchší, keďže spočíva v tom, že necháš DockFlare prevziať kontrolu späť.

**Krok 1: Prekonfiguruj DockFlare**

Odstráň premenné prostredia externého režimu zo súboru `docker-compose.yml` DockFlare.

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... ďalšie nastavenia
    environment:
      # Odstráň nasledujúce dva riadky
      # - USE_EXTERNAL_CLOUDFLARED=true
      # - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Krok 2: Nasaď zmenu**

Spusti `docker compose up -d`, aby sa DockFlare kontajner znovu vytvoril.

Keď aktualizovaný DockFlare kontajner naštartuje:
1.  Zistí, že `USE_EXTERNAL_CLOUDFLARED` je `false`.
2.  Automaticky **vytvorí, nakonfiguruje a spustí** svoj vlastný interný kontajner `cloudflared-agent`.
3.  Nakonfiguruje tohto nového agenta na použitie názvu tunela definovaného v nastaveniach DockFlare.

**Krok 3: Vyraď svojho externého agenta**

Keď si potvrdil, že nový interný agent beží správne a obsluhuje prevádzku, môžeš svojho vlastného agenta `cloudflared` bezpečne zastaviť a odstrániť.
