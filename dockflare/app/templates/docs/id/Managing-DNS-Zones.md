# Mengelola DNS Zone

DockFlare mampu mengelola DNS record di banyak domain atau Cloudflare Zone dalam akun Cloudflare yang sama. Dengan begitu, Anda bisa menjalankan layanan di `service-a.domain-one.com` dan `service-b.another-domain.org` dari satu instance DockFlare yang sama.

## Default Zone

Saat setup awal DockFlare, Anda akan memberikan **Zone ID**. Ini adalah **default zone** tempat DockFlare membuat semua DNS record. Jika Anda hanya memakai satu domain, itu sudah cukup.

## Mengganti Zone lewat Label

Untuk mengelola service pada domain selain default zone, Anda bisa memakai label `dockflare.zonename`.

Label ini memberi tahu DockFlare untuk membuat DNS record service tertentu pada Cloudflare Zone yang disebutkan.

### Prasyarat

Agar ini berfungsi, pastikan **Cloudflare API Token** yang Anda pakai memiliki permission `Zone:DNS:Edit` untuk **semua zone** yang ingin Anda kelola.

### Contoh

Misalkan default zone Anda adalah `example.com`, tetapi Anda juga ingin menjalankan service pada `media.io`.

```yaml
services:
  # Service ini akan dibuat di default zone (example.com)
  service-one:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://service-one:80"

  # Service ini akan dibuat di zone 'media.io'
  service-two:
    image: portainer/portainer-ce
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=portainer.media.io"
      - "dockflare.service=http://service-two:9000"
      # Override default zone untuk service ini
      - "dockflare.zonename=media.io"
```

Saat di-deploy, DockFlare akan:
1. Membuat CNAME record untuk `nginx.example.com` di zone `example.com`.
2. Membuat CNAME record untuk `portainer.media.io` di zone `media.io`.

Kedua hostname itu akan ditambahkan sebagai ingress rule pada Cloudflare Tunnel yang sama.

## Melihat DNS Record di UI

DockFlare Web UI memiliki fitur pada halaman **Settings** yang memungkinkan Anda melihat semua Cloudflare Tunnel pada akun Anda beserta DNS record yang mengarah ke sana.

Agar UI bisa menemukan DNS record di semua zone yang berbeda, Anda bisa memakai environment variable `TUNNEL_DNS_SCAN_ZONE_NAMES`.

### `TUNNEL_DNS_SCAN_ZONE_NAMES`

Environment variable ini menerima daftar nama zone yang dipisahkan koma, yang harus dipindai UI saat mencari DNS record.

**Contoh `docker-compose.yml`:**

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... pengaturan lain
    environment:
      # Beri tahu UI untuk memindai zone ini selain default zone
      - TUNNEL_DNS_SCAN_ZONE_NAMES=media.io,another-domain.org
```

Dengan ini, tampilan DNS record viewer di UI akan memberi gambaran lengkap tentang semua domain yang mengarah ke tunnel Anda.
