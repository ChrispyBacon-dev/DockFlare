# Cara Kerja DockFlare

DockFlare bertindak sebagai jembatan antara environment Docker Anda dan jaringan Cloudflare, mengotomatisasi proses mengekspos layanan ke internet dengan aman. DockFlare terus memantau host Docker Anda dan memakai Cloudflare API untuk mengelola Tunnel, DNS record, dan Access Policy atas nama Anda.

## Alur Kerja Inti

Alur inti DockFlare dapat dipecah menjadi beberapa langkah penting:

1.  **Pemantauan Event Docker**: DockFlare mendengarkan event dari Docker socket, seperti `start` dan `stop` untuk container.

2.  **Deteksi Label**: Saat container baru berjalan, DockFlare akan memeriksanya untuk mencari label `dockflare.`. Jika sebuah container memiliki `dockflare.enable=true`, DockFlare tahu bahwa container itu harus dikelola.

3.  **Interaksi dengan Cloudflare API**: Berdasarkan label yang ada, DockFlare berkomunikasi dengan Cloudflare API untuk menyiapkan resource yang diperlukan:
    *   **Cloudflare Tunnel**: DockFlare menambahkan ingress rule ke Cloudflare Tunnel yang Anda tentukan. Rule ini mengarahkan hostname publik ke alamat jaringan internal container, misalnya `http://my-app:8080`.
    *   **Manajemen DNS**: DockFlare membuat record CNAME pada Cloudflare DNS zone Anda, mengarahkan hostname publik yang diinginkan, misalnya `my-app.example.com`, ke Cloudflare Tunnel.
    *   **Access Policy**: Jika Anda menentukan label access control, DockFlare akan membuat atau memperbarui reusable Cloudflare Access Policy untuk melindungi layanan dengan aturan Zero Trust, misalnya mewajibkan login lewat identity provider atau menerbitkan `bypass` publik.

4.  **Pembersihan Otomatis**: Saat container yang dikelola dihentikan atau dihapus, DockFlare otomatis menjalankan proses cleanup. DockFlare menghapus ingress rule terkait dari Cloudflare Tunnel dan, jika tidak ada layanan lain yang memakai hostname tersebut, juga menghapus DNS record serta Access Application. Ini mencegah record usang dan menjaga konfigurasi Cloudflare tetap bersih.

## Komponen Singkat

| Komponen | Tanggung jawab |
| --- | --- |
| DockFlare Master | Menyediakan UI dan API, memantau event Docker, serta mengorkestrasi Cloudflare Tunnel, DNS, dan Access Policy. Berjalan rootless dan hanya berbicara ke Docker lewat socket proxy. |
| Docker Socket Proxy | Sidecar `tecnativa/docker-socket-proxy` yang mengekspos permukaan Docker API minimal (`containers`, `events`, dan sebagainya) ke master. Mencegah master mengikat raw Docker socket. |
| Redis | Caching, queue, log streaming, dan backchannel heartbeat agent. Berada di jaringan privat `dockflare-internal`. |
| DockFlare Agent (opsional) | Worker remote yang mencerminkan perilaku master pada host lain, mengalirkan event Docker kembali dan mengelola `cloudflared` lokalnya sendiri. |
| cloudflared | Menjaga koneksi tunnel ke Cloudflare, baik untuk master maupun masing-masing agent. |

## Model Konfigurasi Berlapis

DockFlare memakai pendekatan konfigurasi berlapis yang fleksibel, memberi Anda otomatisasi sekaligus kontrol yang detail:

1.  **Docker Labels (Lapisan Dasar)**: Ini adalah metode utama dan otomatis. Anda mendefinisikan seluruh konfigurasi layanan, seperti hostname, URL internal, dan access policy, langsung di `docker-compose.yml` atau perintah Docker Anda. Inilah "source of truth" untuk layanan otomatis.

2.  **Access Groups (Lapisan Abstraksi)**: Agar Anda tidak perlu mengulang policy yang kompleks di banyak layanan, Anda bisa membuat **Access Groups** yang dapat digunakan ulang lewat Web UI. Grup ini adalah template yang membungkus sekumpulan aturan akses, misalnya "izinkan email perusahaan" atau "izinkan akses dari negara tertentu", lalu disinkronkan menjadi reusable Cloudflare Access Policy bernama. Toggle Public vs Authenticated di modal menentukan apakah DockFlare mengirim keputusan `bypass` atau `allow`. Dengan begitu, satu policy penuh bisa diterapkan ke container hanya lewat satu label, `dockflare.access.group=my-policy-group`.

3.  **Web UI Overrides (Lapisan Kontrol)**: Web UI memberi level kontrol tertinggi. Dari dashboard, Anda bisa:
    *   **Meng-override** access policy untuk layanan apa pun, baik yang didefinisikan lewat label maupun Access Group. Override ini persisten dan tidak akan hilang saat container restart.
    *   **Membuat Manual Ingress Rules** untuk layanan yang tidak berjalan di Docker, misalnya layanan di mesin lain di jaringan Anda.
    *   **Me-revert** konfigurasi layanan kembali ke apa yang didefinisikan oleh label Docker, membuang override dari UI.

Model berlapis ini memungkinkan Anda memakai pola "set it and forget it" dengan label Docker untuk sebagian besar layanan, sambil tetap punya kemampuan menangani pengecualian dan skenario yang lebih kompleks lewat Web UI.

---

## Arsitektur Access Policy (v3.0.3+)

### Sistem Reusable Policy

DockFlare kini menggunakan **arsitektur reusable policy** yang selaras dengan best practice Cloudflare:

1. **Access Groups** → sinkron ke → **Cloudflare Reusable Policies**
2. **Access Applications** → mereferensikan → **Reusable Policy IDs**
3. **Single source of truth** - sekali diperbarui, berlaku di mana-mana

Arsitektur ini menghilangkan duplikasi policy dan memungkinkan Anda mengelola policy baik dari DockFlare maupun dashboard Cloudflare dengan sinkronisasi dua arah penuh.

### System-Managed Policies

DockFlare otomatis mengelola dua policy inti untuk konsistensi:

- **`public-default-bypass`**: policy bypass akses publik
  - System policy yang tidak bisa dihapus
  - Dibuat otomatis saat inisialisasi
  - Nama di Cloudflare: `DockFlare-Default-Public-Access-Bypass`
  - Keputusan: `bypass` dengan aturan include `everyone`
  - Dipakai oleh semua layanan yang butuh akses publik dengan bypass terhadap zone protection
  - Mencegah policy bypass duplikat di dashboard Cloudflare Anda

- **`authenticated-default`**: policy autentikasi default
  - System policy yang tidak bisa dihapus
  - Dibuat otomatis saat inisialisasi
  - Nama di Cloudflare: `DockFlare-Default-Authenticated-Access`
  - Keputusan: `allow` dengan one-time PIN + pembatasan email
  - Dipakai untuk skenario akses terautentikasi dasar

### Migrasi Legacy Label

DockFlare otomatis memigrasikan legacy label agar memakai system policy:

- `dockflare.access.policy=bypass` → memakai `public-default-bypass`
- `dockflare.access.group=bypass` → memakai `public-default-bypass`
- `dockflare.access.policy=authenticate` → memakai `authenticated-default`

Migrasi terjadi secara transparan selama pemrosesan container dan reconciliation. Tidak perlu intervensi manual.

### Zone Default Policies

Policy wildcard tingkat zone (`*.domain.com`) memberi keamanan berlapis melalui prioritas policy:

1. **Specific hostname policy** (mis. `app.example.com`) - prioritas tertinggi
2. **Zone wildcard policy** (mis. `*.example.com`) - fallback
3. **Tanpa policy** = akses publik (tanpa Access App) - default

Dengan begitu, layanan yang terlupa atau tidak terdokumentasi tetap terlindungi oleh policy tingkat zone sebagai jaring pengaman keamanan.

**Contoh:**
- Zone policy: `*.internal.company.com` → mewajibkan autentikasi email perusahaan
- Specific service: `public-demo.internal.company.com` → memakai `public-default-bypass`
- Forgotten service: `test.internal.company.com` → dilindungi oleh zone policy (wajib autentikasi)
