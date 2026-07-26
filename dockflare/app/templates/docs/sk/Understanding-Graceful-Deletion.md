# Ako funguje riadené odstránenie (graceful deletion)

Keď zastavíš kontajner spravovaný cez DockFlare, možno si všimneš, že jeho príslušný verejný hostname nezmizne okamžite. Je to kvôli funkcii nazvanej **graceful deletion** (šetrné odstránenie).

## Čo je graceful deletion?

Namiesto okamžitého zmazania Cloudflare ingress pravidla a DNS záznamu vo chvíli, keď sa kontajner zastaví, DockFlare pravidlo označí ako **„čaká na odstránenie“** a spustí časovač.

Súvisiace Cloudflare zdroje (ingress pravidlo a DNS záznam) sa natrvalo odstránia až po vypršaní tohto časovača, známeho ako **ochranná lehota** (grace period).

## Prečo je to užitočné?

Táto funkcia má zabrániť prerušeniu služby v bežných prevádzkových situáciách:

*   **Aktualizácie kontajnerov:** Keď aktualizuješ image kontajnera (`docker compose up -d`), Docker zvyčajne zastaví starý kontajner a spustí nový. Bez ochrannej lehoty by tvoja služba bola na krátky čas nedostupná. Vďaka graceful deletion zostávajú DNS záznam a ingress pravidlo aktívne a DockFlare ich jednoducho znova priradí k novému kontajneru — bez výpadku.
*   **Dočasné reštarty:** Ak potrebuješ na chvíľu zastaviť kontajner kvôli zmene nastavenia a potom ho znova spustiť, ochranná lehota zabezpečí, že tvoja verejná konfigurácia zostane nedotknutá.

## Premenná `GRACE_PERIOD_SECONDS`

Dĺžku tejto ochrannej lehoty riadi premenná prostredia `GRACE_PERIOD_SECONDS`, ktorú nastavíš v súbore `docker-compose.yml`.

*   Predvolená hodnota je `600` sekúnd (10 minút).
*   Túto hodnotu si môžeš upraviť podľa potreby. Kratšia lehota zrýchli čistenie, dlhšia poskytne väčšie okno na reštarty kontajnerov.

**Príklad:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... ďalšie nastavenia
    environment:
      - GRACE_PERIOD_SECONDS=3600 # Nastaví 1-hodinovú ochrannú lehotu
```

## Ako to funguje v praxi

1.  **Kontajner zastavený:** Spustíš `docker stop my-app`.
2.  **Čaká na odstránenie:** DockFlare zaznamená udalosť zastavenia. V webovom rozhraní pravidlo pre `my-app.example.com` teraz zobrazí stav **„pending_deletion“** a čas, kedy je naplánované jeho odstránenie.
3.  **Dva scenáre:**
    *   **Scenár A: Ochranná lehota vyprší:** Ak kontajner zostane zastavený a ochranná lehota (napr. 10 minút) vyprší, spustí sa čistiaca úloha DockFlare na pozadí. Odstráni ingress pravidlo z tvojho Cloudflare tunela a odstráni CNAME DNS záznam.
    *   **Scenár B: Kontajner sa reštartuje:** Ak kontajner spustíš znova (`docker start my-app`) **pred** vypršaním ochrannej lehoty, DockFlare zaznamená udalosť spustenia. Zistí, že pravidlo čaká na odstránenie, odstránenie zruší a jeho stav vráti späť na **„aktívne“**. Tvoja služba beží ďalej bez prerušenia.
