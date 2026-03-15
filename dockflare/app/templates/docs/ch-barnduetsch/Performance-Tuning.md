# Performance-Tuning

Für d meischte Lüt sy d Standard-Iistellige vo DockFlare e guete Mix us Performance u Ressourceverbruch. I sehr grosse oder sehr dynamische Umgebige chasch aber profitiere, wänn du es paar erwytereti Parameter fein abstimmsch.

Die Iistellige wärde als Umgebigsvariablen i dr `docker-compose.yml` konfiguriert.

---

## `CLEANUP_INTERVAL_SECONDS`

Die Variable steuert, wie oft DockFlares Hintergrunds-Task abgloffeni Ressource asynchron ufruumt, also zum Bispil Regle vo gstoppte Container, wo ihri Schonfrist überschritte hei.

* **Standard:** `60` Sekunde
* **Was bewürkt's?** Es churzers Intervall entfernt veralteti Ressource schnäller us dr Cloudflare-Konfiguration. Es längers Intervall reduziert d Häufigkeit vo de Hintergrundprüefige u spart e chly Ressource.
* **Wänn söttsch du's aapasse?** Wänn du e sehr dynamischi Umgebig mit viu churzläbige Container hesch u Ressource mögli schnell wotsch ufruume, chasch dä Wert senke, zum Bispil uf `30`. Für d meischte Setups passt dr Standard sehr guet.

**Bispiel:**

```yaml
environment:
  - CLEANUP_INTERVAL_SECONDS=30
```

---

## `MAX_CONCURRENT_DNS_OPS`

Die Variable legt fest, wie viu DNS-Operatione DockFlare glychzytig darf uusfüehre.

* **Standard:** `3`
* **Was bewürkt's?** Das isch e diräkti Stellschruub für Umgebige mit viu Dienscht. Beim Hochfahre oder bi grosse Deployments begränzt die Iistellig, wie viu paralleli DNS-Änderige a d Cloudflare-API usegöh.
* **Wänn söttsch du's aapasse?** Wänn du Hunderte vo Dienscht verwaltsch u merksch, dass dr Start oder es Massen-Deployment z langsam isch, chasch probiere dä Wert z erhöhe, zum Bispil uf `5` oder `10`. Acht aber druf, dass z'hochi Wärte zu Rate Limits bi Cloudflare chöi füehre.

**Bispiel:**

```yaml
environment:
  - MAX_CONCURRENT_DNS_OPS=5
```

---

## `RECONCILIATION_BATCH_SIZE`

Die Variable steuert d Stapelgrössi für verschiedeni Hintergrund-Abglich.

* **Standard:** `3`
* **Was bewürkt's?** Gewüssi Hintergrundsprozäss verarbeite Element stapelwys, damit weder dr Host no d Cloudflare-API überlaschtet wärde. Die Iistellig bestimmt, wie gross die Päckli sy.
* **Wänn söttsch du's aapasse?** Das isch eher e Experte-Iistellig. Für d meischte Benutzer sött dr Standardwert nid aaglangt wärde. Wänn du extrem viu Regle hesch, chasch vorsichtig mit öppis grösseri Stapel experimentiere.

**Bispiel:**

```yaml
environment:
  - RECONCILIATION_BATCH_SIZE=5
```

---

## `SCAN_ALL_NETWORKS`

Die Variable änderet, wie DockFlare d IP-Adrässe vo Container findet.

* **Standard:** `false`
* **Was bewürkt's?** Standardmässig erwartet DockFlare, dass sich dr Zielcontainer im glyche Docker-Netzwerk befindet wie DockFlare sälber. Wänn `SCAN_ALL_NETWORKS=true` isch, prüeft DockFlare zusätzlich aui Netzwerch, wo dr Container dra aagschlosse isch, zum es gmeinsams Netz u d Ziel-IP z finde.
* **Wänn söttsch du's aapasse?** Nume wänn du es komplexs Docker-Netzwerk-Setup hesch, wo dini App-Container nid im glyche Netz wie DockFlare sy. Denk dra: bi sehr viu Netzwerche cha das dr Ablauf ou verlangsamen.

**Bispiel:**

```yaml
environment:
  - SCAN_ALL_NETWORKS=true
```
