# Mengakses Web UI

Setelah container DockFlare berhasil dijalankan, Anda bisa membuka web UI untuk mengelola pengaturan, melihat status tunnel, dan mengonfigurasi aturan ingress secara manual.

## URL Default

Secara default, web UI DockFlare dapat diakses pada port `5000`. Untuk membukanya, buka browser dan kunjungi URL berikut:

```
http://<your-server-ip>:5000
```

Ganti `<your-server-ip>` dengan alamat IP server tempat DockFlare berjalan.

## Setup Pertama Kali

Saat pertama kali mengakses web UI, Anda akan dipandu oleh **Pre-Flight Setup Wizard**. Wizard ini membantu Anda:

1. Me-restore dari arsip backup DockFlare yang sudah ada (`dockflare_backup_*.zip`). Jika memilih opsi ini, sistem akan mengimpor konfigurasi terenkripsi, state, dan agent key, lalu merestart container secara otomatis agar perubahan diterapkan.
2. Membuat akun administrator dan password untuk web UI.
3. Mengisi Cloudflare Account ID, Zone ID (opsional), dan API token.
4. Mengonfirmasi pengaturan tunnel dan menyelesaikan onboarding.

## Login

Setelah setup awal selesai, Anda akan melihat halaman login setiap kali mengakses web UI. Gunakan password yang dibuat saat setup untuk masuk.

## Menonaktifkan Login dengan Password

DockFlare menyediakan pengaturan "Disable Password Login" untuk deployment lanjutan di mana DockFlare sendiri sudah dilindungi oleh lapisan autentikasi eksternal seperti Cloudflare Access. **Kami sangat tidak menyarankan fitur ini** untuk sebagian besar deployment.

### Mengapa pengaturan ini ada

Jika Anda menjalankan DockFlare di belakang Cloudflare Access atau authentication proxy lain yang sudah memaksa SSO sebelum pengguna mencapai aplikasi, Anda bisa menonaktifkan login password bawaan DockFlare agar tidak terjadi autentikasi ganda.

### Risiko keamanan saat diaktifkan

- ⚠️ **Semua endpoint API akan bisa diakses tanpa autentikasi** saat pengaturan ini aktif
- ⚠️ **Eksposur jaringan Docker:** Walaupun DockFlare dilindungi Cloudflare Access dari internet publik, container lain di jaringan Docker yang sama tetap bisa melewati autentikasi eksternal dan mengakses API DockFlare secara langsung
- ⚠️ **Tidak ada penegakan autentikasi internal:** Aplikasi mengasumsikan bahwa autentikasi eksternal sudah menangani keamanan

### Contoh attack vector

```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

Bahkan jika DockFlare terlindungi dari internet oleh Cloudflare Access, container mana pun yang berjalan pada jaringan Docker yang sama tetap bisa melewati perlindungan itu dan mengakses endpoint API DockFlare tanpa autentikasi.

### Pendekatan yang direkomendasikan

Daripada menonaktifkan autentikasi password, gunakan salah satu opsi aman berikut:

1. **Kredensial lokal DockFlare** - autentikasi password sederhana yang sudah disediakan DockFlare
2. **OAuth/OIDC provider** - konfigurasikan Google, GitHub, Azure AD, atau provider identitas lain untuk pengalaman single sign-on yang nyaman tanpa mengorbankan keamanan (lihat [OAuth Provider Setup](OAuth-Provider-Setup.md))

Keduanya memberi autentikasi yang benar sambil tetap menjaga kenyamanan SSO. Opsi OAuth memberi pengalaman single sign-on tanpa risiko keamanan akibat autentikasi yang dimatikan.

### Intinya

Kecuali Anda memiliki arsitektur keamanan yang sangat spesifik, dipahami dengan baik, dan punya isolasi jaringan yang kuat, biarkan login password tetap aktif dan gunakan OAuth untuk kenyamanan.
