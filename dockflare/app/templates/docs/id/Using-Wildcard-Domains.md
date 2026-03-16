# Menggunakan Wildcard Domain

DockFlare mendukung wildcard domain, misalnya `*.example.com`, untuk merutekan trafik dari banyak subdomain ke satu layanan. Ini sangat berguna untuk aplikasi yang menangani subdomain dinamis, seperti layanan multi-tenant atau dashboard pribadi seperti Heimdall.

## Cara Kerjanya

Saat Anda memakai wildcard hostname, Cloudflare Tunnel akan merutekan semua trafik untuk subdomain apa pun yang tidak memiliki DNS record yang lebih spesifik ke service yang Anda tentukan.

Misalnya, jika Anda mengonfigurasi `*.apps.example.com`, maka trafik untuk `service1.apps.example.com`, `service2.apps.example.com`, dan seterusnya akan diarahkan ke container tujuan yang sama.

## Hal Penting yang Perlu Diperhatikan

Berbeda dengan hostname biasa, DockFlare **tidak bisa membuat DNS record wildcard secara otomatis**. Anda harus membuat wildcard DNS record secara manual di dashboard Cloudflare.

DockFlare tetap akan mengelola **ingress rule** pada Cloudflare Tunnel, tetapi setup DNS awal tetap merupakan langkah manual.

## Panduan Langkah demi Langkah

Berikut cara menyiapkan wildcard domain dengan benar di DockFlare, memakai `*.plex.example.com` sebagai contoh.

### Langkah 1: Buat Wildcard DNS Record Secara Manual

1. Masuk ke **Cloudflare Dashboard**.
2. Buka pengaturan DNS untuk domain Anda.
3. Klik **Add record** lalu buat CNAME record dengan detail berikut:
    *   **Type:** `CNAME`
    *   **Name:** `*.plex` atau cukup `*` jika domain utama Anda adalah `plex.example.com`
    *   **Target:** hostname publik milik tunnel Anda. Anda bisa menemukannya di dashboard Cloudflare Zero Trust pada **Access -> Tunnels**. Biasanya berbentuk `your-tunnel-uuid.cfargotunnel.com`.
    *   **Proxy status:** Pastikan **Proxied** dengan ikon awan oranye.

Record DNS manual ini memberi tahu Cloudflare untuk mengirim semua trafik `*.plex.example.com` ke tunnel Anda.

### Langkah 2: Konfigurasikan Service dengan Wildcard Label

Sekarang, konfigurasikan service Anda di file `docker-compose.yml` dengan label wildcard hostname.

```yaml
services:
  my-proxy-manager:
    image: nginxproxymanager/nginx-proxy-manager
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      # Gunakan wildcard hostname di sini
      - "dockflare.hostname=*.plex.example.com"
      - "dockflare.service=http://my-proxy-manager:81"
```

### Langkah 3: Deploy dan Verifikasi

1. Simpan `docker-compose.yml` lalu jalankan `docker compose up -d`.
2. DockFlare akan mendeteksi container itu dan membuat ingress rule pada Cloudflare Tunnel Anda untuk hostname `*.plex.example.com`.
3. Anda dapat memverifikasinya di DockFlare Web UI dan pada konfigurasi tunnel di dashboard Cloudflare.

Sekarang, setiap request ke subdomain seperti `sonarr.plex.example.com` atau `radarr.plex.example.com` akan dirutekan melalui Cloudflare Tunnel ke container `my-proxy-manager`, yang kemudian dapat menangani trafik itu sesuai kebutuhan.
