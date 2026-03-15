# Leistungsoptimierung (Performance Tuning)

Für die überwältigende Mehrheit der Benutzer bieten die Standardeinstellungen von DockFlare eine exzellente Balance aus Leistung und Ressourcennutzung. In sehr großen oder hochdynamischen Umgebungen können Sie jedoch davon profitieren, einige der erweiterten leistungsspezifischen Parameter abzustimmen.

Diese Einstellungen werden als Umgebungsvariablen (Environment Variables) in Ihrer `docker-compose.yml`-Datei konfiguriert.

---

## `CLEANUP_INTERVAL_SECONDS`

Diese Variable steuert, wie oft DockFlares Hintergrundaufgabe (Background Task) ausgeführt wird, um abgelaufene Ressourcen asynchron zu bereinigen (d. h. Regeln von gestoppten Containern, deren Schonfrist (`grace period`) verstrichen ist).

*   **Standard:** `60` Sekunden
*   **Beschreibung:** Ein kürzeres Intervall bedeutet, dass veraltete Ressourcen schneller aus Ihrer Cloudflare-Konfiguration entfernt werden. Ein längeres Intervall reduziert die Häufigkeit der Hintergrundprüfungen, was den Ressourcenverbrauch leicht senken kann.
*   **Wann Sie es anpassen sollten:** Wenn Sie über eine sehr dynamische Umgebung mit vielen kurzlebigen Containern verfügen und deren Ressourcen fast augenblicklich beseitigt haben möchten, könnten Sie diesen Wert verringern (z. B. auf `30`). Für den Regelbetrieb ist der Standard absolut ausreichend.

**Beispiel:**
```yaml
environment:
  - CLEANUP_INTERVAL_SECONDS=30
```

---

## `MAX_CONCURRENT_DNS_OPS`

Diese Variable legt die maximale Anzahl gleichzeitiger DNS-Operationen (Erstellen, Löschen) fest, die DockFlare parallel ausführt.

*   **Standard:** `3`
*   **Beschreibung:** Dies ist eine direkte Leistungsstellschraube für Umgebungen mit einer großen Anzahl von Diensten. Beim Hochfahren von DockFlare oder beim gleichzeitigen Starten vieler Container begrenzt diese Einstellung, wie viele parallele DNS-Änderungsanfragen an die Cloudflare-API gestellt werden.
*   **Wann Sie es anpassen sollten:** Wenn Sie Hunderte von Diensten verwalten und feststellen, dass der initiale Startvorgang oder ein Massen-Deployment zur Erstellung aller DNS-Einträge zu langsam voranschreitet, können Sie versuchen, diesen Wert zu erhöhen (z. B. auf `5` oder `10`). Seien Sie sich bewusst, dass ein zu hoher Wert zu einem Rate Limiting (Drosselung) durch das Cloudflare-API führen könnte.

**Beispiel:**
```yaml
environment:
  - MAX_CONCURRENT_DNS_OPS=5
```

---

## `RECONCILIATION_BATCH_SIZE`

Dies steuert die Stapelgröße (Batch Size) für verschiedene Abgleichsaufgaben (Reconciliation Tasks) im Hintergrund.

*   **Standard:** `3`
*   **Beschreibung:** Einige Hintergrundaufgaben in DockFlare verarbeiten Elemente in Stapeln, um eine Überlastung des Systems oder der Cloudflare-API zu vermeiden. Diese Einstellung reguliert die Dimension dieser Bündel.
*   **Wann Sie es anpassen sollten:** Dies ist eine tiefgreifende Experteneinstellung. Für die meisten Benutzer sollte der Standardwert nicht angetastet werden. Wenn Sie über eine extrem hohe Regelanzahl verfügen (viele Hunderte oder Tausende), können Sie mit geringfügig größeren Dimensionen experimentieren, worauf allerdings selten Verlass sein muss.

**Beispiel:**
```yaml
environment:
  - RECONCILIATION_BATCH_SIZE=5
```

---

## `SCAN_ALL_NETWORKS`

Diese Variable ändert die Art und Weise, wie DockFlare die IP-Adressen der Container entdeckt.

*   **Standard:** `false`
*   **Beschreibung:** Standardmäßig erwartet DockFlare, dass sich der Zielcontainer im selben Docker-Netzwerk wie DockFlare selbst befindet. Wenn `SCAN_ALL_NETWORKS` auf `true` gesetzt ist, wird DockFlare zusätzlich alle Netzwerke überprüfen, an die ein Container angebunden ist, um ein gemeinsames Netzwerk und die Ziel-IP zu ermitteln.
*   **Wann Sie es anpassen sollten:** Dies sollte ausschließlich dann aktiviert werden, wenn Sie ein vielschichtiges Docker-Netzwerk-Setup implementiert haben, in dem Ihre Applikationscontainer sich fernab des nativen Netzwerkes des DockFlare-Containers befinden. Bedenken Sie, dass die Aktivierung in Umgebungen mit einer sehr großen Anzahl von Docker-Netzwerken Leistungseinbußen mit sich bringen kann, da es mehr Iterationen durch DockFlare voraussetzt.

**Beispiel:**
```yaml
environment:
  - SCAN_ALL_NETWORKS=true
```
