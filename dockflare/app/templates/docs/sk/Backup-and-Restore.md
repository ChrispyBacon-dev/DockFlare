# Záloha a obnovenie

DockFlare 3.0 zavádza kompletný zálohovací archív, takže môžeš presunúť hlavný server na nový hardvér, zotaviť sa z poruchy alebo pripraviť aktualizácie bez toho, aby si sa dotkol surového dátového adresára.

## Čo sa uloží
- `dockflare.key` – Fernet kľúč, ktorý odomyká každý zašifrovaný súbor.
- `dockflare_config.dat` – zašifrované Cloudflare prihlasovacie údaje, UI účty a runtime nastavenia.
- `agent_keys.dat` – zašifrované API kľúče agentov a audit metadáta.
- `state.json` – čitateľná JSON kópia pravidiel, agentov a prístupových skupín.
- `manifest.json` – kontrolné súčty a informácie o verzii archívu (generuje sa automaticky).

Všetky tieto súbory sú zabalené do jedného `dockflare_backup_YYYYMMDD_HHMMSS.zip`. ZIP a rozbalené súbory drž pokope; bez `dockflare.key` sú zašifrované artefakty nepoužiteľné.

## Vytvorenie zálohy
1. V hlavnom rozhraní otvor **Nastavenia → Záloha a obnovenie**.
2. Klikni na **Stiahnuť zálohu (.zip)**.
3. Archív ulož na bezpečné miesto. Zaobchádzaj s ním ako s prihlasovacími údajmi — obsahuje všetko potrebné na ovládanie tvojho Cloudflare účtu cez DockFlare.

Zálohu možno vytvoriť aj počas behu hlavného servera. Každý archív obsahuje manifest s SHA-256 hašmi, takže poškodené sťahovania sa dajú ľahko odhaliť.

## Obnovenie na existujúcom hlavnom serveri
1. Prejdi na **Nastavenia → Záloha a obnovenie**.
2. Nahraj `.zip` cez **Obnoviť zo zálohy**.
3. Potvrď upozornenie: obnovenie prepíše konfiguráciu, kľúče agentov a pravidlá.

DockFlare obnoví zašifrované súbory, znova načíta `state.json` a v prípade potreby zapíše príznak reštartu. Kontajner sa o pár sekúnd ukončí, aby ho Docker mohol spustiť s novou konfiguráciou. Rozhranie sa znova otvorí s obnovenými prihlasovacími údajmi.

Staršie súbory `state.json` sa stále akceptujú pri čiastočnom obnovení. Nahranie samotného JSON súboru nahradí len pravidlá a preskočí zašifrovanú konfiguráciu.

## Obnovenie počas sprievodcu nastavením
Čerstvé inštalácie majú teraz pred krokom 1 predletového sprievodcu odkaz **Obnoviť zo zálohy**.

1. Nahraj zálohovací ZIP.
2. DockFlare zapíše zašifrované artefakty a stav na disk.
3. Kontajner sa automaticky reštartuje; keď nabehne, prihlás sa obnoveným administrátorským účtom.

Tento postup je najrýchlejší spôsob, ako naklonovať produkčný hlavný server alebo sa zotaviť po vymazaní dátového volume. Sprievodcu netreba spúšťať znova ani opätovne zadávať Cloudflare prihlasovacie údaje.

## Po obnovení
- Prejdi na **Nastavenia → Záloha a obnovenie** a over čas najnovšieho manifestu.
- Skontroluj **Agenti → Prehľad**, či sa zaregistrovaní agenti znova pripoja. Ak si ich kľúče rotoval, vydaj ich nanovo.
- Ak si obnovoval do iného prostredia, spusti synchronizáciu (`Akcie → Synchronizovať teraz`).

Rob si pravidelné offline zálohy a spár ich s verziovaním svojho compose stacku, aby si vedel rýchlo znovu postaviť celé nasadenie.
