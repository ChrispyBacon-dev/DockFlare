# Ottimizzazione delle prestazioni

Per la stragrande maggioranza degli utenti, le impostazioni predefinite di DockFlare forniscono un buon equilibrio tra prestazioni e utilizzo delle risorse. Tuttavia, in ambienti molto grandi o altamente dinamici, potresti trarre vantaggio dall'ottimizzazione di alcuni parametri avanzati relativi alle prestazioni.

Queste impostazioni vengono configurate tramite variabili di ambiente nel tuo file `docker-compose.yml`.

---

## `CLEANUP_INTERVAL_SECONDS`

Questa variabile controlla la frequenza con cui viene eseguita l'attività in background di DockFlare per ripulire le risorse scadute (ad esempio, regole da contenitori arrestati il cui periodo di grazia è trascorso).

* **Predefinito:** `60` secondi
* **Descrizione:** Un intervallo più breve significa che le risorse obsolete verranno rimosse più rapidamente dalla configurazione di Cloudflare. Un intervallo più lungo riduce la frequenza dei controlli in background, il che può ridurre leggermente l'utilizzo delle risorse.
* **Quando ottimizzare:** se hai un ambiente molto dinamico con molti contenitori di breve durata e desideri che le relative risorse vengano ripulite quasi immediatamente, potresti abbassare questo valore (ad esempio, a `30`). Per la maggior parte degli utenti, l'impostazione predefinita va bene.

**Esempio:**
```yaml
environment:
  - CLEANUP_INTERVAL_SECONDS=30
```

---

## `MAX_CONCURRENT_DNS_OPS`

Questa variabile imposta il numero massimo di operazioni DNS simultanee (creazione, eliminazione) che DockFlare eseguirà contemporaneamente.

* **Predefinito:** `3`
* **Descrizione:** Questa è una manopola di sintonizzazione diretta delle prestazioni per ambienti con un gran numero di servizi. Quando DockFlare si avvia o quando vengono avviati più contenitori contemporaneamente, questa impostazione limita il numero di richieste parallele effettuate all'API Cloudflare per le modifiche DNS.
* **Quando ottimizzare:** Se gestisci centinaia di servizi e noti che l'avvio iniziale o una distribuzione di massa è lenta nel creare tutti i record DNS, puoi provare ad aumentare questo valore (ad esempio, su `5` o `10`). Tieni presente che impostare un valore troppo alto potrebbe portare a una limitazione della velocità dell'API Cloudflare.

**Esempio:**
```yaml
environment:
  - MAX_CONCURRENT_DNS_OPS=5
```

---

## `RECONCILIATION_BATCH_SIZE`

Controlla la dimensione del batch per varie attività di riconciliazione in background.

* **Predefinito:** `3`
* **Descrizione:** Alcune attività in background in DockFlare elaborano gli elementi in batch per evitare di sovraccaricare il sistema o l'API Cloudflare. Questa impostazione controlla la dimensione di tali batch.
* **Quando sintonizzare:** Questa è un'impostazione molto avanzata. Per la maggior parte degli utenti, il valore predefinito non deve essere modificato. Se disponi di un numero estremamente elevato di regole (molte centinaia o migliaia), potresti sperimentare con dimensioni batch leggermente più grandi, ma generalmente non è necessario.

**Esempio:**
```yaml
environment:
  - RECONCILIATION_BATCH_SIZE=5
```

---

## `SCAN_ALL_NETWORKS`

Questa variabile modifica il modo in cui DockFlare rileva l'indirizzo IP dei contenitori.

* **Predefinito:** `false`
* **Descrizione:** Per impostazione predefinita, DockFlare si aspetta che il contenitore di destinazione si trovi sulla stessa rete Docker di DockFlare stesso. Quando `SCAN_ALL_NETWORKS` è impostato su `true`, DockFlare ispezionerà tutte le reti a cui è collegato un contenitore per trovare una rete condivisa.
* **Quando ottimizzare:** Questa opzione dovrebbe essere abilitata solo se si dispone di una configurazione di rete Docker complessa in cui i contenitori delle applicazioni non si trovano sulla stessa rete di DockFlare. Tieni presente che abilitarlo può avere un impatto sulle prestazioni in ambienti con un numero molto elevato di reti Docker, poiché richiede più lavoro di ispezione da parte di DockFlare.

**Esempio:**
```yaml
environment:
  - SCAN_ALL_NETWORKS=true
```
