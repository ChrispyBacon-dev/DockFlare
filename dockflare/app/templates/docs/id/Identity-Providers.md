# Identity Provider

> **📌 Penting:** Panduan ini untuk mengonfigurasi **Identity Provider bagi Cloudflare Access Policies** guna melindungi layanan atau aplikasi Anda. Jika Anda ingin mengonfigurasi OAuth/OIDC untuk **login DockFlare Web UI**, lihat [OAuth Provider Setup](OAuth-Provider-Setup.md).

Identity Provider memungkinkan autentikasi OAuth/OIDC untuk aplikasi Anda yang dilindungi Cloudflare Zero Trust. DockFlare memudahkan pengelolaan IdP dan integrasinya ke access policy Anda.

## Gambaran Umum

Daripada hanya mengandalkan autentikasi berbasis email, Anda bisa memakai provider populer seperti Google, GitHub, Azure AD, dan lainnya. Pengguna akan autentikasi melalui akun yang sudah mereka miliki, sehingga pengalaman login menjadi lebih mulus dan aman.

## Provider yang Didukung

DockFlare mendukung identity provider berikut:

- **Google** - akun Google konsumen
- **Google Workspace** - akun Google Workspace dengan pembatasan domain opsional
- **Microsoft Azure AD** - Microsoft Entra ID
- **Okta** - Okta Identity Cloud
- **GitHub** - GitHub OAuth
- **Generic OpenID Connect** - provider apa pun yang patuh pada standar OIDC

## Mengelola Identity Provider

### Menambahkan Identity Provider

1. Buka halaman **Access Policies**
2. Di bagian **Identity Providers**, klik **Add Provider**
3. Isi field yang diperlukan:
   - **Friendly Name**: nama internal untuk DockFlare, misalnya `google-main`
   - **Display Name**: nama yang tampil di dashboard Cloudflare
   - **Provider Type**: pilih provider OAuth Anda
   - **Configuration**: kredensial khusus provider
4. Klik **Create Provider**
5. Uji provider menggunakan test URL yang disediakan

### Sinkronisasi dari Cloudflare

Jika Anda sudah menyiapkan IdP di Cloudflare Zero Trust:

1. Klik **Sync from Cloudflare** pada bagian Identity Providers
2. DockFlare akan mengimpor semua IdP yang ada dan membuat friendly name otomatis
3. Anda bisa mengganti friendly name agar lebih mudah dipakai di label

### Menguji Identity Provider

Setelah IdP dibuat:

1. Klik menu **⋮** di samping provider
2. Pilih **Test IdP**
3. Jendela baru akan terbuka untuk autentikasi
4. Verifikasi alur login berjalan dengan benar

## Panduan Setup Provider

### Google

**Langkah 1: Buat OAuth Credentials**

1. Buka [Google Cloud Console](https://console.cloud.google.com/)
2. Buat project baru atau pilih yang sudah ada
3. Masuk ke **APIs & Services** → **Credentials**
4. Klik **Create Credentials** → **OAuth client ID**
5. Pilih **Web application**
6. Tambahkan authorized redirect URI:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
7. Salin **Client ID** dan **Client Secret**

**Langkah 2: Konfigurasi di DockFlare**

- **Client ID**: tempel dari Google Cloud Console
- **Client Secret**: tempel dari Google Cloud Console

### Google Workspace

Sama seperti setup Google di atas, dengan field opsional tambahan:

- **Apps Domain**: batasi ke domain tertentu, misalnya `example.com`

### Microsoft Azure AD

**Langkah 1: Register aplikasi di Azure**

1. Buka [Azure Portal](https://portal.azure.com/)
2. Masuk ke **Azure Active Directory** → **App registrations**
3. Klik **New registration**
4. Beri nama aplikasi Anda
5. Pada **Redirect URI**, pilih **Web** lalu isi:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
6. Klik **Register**
7. Salin **Application (client) ID**
8. Salin **Directory (tenant) ID**
9. Masuk ke **Certificates & secrets** → **New client secret**
10. Buat secret lalu salin nilainya

**Langkah 2: Konfigurasi di DockFlare**

- **Application (client) ID**
- **Directory (tenant) ID**
- **Client Secret**

### GitHub

**Langkah 1: Buat OAuth App**

1. Buka [GitHub Developer Settings](https://github.com/settings/developers)
2. Klik **New OAuth App**
3. Isi detail aplikasi
4. Pada **Authorization callback URL**, gunakan:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
5. Klik **Register application**
6. Salin **Client ID**
7. Generate client secret baru lalu salin

**Langkah 2: Konfigurasi di DockFlare**

- **Client ID**
- **Client Secret**

### Okta

**Langkah 1: Buat aplikasi di Okta**

1. Masuk ke [Okta Admin Console](https://admin.okta.com/)
2. Buka **Applications** → **Create App Integration**
3. Pilih **OIDC - OpenID Connect**
4. Pilih **Web Application**
5. Isi redirect URI:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
6. Klik **Save**
7. Salin **Client ID** dan **Client Secret**
8. Catat **Okta domain** Anda

**Langkah 2: Konfigurasi di DockFlare**

- **Okta Account URL**
- **Client ID**
- **Client Secret**

### Generic OpenID Connect

Untuk provider OIDC lain:

**Langkah 1: Ambil konfigurasi provider**

Siapkan:
- Authorization URL
- Token URL
- JWKS URL
- Client ID
- Client Secret

**Langkah 2: Konfigurasi di DockFlare**

- **Authorization URL**
- **Token URL**
- **JWKS URL**
- **Client ID**
- **Client Secret**

## Menggunakan Identity Provider dalam Access Policy

### Dalam Access Groups

1. Buka **Access Policies** → **Advanced Access Policies**
2. Klik **Create New Group** atau edit grup yang ada
3. Di bagian **Policy Rules**:
   - **Identity Providers**: pilih satu atau lebih IdP
   - **Allowed Emails or Domains**: **wajib saat memakai IdP**
4. Simpan grup

### Mode Autentikasi

Anda punya dua opsi:

1. **Email Only**: isi email tanpa memilih IdP - pengguna autentikasi lewat one-time PIN
2. **IdP + Email**: pilih IdP dan isi allowed email - pengguna harus autentikasi lewat IdP terpilih **dan** emailnya harus cocok

**⚠️ Catatan keamanan:** Saat memakai Identity Provider, Anda **wajib** menentukan allowed email. Tanpa pembatasan email, misalnya jika memilih Google, maka siapa pun yang punya akun Google bisa mengakses layanan Anda.

### Dalam Docker Label

Gunakan friendly name pada access group atau label Anda:

```yaml
services:
  myapp:
    image: myapp:latest
    labels:
      dockflare.enable: "true"
      dockflare.hostname: "app.example.com"
      dockflare.access.group: "my-access-group"
```

Access group `my-access-group` akan me-resolve friendly name IdP menjadi Cloudflare UUID secara otomatis.

## Praktik Terbaik

### Penamaan

Gunakan friendly name yang jelas:
- ✅ `google-main`, `github-dev`, `azure-work`
- ❌ `idp1`, `test`, `new`

### Keamanan

- Rotasi secret secara berkala
- Batasi scope bila memungkinkan
- Selalu uji IdP sebelum dipakai di produksi
- Tinjau log Cloudflare untuk mendeteksi upaya akses yang tidak sah

### Banyak Environment

Buat IdP terpisah untuk setiap environment:
- `google-dev`
- `google-staging`
- `google-prod`

### Persyaratan Email Saat Memakai IdP

**PENTING:** Autentikasi IdP selalu membutuhkan pembatasan email demi keamanan.

**Contoh Access Group:**
- **Identity Providers**: `google-main`
- **Allowed Emails**: `admin@example.com, user@example.com, @contractor-domain.com`

Ini berarti pengguna harus:
- login lewat `google-main`
- dan memiliki email yang cocok dengan daftar yang diizinkan

## Troubleshooting

### Error "Invalid Redirect URI"

**Penyebab:** Redirect URI di provider OAuth tidak cocok dengan URI yang diharapkan Cloudflare.

**Solusi:** pastikan Anda memakai URI berikut secara persis:
```
https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
```

### "IdP Test Failed"

**Penyebab:** kredensial atau konfigurasi salah.

**Solusi:**
1. Verifikasi Client ID dan Client Secret
2. Pastikan aplikasi OAuth aktif di provider
3. Untuk Azure AD, verifikasi client ID dan tenant ID
4. Uji provider lewat test URL Cloudflare

### "Cannot Delete System-Managed IdP"

**Penyebab:** Anda mencoba menghapus provider One-Time PIN bawaan.

**Solusi:** provider `onetimepin` dikelola sistem dan tidak dapat dihapus.

### "IdP Not Found in Docker Label"

**Penyebab:** Anda memakai UUID Cloudflare alih-alih friendly name.

**Solusi:** gunakan friendly name seperti `google-main`.

## Dokumentasi Terkait

- [Access Policy Best Practices](Access-Policy-Best-Practices.md)
- [Zone Default Policies](Zone-Default-Policies.md)
- [Container Labels](Container-Labels.md)
- [Security Architecture](Security-Architecture.md)
