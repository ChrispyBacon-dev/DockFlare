# Zone Default Policies - Perlindungan Wildcard

## Gambaran Umum

Zone Default Policies adalah fitur best practice keamanan yang menggunakan wildcard application Cloudflare Access seperti `*.domain.com` untuk melindungi semua subdomain dalam sebuah DNS zone secara otomatis.

## Masalah yang Diselesaikan

Tanpa zone default policies:
- Layanan yang terlupa bisa terbuka ke publik
- Subdomain baru tidak punya perlindungan sampai dikonfigurasi manual
- Typo pada konfigurasi hostname bisa melewati access control
- Dokumentasi yang tidak sinkron dapat menimbulkan celah keamanan

## Cara Kerjanya

### Prioritas Policy

Cloudflare mengevaluasi Access Policy dalam urutan berikut:

1. **Exact hostname match** seperti `app.example.com`
2. **Wildcard match** seperti `*.example.com`
3. **No match** = akses publik tanpa Access App

### Implementasi di DockFlare

Bagian **Zone Default Policies** di DockFlare:
- Menampilkan semua Cloudflare DNS zone Anda
- Menunjukkan status perlindungan dengan badge visual
- Memungkinkan pembuatan policy `*.zone.com` dengan satu klik
- Membiarkan Anda memilih Access Group yang akan melindungi zone tersebut

## Panduan Setup

### Langkah 1: Tinjau Zone Anda

1. Buka halaman **Access Policies**
2. Scroll ke **Zone Default Policies (*.tld Wildcards)**
3. Tinjau status perlindungan:
   - 🛡️ **Hijau "Protected"** - zone sudah memiliki wildcard policy
   - ⚠️ **Kuning "Not Protected"** - zone masih rentan

### Langkah 2: Buat Zone Policy

Untuk tiap zone yang belum terlindungi:

1. Klik tombol **Create Policy**
2. Modal akan menampilkan hostname `*.zone-name.com`
3. Pilih Access Policy yang sesuai:
   - **Public zones** → `public-default-bypass`
   - **Internal zones** → policy autentikasi
   - **Mixed zones** → policy yang paling ketat
4. Klik **Create Zone Policy**

### Langkah 3: Verifikasi di Cloudflare

1. Buka dashboard Cloudflare Zero Trust
2. Masuk ke **Access → Applications**
3. Cari aplikasi bernama `Zone Default: *.domain.com`
4. Verifikasi policy-nya sudah benar

## Rekomendasi Keamanan

### Environment Produksi

✅ **Selalu aktifkan zone default policies**
- Mencegah eksposur yang tidak disengaja
- Menangkap kesalahan konfigurasi
- Melindungi dari serangan penemuan subdomain

### Strategi Memilih Policy

- **Domain konten publik** seperti blog dan marketing: `public-default-bypass`
- **Domain tool internal**: autentikasi email atau domain
- **Domain dengan data sensitif**: autentikasi dengan MFA
- **Domain development**: kunci dengan policy paling ketat

### Monitoring

Tinjau secara berkala:
- Zone mana yang sudah terlindungi di halaman **Access Policies**
- Log Access Application di Cloudflare
- Daftar subdomain aktif dibanding policy yang sudah dikonfigurasi

## Troubleshooting

### Error "Policy already exists"

Access Application `*.domain.com` sudah ada. Bisa jadi:
- Dibuat manual di Cloudflare
- Dibuat sebelumnya oleh DockFlare
- Dibuat tool lain

**Solusi:** Kelola langsung dari Cloudflare atau hapus lalu buat ulang melalui DockFlare.

### Service masih bisa diakses tanpa autentikasi

Periksa prioritas policy:
1. Pastikan service punya specific hostname policy
2. Pastikan wildcard zone sudah ada dan dikonfigurasi dengan benar
3. Jika service memang harus tetap publik meski zone dilindungi, tambahkan label `dockflare.access.group=public-default-bypass`

### Membypass Perlindungan Zone untuk Service Publik

Jika Anda memiliki zone-level authentication policy tetapi ada service tertentu yang harus tetap publik:

1. Tambahkan label bypass ke container:
   ```yaml
   labels:
     - "dockflare.access.group=public-default-bypass"
   ```
2. Ini akan membuat exact hostname Access Application dengan keputusan bypass
3. Exact hostname policy akan meng-override wildcard policy
4. Service menjadi dapat diakses publik sementara zone tetap terlindungi
5. Periksa Cloudflare Access logs untuk melihat urutan evaluasi policy
6. Pastikan DNS record menunjuk ke tunnel yang benar

### Zone tidak muncul di daftar

Kemungkinan penyebab:
- DNS zone tidak ada di akun Cloudflare Anda
- API token tidak memiliki permission `Zone:Zone:Read`
- Zone sedang dipause atau dihapus

**Solusi:** Pastikan zone ada di dashboard Cloudflare dan API token punya permission yang benar.

## Praktik Terbaik

1. **Buat zone policy terlebih dahulu** - sebelum menambahkan layanan
2. **Gunakan autentikasi untuk zone internal** - jangan gunakan bypass
3. **Dokumentasikan pengecualian** - jika ada zone yang memang tidak perlu dilindungi
4. **Audit rutin** - tinjau status perlindungan zone setiap bulan
5. **Uji sebelum produksi** - pastikan wildcard policy tidak merusak layanan yang ada
6. **Prinsip least privilege** - gunakan policy paling ketat yang tetap memungkinkan akses yang sah

## Contoh Konfigurasi

### Public Blog Zone
```
Zone: blog.example.com
Policy: public-default-bypass
Hasil: semua subdomain dapat diakses publik (*.blog.example.com)
```

### Internal Tools Zone
```
Zone: internal.company.com
Policy: Company Email Authentication
Hasil: semua subdomain mewajibkan email @company.com (*.internal.company.com)
```

### Mixed Development Zone
```
Zone: dev.company.com
Policy: Developer Team Authentication
Hasil: semua layanan dev terlindungi secara default (*.dev.company.com)
Specific override: public-demo.dev.company.com → public-default-bypass
```

## Memahami Prioritas Policy

### Skenario 1: Specific Policy Meng-override Wildcard

**Setup:**
- Zone policy: `*.example.com` → wajib autentikasi
- Specific policy: `blog.example.com` → `public-default-bypass`

**Hasil:**
- `blog.example.com` → publik
- `api.example.com` → wajib autentikasi
- `forgotten.example.com` → wajib autentikasi

### Skenario 2: Wildcard sebagai Jaring Pengaman

**Setup:**
- Zone policy: `*.internal.company.com` → wajib email `@company.com`
- Tidak ada specific policy untuk `test-server.internal.company.com`

**Hasil:**
- `test-server.internal.company.com` → wajib autentikasi
- Walaupun Anda lupa mengonfigurasinya, zone policy tetap melindunginya

### Skenario 3: Tidak Ada Perlindungan

**Setup:**
- Tidak ada zone policy untuk `*.risky-domain.com`
- Specific policy: `app.risky-domain.com` → Authentication

**Hasil:**
- `app.risky-domain.com` → wajib autentikasi
- `forgotten.risky-domain.com` → ⚠️ **PUBLIK**

## Integrasi dengan Label DockFlare

### Menggunakan Label `default_tld`

Label `dockflare.access.policy=default_tld` memberi tahu DockFlare untuk memakai wildcard policy milik zone:

```yaml
services:
  my-service:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=new-app.internal.company.com"
      - "dockflare.service=http://my-service:80"
      - "dockflare.access.policy=default_tld"
```

**Perilaku:**
- Jika `*.internal.company.com` ada → service mewarisi policy itu
- Jika tidak ada zone policy → service akan publik

### Rekomendasi

Daripada mengandalkan label `default_tld`:
1. Buat zone default policy lewat UI
2. Biarkan wildcard policy melindungi semua service secara otomatis
3. Buat specific policy hanya untuk pengecualian
