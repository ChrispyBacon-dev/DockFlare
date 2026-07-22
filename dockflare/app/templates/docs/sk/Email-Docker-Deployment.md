# Nasadenie cez Docker (e-mailový profil)

E-mailová sada DockFlare pozostáva z dvoch ďalších mikroslužieb: **Mail Manager** a **Webmail PWA**. Tieto služby sú voliteľné a spravujú sa pomocou Docker Compose **profilov**.

## Zapnutie e-mailového profilu

Na spustenie DockFlare s podporou e-mailu musíš pri príkazoch Docker Compose zahrnúť profil `email`.

### Spustenie kontajnerov
```bash
docker compose --profile email up -d
```

### Zastavenie kontajnerov
Ak spustíš `docker compose down`, zastaví všetky služby vrátane e-mailu. Na opätovné spustenie s e-mailom nezabudni zahrnúť profil:
```bash
docker compose --profile email up -d
```

## Konfigurácia Docker Compose

E-mailové služby sú už zahrnuté v predvolenom `docker-compose.yml`. Relevantné sekcie sú:

```yaml
  dockflare-mail-manager:
    image: alplat/dockflare-mail-manager:stable
    container_name: dockflare-mail-manager
    restart: unless-stopped
    profiles: ["email"]
    environment:
      - DOCKFLARE_MASTER_URL=http://dockflare:5000
      - MAIL_DATA_PATH=/data
    volumes:
      - mail_data:/data
    depends_on:
      dockflare:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

  dockflare-webmail:
    image: alplat/dockflare-webmail:stable
    container_name: dockflare-webmail
    restart: unless-stopped
    profiles: ["email"]
    environment:
      - DOCKFLARE_MASTER_URL=https://dockflare.TLD  # nahraď svojou doménou
    labels:
      - dockflare.enable=true
      - dockflare.hostname=mail.dockflare.TLD  # nahraď svojou doménou
      - dockflare.service=http://dockflare-webmail:80
    depends_on:
      dockflare-mail-manager:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  mail_data:
```

> **Dôležité:** Pred spustením e-mailového profilu aktualizuj dve zástupné hodnoty v službe `dockflare-webmail`:
> - `DOCKFLARE_MASTER_URL` — verejná HTTPS URL tvojho DockFlare Mastera (napr. `https://dockflare.example.com`)
> - label `dockflare.hostname` — subdoména, kde bude webmail dostupný (napr. `mail.example.com`)

## Rozbor služieb

| Služba | Popis | Port |
| :--- | :--- | :--- |
| `dockflare-mail-manager` | Backendový engine, ktorý spracúva MIME, spravuje SQLite a obsluhuje webhooky. | Iba interne |
| `dockflare-webmail` | Frontendová aplikácia pre používateľov postavená na Vue. | 80 (interne) |

## Trvalé volumes

E-mailová sada zavádza nový volume: `mail_data`.

*   **Umiestnenie:** `/data` vnútri kontajnera `mail-manager`.
*   **Obsah:**
    *   `/data/db/mail.db`: SQLite databáza obsahujúca všetky metadáta správ a vyhľadávacie indexy.
    *   `/data/attachments/`: Úložisko v súborovom systéme pre všetky e-mailové prílohy.
*   **Dôležitosť:** **Tento volume nikdy nemaž**, pokiaľ nechceš natrvalo vymazať všetky uložené e-maily. Zabezpeč, aby bol tento volume zahrnutý v tvojej zálohovacej stratégii na úrovni hostiteľa.

## Overenie

Keď sú kontajnery spustené, skontroluj ich stav v hlavnom rozhraní DockFlare pod navigačnou položkou **E-mail**. Pri oboch službách by si mal v karte **Stav kontajnerov** vidieť zelený stav „Beží“.
