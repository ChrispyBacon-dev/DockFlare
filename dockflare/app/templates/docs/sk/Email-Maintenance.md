# Údržba a riešenie problémov

E-mail DockFlare je navrhnutý tak, aby si vyžadoval minimum údržby, no pochopiť, ako riešiť zálohy a bežné problémy, je pre dlhodobú spoľahlivosť dôležité.

## Záloha a obnovenie

Všetky tvoje e-mailové dáta sú uložené v Docker volume `mail_data`. Zálohu vytvoríš takto:

1.  **Záloha celého volume:** Zálohuj celý priečinok volume na hostiteľskom stroji. Je to najbezpečnejšia možnosť, keďže zachytí surovú SQLite databázu aj všetky súbory príloh.
2.  **Záloha cez UI:** Na stránke **E-mail** nájdi kartu **Záloha a obnovenie** a klikni na **Stiahnuť zálohu**. Vygeneruje sa ZIP archív tvojich e-mailových dát. Poznámka: táto záloha obsahuje e-maily a prílohy v čitateľnej podobe — ulož ju na bezpečné miesto.

Obnovenie:
1.  Uisti sa, že volume `mail_data` je pripojený v tvojom `docker-compose.yml`.
2.  Na stránke **E-mail** v karte **Záloha a obnovenie** vyber svoj ZIP súbor a klikni na **Obnoviť zálohu**. Tým sa natrvalo prepíšu existujúce e-mailové dáta.

## Logy

Ladenie problémov s doručovaním si často vyžaduje pohľad do logov kontajnera `dockflare-mail-manager`.

```bash
docker logs -f dockflare-mail-manager
```

Stránka E-mail obsahuje aj kartu **Logy doručovania**. Kliknutím na **Preskúmať** otvoríš prehliadač logov, ktorý má dve karty:
*   **Odchádzajúci log:** História všetkých pokusov o odoslanie pošty.
*   **Log odmietnutí:** História všetkých zlyhaní doručenia (NDR) pre tebou odoslané e-maily.

## Odolnosť a samoopravovanie

### Bufferovanie v R2
Ak server prejde do offline stavu (napr. výpadok prúdu alebo internetu), Cloudflare inbound worker si všimne, že tvoj lokálny webhook je nedostupný. E-mail bezpečne uchová v **R2 temp_cache**.
*   Worker spúšťa **cron job** každých 5 minút.
*   Automaticky sa bude pokúšať doručiť všetky nabufferované e-maily, kým server nebude znova online.

### Súlad databázy a súborového systému
Mail Manager obsahuje štartovaciu rutinu, ktorá zabezpečí, že databáza a súborový systém sú zosynchronizované. Ak súbor prílohy existuje, ale nemá záznam v databáze („osirotený“), automaticky sa odstráni, aby sa ušetrilo miesto.

## Bežné problémy

### „Worker Error“ v logoch
Uisti sa, že tvoj API token má oprávnenia `Workers Scripts` a `Workers KV Storage`. Ak si nedávno aktualizoval DockFlare, možno budeš musieť na stránke E-mail kliknúť na **Znova nasadiť Workers**, aby sa zosynchronizovali nové premenné prostredia.

### Pošta mešká
Skontroluj logy **cron** v dashboarde Cloudflare workera. Ak je tvoj lokálny server pod veľkou záťažou alebo má sieťové problémy, worker nabufferuje poštu do R2 a doručí ju, keď server odpovie.
