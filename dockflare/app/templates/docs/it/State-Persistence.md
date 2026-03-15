# Persistenza dello stato

DockFlare è un'applicazione con stato. Deve tenere traccia dei servizi gestiti, delle sostituzioni applicate dall'interfaccia web e di altri dettagli di configurazione. Questo stato viene salvato sul disco per garantire che la configurazione non venga persa se il container DockFlare viene riavviato o ricreato.

## Come viene archiviato lo stato

DockFlare memorizza il suo stato in tre file chiave situati nella directory `/app/data` all'interno del contenitore:

1. `dockflare_config.dat`: questo è il file più critico. Contiene tutte le impostazioni principali e le informazioni sensibili in un formato **crittografato**. Ciò include:
    * Il tuo token API Cloudflare e l'ID account.
    * Hash della password dell'interfaccia web di DockFlare.
    * Impostazioni principali configurate tramite l'interfaccia web, come il nome del tunnel e gli ID di zona.

2. `agent_keys.dat`: un archivio crittografato contenente tutte le chiavi API dell'agente e i relativi metadati (proprietario, stato, timestamp). Mantenere questo file sicuro impedisce il riutilizzo delle chiavi obsolete.

3. `state.json`: questo file memorizza lo stato dinamico dei servizi gestiti in un semplice formato JSON. Ciò include:
    * L'elenco di tutte le regole ingress gestite da DockFlare, indipendentemente dal fatto che provengano da etichette Docker o siano state create manualmente nell'interfaccia web.
    * Qualsiasi sostituzione applicata dall'interfaccia web ai criteri di accesso.
    * Tutti i gruppi di accesso che hai creato.
    * Lo stato "in attesa di eliminazione" per i servizi che sono stati interrotti ma che sono ancora nel periodo di grazia.

## L'importanza di un volume persistente

Poiché tutta la tua configurazione è archiviata nella directory `/app/data`, è **assolutamente cruciale** mappare questa directory su un volume permanente sul tuo computer host.

Se non utilizzi un volume persistente, **tutte le impostazioni, la password dell'interfaccia web e le configurazioni delle regole andranno perse** ogni volta che il container DockFlare viene rimosso e ricreato, ad esempio durante un aggiornamento dell'immagine.

### Configurazione consigliata per la composizione di Docker

La configurazione `docker-compose.yml` consigliata gestisce questo automaticamente definendo un volume denominato e montandolo su `/app/data`:

```yaml
services:
  dockflare:
    # ... other settings
    volumes:
      # This line ensures your data is persisted
      - ./dockflare_data:/app/data

volumes:
  # This defines the named volume on your host
  dockflare_data:
```

Con questa configurazione, i tuoi file `dockflare_config.dat`, `agent_keys.dat` e `state.json` verranno archiviati in una directory denominata `dockflare_data` sul tuo host, preservando in modo sicuro la tua configurazione durante gli aggiornamenti del contenitore.

## Backup e ripristino

DockFlare ora raggruppa tutti i dati critici in un unico archivio di backup crittografato. Le cache Redis vengono omesse perché possono essere ricostruite in modo sicuro sulla rete privata `dockflare-internal`. Il pannello **Impostazioni → Backup e ripristino** ti consente di scaricare un `.zip` che contiene:

* `dockflare_config.dat`
* `dockflare.key`
* `agent_keys.dat`
* `state.json` (quando presente)
* Un manifest con checksum per la verifica dell'integrità

Il ripristino dell'archivio ricrea questi file e li ricarica nell'istanza in esecuzione. I caricamenti legacy di `state.json` sono ancora accettati, ma ripristinano solo i metadati delle regole: in seguito dovrai inserire nuovamente le credenziali manualmente.
DockFlare riavvia automaticamente il contenitore dopo un ripristino completo dell'archivio in modo che la configurazione crittografata venga caricata immediatamente.
