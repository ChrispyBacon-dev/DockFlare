# Arsitektur Keamanan & Hardening DockFlare

Dokumen ini menjelaskan bagaimana DockFlare mengamankan node Master maupun Agent yang telah di-enrol pada DockFlare 3.0+. Dokumen ini melengkapi security audit dengan mencatat safeguard yang sudah dibangun ke dalam DockFlare dan praktik operasional yang direkomendasikan.

## 1. Model Kepercayaan Control Plane

- **Master sebagai Source of Truth** – DockFlare Master menyimpan semua kredensial Cloudflare dan definisi policy. Agent tidak pernah mengelola API token; mereka hanya mengeksekusi instruksi melalui channel yang terautentikasi.
- **API key per agent** – Enrolment membutuhkan API key unik yang diterbitkan Master. Kunci-kunci ini disimpan dalam `agent_keys.dat` yang terenkripsi lengkap dengan metadata agar bisa dirotasi atau dicabut kapan saja.
- **Perlindungan Master API** – Endpoint administratif seperti web UI dan `/api/v2/*` memerlukan sesi yang valid atau master API key.

## 2. Konfigurasi Terenkripsi & Manajemen Kunci

- **`dockflare_config.dat` terenkripsi** – kredensial Cloudflare, akun UI, default tunnel, dan master key disimpan dalam blob terenkripsi yang dilindungi `dockflare.key`
- **Registry agent terenkripsi** – agent API key dan metadata audit disimpan di `agent_keys.dat`
- **Restart otomatis saat restore** – saat backup dipulihkan, DockFlare menulis artefak terenkripsi, memuat ulang runtime state, lalu keluar agar Docker langsung merestart container dengan konfigurasi baru
- **`state.json` tetap plaintext** – agar operator tetap bisa memeriksa rule dan agent

## 3. Jaminan Backup & Restore

- **Isi arsip backup** – setiap backup `dockflare_backup_*.zip` berisi `dockflare_config.dat`, `dockflare.key`, `agent_keys.dat`, `state.json`, dan `manifest.json`
- **Alur restore otomatis** – restore lewat setup wizard atau Settings akan menulis artefak, memuat ulang cache runtime, dan memaksa restart container
- **Kompatibilitas legacy** – upload `state.json` standalone masih didukung untuk troubleshooting atau migrasi parsial

## 4. Keamanan Jaringan & Komunikasi

- **Transport Cloudflare Tunnel** – agent tidak mengekspos port inbound
- **Authenticated agent calls** – REST call dari agent menyertakan API key dan agent ID yang sesuai
- **Redis backplane** – Redis dipakai untuk cache, log streaming, dan sinyal antar thread; disarankan tetap pada jaringan privat `dockflare-internal`
- **Runtime least-privilege** – master dan agent berjalan sebagai user `dockflare` UID/GID 65532 dan hanya berbicara ke Docker lewat socket proxy

## 5. Autentikasi & Otorisasi

- **UI login yang diperkeras** – Pre-Flight wizard memaksa pembuatan akun admin UI
- **Manajemen sesi** – sesi Flask-Login terikat pada konfigurasi terenkripsi
- **Agent ACL** – setiap catatan agent melacak assignment tunnel, heartbeat, dan pending command

### ⚠️ Peringatan penting: "Disable Password Login"

DockFlare memiliki pengaturan "Disable Password Login" untuk deployment lanjutan, tetapi **sangat tidak disarankan** bagi sebagian besar penggunaan.

**Risiko keamanan saat diaktifkan:**
- Semua endpoint API dapat diakses tanpa autentikasi
- Container lain pada jaringan Docker yang sama dapat mengakses API DockFlare secara langsung
- Aplikasi mengasumsikan autentikasi eksternal sepenuhnya menangani keamanan

**Pendekatan yang direkomendasikan:**
1. Kredensial lokal DockFlare
2. OAuth/OIDC provider untuk SSO yang aman

**Intinya:** jika Anda tidak punya arsitektur jaringan yang sangat dipahami dan terisolasi, biarkan password login tetap aktif.

## 6. Audit & Visibilitas Operasional

- **Metadata tracking** – agent key mencatat `created_at`, `last_used_at`, `bound_agent_id`, status, dan event pencabutan
- **Log streaming** – log real-time mengalir lewat Redis pub/sub
- **Status API** – `/api/v2/overview` menggabungkan kesehatan tunnel, agent, dan konfigurasi untuk monitoring

## 7. Rekomendasi Deployment

| Area | Rekomendasi |
| --- | --- |
| Docker Volumes | Persist `/app/data` dan `/app/logs` bila file logging diaktifkan |
| Redis | Jalankan `redis:7-alpine` pada jaringan privat atau arahkan `REDIS_URL` ke instance yang sudah diperkeras |
| Backups | Unduh `.zip` secara berkala dan simpan bersama `dockflare.key` |
| Agents | Perlakukan API key sebagai kredensial |
| Reverse Proxy | Tempatkan DockFlare di balik Cloudflare Access atau IdP tepercaya |
| Monitoring | Beri alert untuk restart tak terduga, heartbeat agent hilang, atau penerbitan key baru di luar window maintenance |

## 8. Peningkatan di Masa Depan

- Perlindungan passphrase opsional untuk Fernet key saat disimpan
- Rotasi otomatis agent key dengan grace period
- Scope command agent yang lebih granular

DockFlare terus berkembang dengan fokus keamanan. Ikuti release notes untuk peningkatan hardening berikutnya.
