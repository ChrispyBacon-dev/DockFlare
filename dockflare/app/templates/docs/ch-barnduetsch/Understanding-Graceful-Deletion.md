# Graceful Deletion verstah

Wänn du e vo DockFlare verwaltete Container stoppisch, merkisch vilicht, dass dr öffentlechi Hostname nid grad sofort verschwinde tuet. Das chunnt vom Feature **Graceful Deletion**.

## Was isch Graceful Deletion?

Statt d Ingress-Regel u dr DNS-Iitrag grad im Momänt vom Stoppe z lösche, markiert DockFlare d Regel als **`pending deletion`** u startet e Timer.

Erst wänn die **grace period** ablouft, wärde d Cloudflare-Ressource würklech glöscht.

## Warum das sinnvoll isch

Das verhindert Unterbrüch bi tüüpine Situatione:

* **Container-Updates:** Bi `docker compose up -d` wird dr alti Container oft churz stoppt, bevor dr neu startet. Dank grace period blybt d Regle chli no parat.
* **Temporäri Neustarts:** Wänn du churz öppis aapassisch u dr Container grad wieder startisch, mues nid aues neu aagleit wärde.

## D Variable `GRACE_PERIOD_SECONDS`

D Längi vo dr Schonfrist steuersch mit dr Umgebigsvariable `GRACE_PERIOD_SECONDS` i dr `docker-compose.yml`.

* Standard isch `600` Sekunde, also 10 Minute.
* E churzere Wert räumt schnäuer uf, e längere git meh Zyt für Neustarts.

**Beispiel:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      - GRACE_PERIOD_SECONDS=3600 # Set a 1-hour grace period
```

## Wie s i dr Praxis lauft

1. **Container stoppt:** Du machsch `docker stop my-app`.
2. **Regel wartet:** DockFlare setzt dr Status i dr Web UI uf **`pending_deletion`**.
3. **Nachhär git s zwöi Möglichkeite:**
   * **Ablouf vo dr grace period:** Dr Container blybt use, also löscht DockFlare d Ingress-Regel u dr CNAME.
   * **Container chunnt zrügg:** Dr Container startet vor em Ablauf wieder, DockFlare bricht s Lösche ab u setzt dr Status wieder uf **`active`**.
