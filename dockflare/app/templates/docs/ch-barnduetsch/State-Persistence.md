# Persistänte Status

DockFlare isch e zustandsbehafteti Aawändig. Verwalteti Dienscht, UI-Overrides u angeri Konfigurationsdate müesse irgendwone persistiert wärde, damit nach eme Neustart oder eme Container-Neubau nid aues verlore geit.

## Wie DockFlare dr Status speicheret

DockFlare speicheret sini wichtige Date i `/app/data` im Container:

1. `dockflare_config.dat`: Di wichtigschti Datei. Da drin si d zentrale Istellige u sensible Date **verschlüsslet** gspeicheret:
   * dis Cloudflare-API-Token u dini Account-ID
   * dr Passwort-Hash vo dr DockFlare-UI
   * Tunnel-Defaults, Zone-ID u angeri UI-Istellige

2. `agent_keys.dat`: Es verschlüsselts Register mit aune Agent-API-Schlüssle u Metadate wie Besitzer, Status u Zytstämple.

3. `state.json`: Dr dynamischi Laufzitstatus im JSON-Klartext. Da drin si zum Bispil:
   * verwalteti Ingress-Regle
   * UI-Overrides für Access Policies
   * aagleiti Access Groups
   * `pending deletion`-Status für temporär gstoppeti Dienscht

## Warum es es persistents Volume bruucht

Wiu dini ganz Konfiguration i `/app/data` ligt, isch es **absolut entscheidend**, dass das Verzeichnis uf es persistents Volume oder e persistente Bind-Mount geit.

Ohni persistänts Volume geit der bi jedem Neu-Erstelle vom Container praktisch aues verlore: Istellige, UI-Login, Regle u Access-Konfiguration.

### Empfohlni Docker-Compose-Konfiguration

E tüüpi Konfiguration luegt so uus:

```yaml
services:
  dockflare:
    # ... angeri Istellige
    volumes:
      - ./dockflare_data:/app/data

volumes:
  dockflare_data:
```

Mit so nere Konfiguration blybe `dockflare_config.dat`, `agent_keys.dat` u `state.json` bi Updates u Neustarts erhalte.

## Backup u Wiederherstellig

DockFlare bündlet aui kritische Date i nes einzelts Backup-Archiv. Redis-Caches si nid debi, wiu si bi Bedarf wieder neu ufbout wärde chöi. Under **Istellige -> Backup & Wiederherstellig** chasch e `.zip` abelade mit:

* `dockflare_config.dat`
* `dockflare.key`
* `agent_keys.dat`
* `state.json` (falls vorhanden)
* em Manifest mit Prüefsummene

Bi dr Wiederherstellig wärde die Date zrügggschribe u i d laufendi Instanz glade. E alti, einzelni `state.json` cha no importiert wärde, stellt aber nume Regel-Metadate wieder här; Zugangsdaten muesch nachhär neu iihgäh.

Nach ere vollständige Wiederherstellig startet DockFlare dr Container automatisch neu, damit d verschlüssleti Konfiguration grad wieder aktiv isch.
