# Docker Deployment (Email Profile)

The DockFlare Email Suite consists of two additional microservices: the **Mail Manager** and the **Webmail PWA**. These services are optional and are managed using Docker Compose **profiles**.

## Enabling the Email Profile

To start DockFlare with email support, you must include the `email` profile when running your Docker Compose commands.

### Starting the containers
```bash
docker compose --profile email up -d
```

### Stopping the containers
If you run `docker compose down`, it will stop all services including email. To restart with email again, remember to include the profile:
```bash
docker compose --profile email up -d
```

## Docker Compose Configuration

The email services are already included in the default `docker-compose.yml`. The relevant sections are:

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
      - DOCKFLARE_MASTER_URL=https://dockflare.TLD  # replace with your domain
    labels:
      - dockflare.enable=true
      - dockflare.hostname=mail.dockflare.TLD  # replace with your domain
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

> **Important:** Before starting the email profile, update the two placeholder values in the `dockflare-webmail` service:
> - `DOCKFLARE_MASTER_URL` — the public HTTPS URL of your DockFlare Master (e.g. `https://dockflare.example.com`)
> - `dockflare.hostname` label — the subdomain where Webmail will be accessible (e.g. `mail.example.com`)

## Service Breakdown

| Service | Description | Port |
| :--- | :--- | :--- |
| `dockflare-mail-manager` | The backend engine that processes MIME, manages SQLite, and handles webhooks. | Internal only |
| `dockflare-webmail` | The Vue-based frontend application for users. | 80 (Internal) |

## Persistent Volumes

The Email Suite introduces a new volume: `mail_data`.

*   **Location:** `/data` inside the `mail-manager` container.
*   **Contents:** 
    *   `/data/db/mail.db`: The SQLite database containing all message metadata and search indices.
    *   `/data/attachments/`: The filesystem storage for all email attachments.
*   **Importance:** **Never delete this volume** unless you want to permanently erase all stored emails. Ensure this volume is included in your host-level backup strategy.

## Verification

Once the containers are started, check their status in the DockFlare Master UI under the **Email** navigation item. You should see a green "Running" status for both services in the **Container Status** card.
