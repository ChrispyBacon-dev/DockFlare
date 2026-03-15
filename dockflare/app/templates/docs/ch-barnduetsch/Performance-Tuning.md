# Leistungsoptimierung (Performance Tuning)

Für d'meischte Lüt si d'Standardiistellige vo DockFlare e super Mix us Leistung u Ressourcäverbrauch. I sehr grosse oder sehr dynamische Umgebige chasch aber profitiere, wänn du ein paar vo de erweiterete Performance-Parameter fein-tunisch.

Diese Istellige wärde als Umgebungsvariablen (Environment Variables) in dinere `docker-compose.yml`-Datei konfiguriert.

---

## `CLEANUP_INTERVAL_SECONDS`

Diese Variable steuert, wie oft DockFlares Hintergrundaufgabe (Background Task) ausgeführt wird, um abgelaufene Ressourcen asynchron zu bereinigen (d. h. Regeln von gestoppten Containern, deren Schonfrist (`grace period`) verstrichen isch).

*   **Standard:** `60` Sekunden
*   **Beschreibung:** Ein kürzeres Intervall bedeutet, dass veraltete Ressourcen schneller aus dinere Cloudflare-Konfiguration entfernt wärde. Ein längeres Intervall reduziert die Häufigkeit der Hintergrundprüfungen, was den Ressourcenverbrauch leicht senken cha.
*   **Wann du es aapasse söttsch:** Wänn du e sehr dynamischi Umgebig mit vil churzläbige Containern hesch u dere Ressource fasch grad wäg haa wotsch, chönntsch dä Wert verringere (z.B. uf `30`). Für dr Normalbetrieb isch dr Standard absolut ausreichend.

**Beispiel:**
```yaml
environment:
  - CLEANUP_INTERVAL_SECONDS=30
```

---

## `MAX_CONCURRENT_DNS_OPS`

Diese Variable legt die maximale Anzahl gleichzeitiger DNS-Operationen (Erstellen, Löschen) fest, die DockFlare parallel ausführt.

*   **Standard:** `3`
*   **Beschreibung:** Das isch eine direkte Leistungsstellschraube für Umgebungen mit einer grossen Anzahl von Diensten. Beim Hochfahren von DockFlare oder beim gleichzeitigen Starten vieler Container begrenzt diese Istellige, wie viele parallele DNS-Änderungsanfragen an die Cloudflare-API gestellt wärde.
*   **Wann du es anpassen söttsch:** Wänn du Hundereti vo Dienste verwaltsch u merksch, dass dr initial Start oder es Massen-Deployment zum Erstelle vo allne DNS-Iiträg z'langsam isch, chasch probiere dä Wert z'erhöhe (z.B. uf `5` oder `10`). Ha aber im Chopf: z'höch cha i es Rate Limiting (Drosselig) vo dr Cloudflare-API laufe.

**Beispiel:**
```yaml
environment:
  - MAX_CONCURRENT_DNS_OPS=5
```

---

## `RECONCILIATION_BATCH_SIZE`

Das steuert die Stapelgrösse (Batch Size) für verschiedene Abgleichsaufgaben (Reconciliation Tasks) im Hintergrund.

*   **Standard:** `3`
*   **Beschreibung:** Einige Hintergrundaufgaben in DockFlare verarbeiten Elemente in Stapeln, um eine Überlastung des Systems oder der Cloudflare-API zu vermeiden. Diese Istellige reguliert die Dimension dieser Bündel.
*   **Wann du es anpassen sollten:** Das isch eine tiefgreifende Experteneinstellung. Für die meisten Benutzer sollte der Standardwert nid angetastet wärde. Wänn du über eine extrem hohe Regelanzahl verfügen (viele Hunderte oder Tausende), chasch mit geringfügig grösseren Dimensionen experimentieren, worauf allerdings selten Verlass sein mues.

**Beispiel:**
```yaml
environment:
  - RECONCILIATION_BATCH_SIZE=5
```

---

## `SCAN_ALL_NETWORKS`

Diese Variable ändert die Art u Weise, wie DockFlare die IP-Adressen der Container entdeckt.

*   **Standard:** `false`
*   **Beschreibung:** Standardmässig erwartet DockFlare, dass sich der Zielcontainer im selben Docker-Netzwerk wie DockFlare selbst befindet. Wenn `SCAN_ALL_NETWORKS` auf `true` gesetzt isch, wird DockFlare zusätzlich alle Netzwerke überprüfen, an die ein Container angebunden isch, um ein gemeinsames Netzwerk u die Ziel-IP zu ermitteln.
*   **Wann du es anpassen söttsch:** Das söttsch nume aktiviere, wänn du es komplexes Docker-Netzwerk-Setup hesch, wo dini App-Container nid im gliche Netzwerk wie DockFlare hocke. Ha im Chopf, dass das i Umgebige mit sehr vil Docker-Netzwerke langsamer werde cha, will DockFlare meh Iteratione mues mache.

**Beispiel:**
```yaml
environment:
  - SCAN_ALL_NETWORKS=true
```
