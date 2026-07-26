# Trvalé uloženie stavu

DockFlare je stavová aplikácia. Potrebuje si udržiavať prehľad o službách, ktoré spravuje, o UI prepisoch a ďalších detailoch konfigurácie. Tento stav sa ukladá na disk, aby sa tvoja konfigurácia nestratila pri reštarte alebo znovuvytvorení DockFlare kontajnera.

## Ako sa stav ukladá

DockFlare ukladá svoj stav do troch kľúčových súborov v adresári `/app/data` vnútri kontajnera:

1.  `dockflare_config.dat`: Najdôležitejší súbor. Obsahuje všetky tvoje základné nastavenia a citlivé informácie v **zašifrovanej** podobe. Patrí sem:
    *   Tvoj Cloudflare API token a Account ID.
    *   Haš hesla tvojho DockFlare UI.
    *   Základné nastavenia z UI, ako názov tunela a Zone ID.

2.  `agent_keys.dat`: Zašifrované úložisko so všetkými API kľúčmi agentov a ich metadátami (vlastník, stav, časové značky). Uchovanie tohto súboru v bezpečí zabraňuje opätovnému použitiu zastaraných kľúčov.

3.  `state.json`: Tento súbor ukladá dynamický stav tvojich spravovaných služieb v čitateľnom JSON formáte. Patrí sem:
    *   Zoznam všetkých ingress pravidiel, ktoré DockFlare spravuje, či už pochádzajú z Docker labelov, alebo boli vytvorené ručne v UI.
    *   Všetky UI prepisy uplatnené na prístupové politiky.
    *   Všetky prístupové skupiny, ktoré si vytvoril.
    *   Stav „čaká na odstránenie“ pri službách, ktoré boli zastavené, ale sú stále v ochrannej lehote.

## Dôležitosť trvalého volume

Keďže celá tvoja konfigurácia je uložená v adresári `/app/data`, je **úplne kľúčové**, aby si tento adresár namapoval na trvalý volume na hostiteľskom stroji.

Ak trvalý volume nepoužiješ, **všetky tvoje nastavenia, UI heslo a konfigurácie pravidiel sa stratia** vždy, keď sa DockFlare kontajner odstráni a znovu vytvorí (napr. pri aktualizácii image).

### Odporúčaná konfigurácia Docker Compose

Odporúčaná konfigurácia `docker-compose.yml` to za teba rieši automaticky tým, že definuje pomenovaný volume a pripojí ho na `/app/data`:

```yaml
services:
  dockflare:
    # ... ďalšie nastavenia
    volumes:
      # Tento riadok zabezpečí, že tvoje dáta sú trvalé
      - ./dockflare_data:/app/data

volumes:
  # Toto definuje pomenovaný volume na tvojom hostiteľovi
  dockflare_data:
```

S touto konfiguráciou sa tvoje súbory `dockflare_config.dat`, `agent_keys.dat` a `state.json` uložia do adresára `dockflare_data` na tvojom hostiteľovi a bezpečne zachovajú tvoje nastavenie naprieč aktualizáciami kontajnera.

## Záloha a obnovenie

DockFlare teraz zbalí všetky kritické dáta do jedného zašifrovaného zálohovacieho archívu. Redis cache sa vynecháva, keďže ju možno bezpečne znovu postaviť na privátnej sieti `dockflare-internal`. Panel **Nastavenia → Záloha a obnovenie** ti umožní stiahnuť `.zip`, ktorý obsahuje:

* `dockflare_config.dat`
* `dockflare.key`
* `agent_keys.dat`
* `state.json` (ak existuje)
* Manifest s kontrolnými súčtami na overenie integrity

Obnovenie archívu znovu vytvorí tieto súbory a načíta ich do bežiacej inštancie. Nahranie staršieho `state.json` sa stále akceptuje, no obnoví len metadáta pravidiel — prihlasovacie údaje potom budeš musieť zadať ručne.
DockFlare po obnovení celého archívu automaticky reštartuje kontajner, aby sa zašifrovaná konfigurácia načítala okamžite.
