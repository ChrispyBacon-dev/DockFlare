# Backup e ripristino

DockFlare 3.0 introduce un archivio di backup completo, così puoi spostare un Master su nuovo hardware, ripristinarlo dopo un guasto o preparare un aggiornamento senza dover intervenire direttamente sulla directory dei dati grezzi.

## Cosa viene salvato
- `dockflare.key` – la chiave Fernet che permette di decifrare ogni file protetto.
- `dockflare_config.dat` – credenziali Cloudflare cifrate, account dell'interfaccia web e impostazioni di runtime.
- `agent_keys.dat` – chiavi API degli agenti cifrate e metadati di audit.
- `state.json` – una copia JSON in chiaro di regole, agenti e Access Groups.
- `manifest.json` – checksum e informazioni di versione dell'archivio, generati automaticamente.

Tutti questi file vengono raccolti in un unico `dockflare_backup_YYYYMMDD_HHMMSS.zip`. Conserva insieme il file ZIP e gli eventuali file estratti: senza `dockflare.key`, gli artefatti cifrati non possono essere utilizzati.

## Creazione di un backup
1. Apri **Impostazioni → Backup e ripristino** nell'interfaccia web.
2. Fai clic su **Scarica backup (.zip)**.
3. Conserva l'archivio in un luogo sicuro. Trattalo come una credenziale sensibile: contiene tutto il necessario per gestire il tuo account Cloudflare tramite DockFlare.

I backup possono essere creati mentre il Master è in esecuzione. Ogni archivio include un manifest con hash SHA-256, così da individuare facilmente eventuali download corrotti.

## Ripristino su un Master esistente
1. Vai su **Impostazioni → Backup e ripristino**.
2. Carica il file `.zip` tramite **Ripristina da backup**.
3. Conferma l'avviso: il ripristino sovrascrive la configurazione esistente, le chiavi degli agenti e le regole.

DockFlare riscrive i file cifrati, ricarica `state.json` e, se necessario, imposta un flag di riavvio. Dopo pochi secondi il container termina, così Docker può riavviarlo con la nuova configurazione. Al termine, l'interfaccia web tornerà disponibile con le credenziali ripristinate.

I file `state.json` legacy sono ancora supportati per ripristini parziali. Il caricamento di un semplice file JSON sostituisce solo le regole e lascia invariata la configurazione cifrata.

## Ripristino durante l'installazione guidata
Nelle nuove installazioni compare ora il link **Ripristina da backup** prima del passaggio 1 della procedura guidata iniziale.

1. Carica il ZIP di backup.
2. DockFlare scrive su disco gli artefatti cifrati e lo stato.
3. Il container si riavvia automaticamente; una volta tornato disponibile, accedi con l'account amministratore ripristinato.

Questo flusso è il modo più rapido per clonare un Master di produzione o ripristinarlo dopo aver cancellato il volume dati. Non serve ripetere la procedura guidata né reinserire le credenziali Cloudflare.

## Dopo il ripristino
- Visita **Impostazioni → Backup e ripristino** per verificare il timestamp più recente nel manifest.
- Controlla **Agenti → Panoramica** per assicurarti che gli agenti registrati si riconnettano correttamente. Se hai ruotato le chiavi, emettine di nuove.
- Avvia una riconciliazione se hai ripristinato il sistema in un ambiente diverso (`Actions → Reconcile Now`).

Mantieni backup offline regolari e abbinali, se possibile, al controllo di versione del tuo stack Compose, così potrai ricostruire rapidamente l'intera distribuzione.
