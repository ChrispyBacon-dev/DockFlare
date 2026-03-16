# Menggunakan Banyak Domain (Indexed Labels)

DockFlare menyediakan fitur **indexed labels** yang memungkinkan Anda mendefinisikan banyak ingress rule yang independen untuk satu container. Ini sangat berguna saat Anda ingin mengekspos port atau path yang berbeda dari layanan yang sama ke hostname publik yang berbeda.

## Cara Kerjanya

Untuk membuat beberapa rule, cukup beri prefix integer dan titik pada label DockFlare standar, dimulai dari `0`. Contohnya `dockflare.0.hostname`, `dockflare.1.hostname`, dan seterusnya.

*   Setiap index mewakili ingress rule yang terpisah.
*   Indexed hostname selalu wajib untuk memulai rule baru.
*   Label lain pada index yang sama hanya akan berlaku untuk rule itu.

## Mekanisme Fallback

Jika Anda tidak memberikan indexed label tertentu untuk sebuah rule, nilainya akan **fallback ke base label yang sesuai**.

Dengan begitu, Anda bisa mendefinisikan pengaturan umum sekali di level dasar lalu hanya meng-override nilai yang memang perlu berubah untuk tiap indexed rule.

## Contoh: Mengekspos Web UI dan API

Misalkan Anda punya satu container yang melayani web application di port `80` dan API terpisah di port `3000`. Anda ingin mengeksposnya di `app.example.com` dan `api.example.com`, sambil mengamankan API dengan Access Group tertentu dan membiarkan aplikasi utama tetap publik.

```yaml
services:
  my-app:
    image: my-application
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"

      # --- Base Labels (Fallback) ---
      - "dockflare.service=http://my-app:80"

      # --- Rule 0: Web UI ---
      - "dockflare.0.hostname=app.example.com"

      # --- Rule 1: API ---
      - "dockflare.1.hostname=api.example.com"
      - "dockflare.1.service=http://my-app:3000"
      - "dockflare.1.access.group=api-users-policy"
```

### Penjabaran Contoh

*   **Rule 0 (`app.example.com`)**:
    *   Mendefinisikan `dockflare.0.hostname`
    *   Tidak mendefinisikan `dockflare.0.service`, jadi akan fallback ke `dockflare.service` yaitu `http://my-app:80`
    *   Tetap publik karena tidak ada access policy untuk index ini maupun pada level dasar

*   **Rule 1 (`api.example.com`)**:
    *   Mendefinisikan `dockflare.1.hostname`
    *   **Meng-override** service dengan `dockflare.1.service` ke port API `3000`
    *   Menerapkan policy keamanan khusus lewat `dockflare.1.access.group`

Pendekatan ini menjaga konfigurasi label tetap rapi dan mengurangi pengulangan di file `docker-compose.yml`.
