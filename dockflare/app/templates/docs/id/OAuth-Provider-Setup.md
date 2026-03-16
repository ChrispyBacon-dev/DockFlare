## Setup OAuth Provider

> **📌 Penting:** Panduan ini untuk mengonfigurasi **autentikasi DockFlare Web UI** atau login ke DockFlare itu sendiri. Jika Anda ingin mengonfigurasi OAuth/OIDC untuk **Cloudflare Access Policies** agar melindungi layanan, lihat [Identity Providers](Identity-Providers.md).

DockFlare memungkinkan Anda mendelegasikan autentikasi pengguna ke provider eksternal dengan standar OpenID Connect (OIDC). Ini memungkinkan single sign-on untuk antarmuka web DockFlare dan integrasi dengan provider seperti Google, Authentik, Okta, dan lainnya.

### Menambahkan Provider Baru

Ikuti langkah berikut untuk menambahkan provider OIDC baru:

1. **Buka Settings:** dari dashboard utama, masuk ke halaman **Settings**.
2. **Cari bagian OAuth:** scroll ke bagian **OAuth Authentication**.
3. **Tambah provider:** klik **Add Provider** untuk membuka modal konfigurasi.

Field yang akan muncul:

*   **Provider Type:** diset ke `OpenID Connect (OIDC)`, standar modern untuk autentikasi federatif.
*   **Issuer URL:** field terpenting. Ini adalah base URL provider OIDC Anda yang dipakai DockFlare untuk menemukan konfigurasi provider secara otomatis.
*   **Provider ID:** nama pendek, unik, huruf kecil, misalnya `google` atau `authentik-corp`. Dipakai secara internal dan di callback URL.
*   **Display Name:** nama ramah pengguna yang akan muncul di tombol login, misalnya `Google`.
*   **Client ID:** identifier publik untuk aplikasi DockFlare, diperoleh dari console developer provider.
*   **Client Secret:** secret rahasia untuk aplikasi DockFlare.
*   **Enable Provider:** checkbox untuk mengaktifkan atau menonaktifkan provider kapan saja.

Setelah detail diisi, klik **Add Provider** untuk menyimpan.

### Menemukan Callback URL

Setelah provider ditambahkan, **Callback URL** yang dibutuhkan akan ditampilkan di bawah entri provider di halaman Settings.

Anda harus menyalin URL itu persis dan menambahkannya ke daftar callback URL yang diizinkan pada console administrasi provider Anda.

---

### Contoh: Menyiapkan Google

1. Buka [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Klik **+ CREATE CREDENTIALS** lalu pilih **OAuth client ID**.
3. Pada **Application type**, pilih **Web application**.
4. Di **Authorized redirect URIs**, klik **+ ADD URI** lalu isi callback URL dari DockFlare, misalnya `https://your-dockflare-domain.com/auth/google/callback`.
5. Klik **CREATE** lalu salin **Client ID** dan **Client Secret**.
6. Isi di DockFlare:
    *   **Issuer URL:** `https://accounts.google.com`
    *   **Provider ID:** `google`
    *   **Display Name:** `Google`
    *   **Client ID:** nilai dari Google
    *   **Client Secret:** nilai dari Google

Simpan provider di DockFlare, dan Anda akan bisa login memakai akun Google.

---

### Mengonfigurasi DockFlare dengan OAuth dan Access Policy

Saat menggunakan autentikasi OAuth, Anda mungkin ingin melindungi antarmuka utama DockFlare dengan access policy sambil memastikan callback OAuth tetap bisa diakses. Ini sangat penting bila instance DockFlare Anda memakai pembatasan IP atau kontrol akses lain.

#### Praktik terbaik: Bypass policy untuk callback OAuth

Gunakan indexed labels untuk membuat rule terpisah bagi antarmuka utama dan path callback OAuth:

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    labels:
      # Antarmuka utama DockFlare dengan access policy
      - "dockflare.enable=true"
      - "dockflare.hostname=dockflare.example.com"
      - "dockflare.service=http://dockflare:5000"
      - "dockflare.access.group=team"

      # Path callback OAuth dengan bypass policy
      - "dockflare.0.hostname=dockflare.example.com"
      - "dockflare.0.path=/auth/google/callback"
      - "dockflare.0.service=http://dockflare:5000"
      - "dockflare.0.access.policy=bypass"

      # Tambahkan callback path lain bila perlu
      - "dockflare.1.hostname=dockflare.example.com"
      - "dockflare.1.path=/auth/github/callback"
      - "dockflare.1.service=http://dockflare:5000"
      - "dockflare.1.access.policy=bypass"
```

#### Mengapa konfigurasi ini diperlukan

- **Perlindungan antarmuka utama**: dashboard DockFlare tetap dilindungi
- **Fungsionalitas OAuth**: callback OAuth bisa mencapai DockFlare tanpa hambatan autentikasi
- **Keamanan**: hanya path callback tertentu yang dibypass
- **Fleksibilitas**: bekerja untuk kombinasi access policy apa pun

#### Catatan penting

1. **Path matching**: callback path harus persis sama dengan yang diharapkan provider OAuth
2. **Banyak provider**: tambahkan indexed rule terpisah untuk setiap provider
3. **Jangan gunakan wildcard path** untuk alasan keamanan
4. **Pengujian**: uji akses yang dilindungi dan alur login OAuth setelah konfigurasi
