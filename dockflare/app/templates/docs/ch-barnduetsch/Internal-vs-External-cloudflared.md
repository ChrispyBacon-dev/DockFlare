# Interne vs. externe `cloudflared`

DockFlare cha i zwöi Modis loufe, zum `cloudflared` z verwalte. `cloudflared` isch dr Teil, wo d permanänti Verbindig zwüsche dim Server u em Cloudflare-Netz ufbout. Wänn du de Unterschied vo de beidne Modis verstande hesch, chasch ds passendere Setup für dini Umgebig wähle.

## Interne Modus (Standard)

Im interne Modus übernimmt DockFlare d ganz Verwaltig vom `cloudflared`-Agent sälber.

Wänn DockFlare startet, macht es automatisch:

1. Es eigets Docker-Container für `cloudflare/cloudflared` erstelle
2. Dr Tunnel mit de richtige Zugangsdaten konfigurieren
3. D Ingress-Regle aktuell halte
4. `cloudflared` neu starte, wänn sich d Konfiguration änderet

Das isch dr **Standard** u ou dr empfohlni Modus für d meischte Benutzer.

### Vorteil

* **Eifachs Setup** – DockFlare übernimmt praktisch aues für di
* **Zentrali Verwaltig** – Tunnel u `cloudflared` si us ere Hand verwaltet
* **Weniger Handarbeit** – Kei separati Prozesspflege nötig

### Nachteil

* **Weniger Feinkontroll** – Du bisch uf die Optione beschränkt, wo DockFlare bereitstellt

## Externe Modus

Im externe Modus bisch du sälber für Betrieb u Verwaltig vom `cloudflared`-Agent verantwortlich. DockFlare verbindet sech de mit eme bestehende Agent statt sälber eine z erstelle.

Das heisst:

* DockFlare erstellt **kei** eigete `cloudflared`-Container
* Du muesch sälber luege, dass `cloudflared` louft
* Du verwaltsch Version, Flags u Lifecycle vo `cloudflared` sälber

Das isch e **fortgschrittne Modus** für spezielli Aaforderige oder bestehendi Setups.

### Vorteil

* **Maximali Kontroll** – Du bestimmsch Version, Kommandozeile u Laufzyklus
* **Gueti Integrationsmöglichkeit** – Praktisch, wänn du scho es separates `cloudflared`-Setup hesch

### Nachteil

* **Meh Komplexität** – Du muesch sälber sicherstelle, dass dr Agent louft, richtig konfiguriert isch u am richtige Tunnel hängt

## Wänn bruuchsch welä Modus?

### Interne Modus isch besser, wänn ...

* du e möglichst eifachi Iirichtig wotsch
* DockFlare d Tunnel komplett söll verwalte
* du nid sälber no zusätzlich `cloudflared` pflege wotsch

### Externe Modus isch sinnvoll, wänn ...

* du scho es bestehends `cloudflared`-Setup hesch
* du spezielli Argument oder e eigeti Prozessverwaltig bruchsch
* du ganz genau kontrolliere wotsch, wie `cloudflared` deployt wird

## Externe Modus aktiviere

Zum externe Modus z aktiviere, muesch d entsprächende Umgebigsvariable für dr DockFlare-Container setze. D genoue Werte u d Bereitstellig si i dr Doku zum externe Modus beschribe:

* [Externe `cloudflared`-Modus](External-cloudflared-Mode.md)
* [Zwüsche Modis wächsle](Switching-Between-Modes.md)

## Kurzfazit

Für d meischte Setups isch dr **interne Modus** dr richtigi Wäg. Dr **externe Modus** lohnt sech vor allem de, wänn du bewusst meh Kontroll oder e vorhandeni `cloudflared`-Infrastruktur iibinde wotsch.
