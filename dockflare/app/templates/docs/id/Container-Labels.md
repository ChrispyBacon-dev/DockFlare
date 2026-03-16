# Referensi Label Container

DockFlare terutama dikonfigurasi melalui label Docker yang ditempelkan pada container Anda. Halaman ini memberikan referensi lengkap untuk semua label yang didukung.

## Konfigurasi Dasar

Label berikut mengatur routing dasar dan definisi layanan untuk sebuah container.

| Label | Deskripsi | Contoh |
| :--- | :--- | :--- |
| `dockflare.enable` | **Wajib.** Sakelar utama. Harus bernilai `true` agar DockFlare mengelola container. | `dockflare.enable=true` |
| `dockflare.hostname` | **Wajib.** Hostname publik untuk layanan Anda. | `dockflare.hostname=myservice.example.com` |
| `dockflare.service` | **Wajib.** URL internal layanan yang harus dihubungi Cloudflare Tunnel. Bisa berupa `http`, `https`, `tcp`, `ssh`, `rdp`, `http_status:XXX`, atau `bastion`. | `dockflare.service=http://my-app-container:8080` |
| `dockflare.path` | Path URL yang diarahkan ke layanan ini. Berguna untuk mengekspos beberapa layanan pada hostname yang sama. | `dockflare.path=/api` |
| `dockflare.zonename` | (Opsional) Cloudflare zone eksplisit tempat DNS record dibuat. Jika tidak diisi, DockFlare akan mendeteksi zone secara otomatis dari hostname dan hanya fallback ke default `CF_ZONE_ID` bila deteksi gagal. | `dockflare.zonename=another-domain.com` |
| `dockflare.no_tls_verify` | Jika `true`, verifikasi sertifikat TLS antara `cloudflared` dan origin service akan dimatikan. Berguna untuk origin dengan sertifikat self-signed. | `dockflare.no_tls_verify=true` |
| `dockflare.originsrvname` | Menetapkan hostname SNI khusus untuk koneksi TLS ke origin. Di dashboard Cloudflare ini dikenal sebagai Origin Server Name. | `dockflare.originsrvname=internal.service.local` |
| `dockflare.httpHostHeader` | Meng-override header `Host` yang dikirim `cloudflared` ke origin service. | `dockflare.httpHostHeader=custom-host.internal` |
| `dockflare.http2_origin` | Jika `true`, mengaktifkan HTTP/2 antara `cloudflared` dan origin service. Diperlukan untuk layanan gRPC. Hanya berlaku untuk HTTP/HTTPS. | `dockflare.http2_origin=true` |
| `dockflare.disable_chunked_encoding` | Jika `true`, menonaktifkan chunked transfer encoding pada HTTP/1.1. Berguna untuk server WSGI seperti Flask, Django, FastAPI, dan origin lain yang tidak mendukung chunked request dengan baik. | `dockflare.disable_chunked_encoding=true` |

> **Tip:** Sejak DockFlare v3.0, Anda biasanya tidak perlu lagi mengisi `dockflare.zonename`. Master akan mendeteksi Cloudflare zone yang benar dari suffix hostname dan hanya memakai default zone bila tidak menemukan kecocokan.

> **Catatan:** Opsi Cloudflare **Match SNI to Host** tersedia pada konfigurasi manual rule di dashboard. Saat ini opsi tersebut belum bisa diatur lewat Docker label.

---

## Konfigurasi Access Policy

Label berikut memungkinkan Anda membuat dan mengelola Cloudflare Access application secara dinamis untuk mengamankan layanan Anda.

**Catatan:** Sangat dianjurkan memakai **Access Groups** lewat `dockflare.access.group`. DockFlare 3.0.3 menyinkronkan setiap Access Group menjadi reusable Cloudflare Access Policy bernama. Jika `dockflare.access.group` atau `dockflare.access.groups` dipakai, semua label `dockflare.access.*` lain akan diabaikan.

### Perubahan Penting di v3.0.3

#### System Default Bypass Policy

Mulai v3.0.3, saat Anda memakai `dockflare.access.policy=bypass` atau `dockflare.access.group=bypass`, layanan akan mereferensikan reusable policy `public-default-bypass` yang dikelola sistem, bukan membuat inline policy baru. Ini menjaga dashboard Cloudflare tetap bersih.

- **Sebelum v3.0.3:** tiap bypass rule membuat inline policy terpisah
- **v3.0.3+:** semua bypass rule berbagi satu policy `public-default-bypass`

#### Migrasi Legacy Label

DockFlare otomatis memigrasikan legacy bypass label ke system policy terpusat:

- `dockflare.access.policy=bypass` → memakai `public-default-bypass`
- `dockflare.access.group=bypass` → memakai `public-default-bypass`

Migrasi ini berlangsung transparan saat pemrosesan container dan reconciliation.

#### Konfigurasi Access yang Disederhanakan

Untuk skenario akses yang kompleks seperti autentikasi email/domain atau IP allowlist, kini lebih disarankan:

1. Membuat Access Group di halaman **Access Policies**
2. Mereferensikannya dengan `dockflare.access.group=your-group-id`

Opsi quick-create telah dihapus dari UI untuk mendorong alur kerja best practice ini.

#### Label Zone Default Policy

Label `dockflare.access.policy=default_tld` masih berfungsi dan akan mewarisi perlindungan dari wildcard policy `*.domain.com` milik zone Anda. Jika zone policy tidak ada, service akan publik.

**Rekomendasi:** buat zone default policy untuk semua domain Anda melalui UI.

| Label | Deskripsi | Contoh |
| :--- | :--- | :--- |
| `dockflare.access.group` | ID dari satu Access Group yang sudah dikonfigurasi sebelumnya untuk diterapkan ke service ini. ID ini bisa dilihat di halaman **Access Policies** di DockFlare UI. | `dockflare.access.group=internal-tools-policy` |
| `dockflare.access.groups` | Daftar ID Access Group yang dipisahkan koma. Memungkinkan Anda melapisi beberapa policy pada satu service. | `dockflare.access.groups=allow-team-a,allow-admins` |
| `dockflare.access.policy` | Jenis policy utama. Bisa `bypass`, `authenticate`, atau `default_tld`. Jika kosong, service akan publik. Lebih baik gunakan Access Groups untuk reusable policy. | `dockflare.access.policy=authenticate` |
| `dockflare.access.name` | Nama kustom untuk Cloudflare Access Application. Default-nya `DockFlare-{hostname}`. | `dockflare.access.name=My Web App Access` |
| `dockflare.access.session_duration` | Durasi sesi bagi pengguna terautentikasi, misalnya `24h` atau `30m`. Default `24h`. | `dockflare.access.session_duration=1h` |
| `dockflare.access.app_launcher_visible` | Jika `true`, aplikasi akan terlihat di Cloudflare Access App Launcher. | `dockflare.access.app_launcher_visible=true` |
| `dockflare.access.allowed_idps` | Daftar UUID Identity Provider yang diizinkan, dipisahkan koma. UUID ini bisa Anda temukan di dashboard Cloudflare Zero Trust. | `dockflare.access.allowed_idps=uuid1,uuid2` |
| `dockflare.access.auto_redirect_to_identity` | Jika `true`, pengguna akan langsung diarahkan ke halaman login IdP alih-alih splash page Cloudflare Access. | `dockflare.access.auto_redirect_to_identity=true` |
| `dockflare.access.custom_rules` | String JSON berisi array Cloudflare Access Policy rules. Memberi fleksibilitas maksimal untuk policy unik yang kompleks. | `dockflare.access.custom_rules='[{\"email\":{\"email\":\"user@example.com\"},\"action\":\"allow\"}]'` |

---

## Indexed Labels untuk Banyak Domain

DockFlare mendukung beberapa hostname untuk satu container dengan indexed labels. Ini berguna untuk mengekspos port atau path yang berbeda dari layanan yang sama pada hostname publik yang berbeda.

Untuk memakainya, tambahkan prefix angka ke label, dimulai dari `0`.

*   Indexed hostname seperti `<index>.hostname` selalu wajib ada.
*   Label lain pada index yang sama akan meng-override label dasar untuk hostname tersebut.
*   Jika sebuah indexed label tidak disediakan, nilainya akan fallback ke base label yang sesuai.

### Contoh

Contoh ini mengekspos dua hostname dari satu container:
1. `app.example.com` menuju antarmuka web utama di port `80`
2. `api.example.com` menuju API di port `3000` dan diamankan dengan Access Group khusus

```yaml
services:
  my-multi-service:
    image: my-app
    labels:
      - "dockflare.enable=true"

      # --- Definition 0 ---
      - "dockflare.0.hostname=app.example.com"
      - "dockflare.0.service=http://my-multi-service:80"

      # --- Definition 1 ---
      - "dockflare.1.hostname=api.example.com"
      - "dockflare.1.service=http://my-multi-service:3000"
      - "dockflare.1.access.group=api-access-policy"
```
