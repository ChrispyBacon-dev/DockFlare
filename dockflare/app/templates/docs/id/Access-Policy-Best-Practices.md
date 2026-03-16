# Praktik Terbaik & Contoh Access Policy

Fitur keamanan paling kuat di DockFlare adalah **Access Groups**. Fitur ini menyediakan cara yang terpusat, dapat dipakai ulang, dan mudah dirawat untuk mengamankan layanan Anda dengan Cloudflare Zero Trust.

## "Aturan Emas": Gunakan Access Groups

Praktik terbaik yang paling penting adalah **menggunakan Access Groups untuk semua access policy umum Anda**.

Access Groups adalah template policy yang Anda buat di DockFlare Web UI. Alih-alih mendefinisikan aturan kompleks dengan banyak label pada setiap container, Anda membuat policy sekali lalu menerapkannya dengan satu label yang bersih. DockFlare v3.0.3 kini menyinkronkan setiap grup menjadi Cloudflare Access Policy yang reusable sehingga set keputusan yang sama dapat melayani banyak aplikasi.

---

## Cara Membuat dan Menggunakan Access Groups

Membuat Access Group adalah proses sederhana yang sepenuhnya dilakukan di DockFlare UI.

### Langkah 1: Buat Access Group

1. Buka halaman **Access Policies** dari navigasi utama di DockFlare UI.
2. Klik tombol **"Add Access Group"**.
3. Beri grup Anda **ID yang unik dan deskriptif**. ID inilah yang akan dipakai dalam label Docker. Contoh: `admin-users`, `home-network`, `geo-block`.
4. Pilih **Access Mode** dari tab di bagian atas modal:
    *   **Authenticated** mewajibkan pengguna login dan menghasilkan keputusan `allow`.
    *   **Public** memakai keputusan `bypass` agar aplikasi tetap terbuka sambil tetap menghormati filter geo.
5. Isi input yang muncul sesuai mode yang dipilih: email untuk Authenticated dan daftar negara opsional untuk keduanya.
6. Sesuaikan pengaturan opsional seperti durasi sesi, visibilitas App Launcher, dan redirect otomatis ke IdP jika Anda memakai mode Authenticated.
7. Simpan grup. DockFlare menulis definisinya secara lokal dan menyinkronkannya ke Cloudflare sebagai `DockFlare-AccessGroup-<id>`.

### Langkah 2: Terapkan Access Group

Setelah dibuat, ada dua cara untuk menerapkan Access Group ke sebuah layanan:

#### A) Dengan Docker Label (Cara yang Direkomendasikan)

Untuk container baru maupun yang sudah ada, cukup tambahkan label `dockflare.access.group` dengan ID grup yang Anda buat.

```yaml
services:
  grafana:
    image: grafana/grafana
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=monitoring.example.com"
      - "dockflare.service=http://grafana:3000"
      # Terapkan seluruh policy dengan satu label sederhana:
      - "dockflare.access.group=admin-users"
```

Anda juga bisa menerapkan beberapa grup dengan `dockflare.access.groups` memakai daftar ID yang dipisahkan koma:
`dockflare.access.groups=admin-users,home-network`

#### System-Managed Policies

DockFlare menyediakan dua system policy bawaan yang otomatis tersedia:

- **`public-default-bypass`** - akses publik dengan keputusan bypass, cocok untuk layanan yang benar-benar publik
- **`authenticated-default`** - autentikasi default dengan one-time PIN + pembatasan email

System policy ini tidak dapat dihapus dan menjadi fondasi perlindungan zone serta migrasi legacy label.

#### B) Melalui Web UI (Untuk Manual Rule atau Override)

Anda juga bisa menerapkan Access Group ke rule mana pun langsung dari dashboard:
1. Cari ingress rule yang ingin Anda ubah di dashboard utama.
2. Klik tombol **"Manage Rule"**.
3. Di modal edit, pilih Access Group yang diinginkan dari dropdown **"Access Groups"**.
4. Simpan perubahan.

Cara ini cocok untuk menerapkan policy ke rule yang dibuat manual untuk layanan non-Docker, atau untuk sementara meng-override policy yang didefinisikan lewat label Docker.

---

## Contoh Policy

Berikut beberapa konfigurasi policy umum yang bisa Anda buat dalam Access Group.

### Contoh 1: Autentikasi Berdasarkan Email

Ini adalah use case paling umum: hanya mengizinkan pengguna tertentu yang dapat autentikasi melalui Identity Provider yang Anda konfigurasikan, misalnya Google, GitHub, atau one-time PIN yang dikirim lewat email.

*   **Group ID:** `admin-users`
*   **Mode:** *Authenticated*
*   **Allowed emails:** `user1@example.com`, `user2@example.com`
*   **Session duration:** `24h`

DockFlare akan membuat reusable policy dengan keputusan `allow` untuk daftar email tersebut serta aturan `deny` untuk semua pengguna lain. Terapkan grup dengan `dockflare.access.group=admin-users`.

### Contoh 2: Mengizinkan IP Rumah Anda

Policy ini membatasi akses ke jaringan rumah Anda, memungkinkan Anda melewati login saat memakai IP tepercaya sambil tetap mewajibkan autentikasi di luar itu.

1. **Cari Public IP Anda:** Di browser, cari "what is my ip". Public IP Anda akan ditampilkan, misalnya `203.0.113.55`.
2. **Buat Access Group:**
    *   **Group ID:** `home-network`
    *   **Mode:** *Authenticated*
    *   **Allowed emails:** `you@example.com`
    *   **Bypass IPs:** tambahkan `203.0.113.55/32` ke field IP allowlist

DockFlare akan membuat policy yang pertama-tama membypass range IP Anda, lalu mewajibkan email yang ditentukan untuk autentikasi. Semua pengguna lain akan menerima keputusan deny.

### Contoh 3: Geo-Fencing

Policy ini menjaga situs marketing Anda tetap publik sambil membatasi trafik dari wilayah tertentu.

*   **Group ID:** `public-eu`
*   **Mode:** *Public*
*   **Blocked countries:** `RU`, `CN`, `KP`

Reusable policy yang dihasilkan akan memberikan keputusan Cloudflare `bypass` untuk semua orang kecuali negara yang diblokir. Anda bisa menggabungkannya dengan grup lain jika perlu menambahkan lapisan kontrol, misalnya `dockflare.access.groups=public-eu,admin-users`.

---

## Zone Default Policies - Praktik Keamanan Terbaik

### Apa itu Zone Default Policies?

Zone Default Policies adalah wildcard `*.domain.com` Access Application yang melindungi SEMUA subdomain dalam satu DNS zone, termasuk yang belum Anda konfigurasi secara eksplisit.

### Mengapa Ini Penting

**Masalahnya:** Jika Anda lupa menambahkan Access Policy ke sebuah layanan, layanan itu akan terbuka ke publik secara default.

**Solusinya:** Wildcard policy tingkat zone berfungsi sebagai jaring pengaman. Walaupun Anda lupa mengonfigurasi `forgotten-service.yourdomain.com`, policy `*.yourdomain.com` akan menangkapnya.

### Cara Menyiapkannya

1. Buka halaman **Access Policies**
2. Scroll ke bagian **Zone Default Policies (*.tld Wildcards)**
3. Cari zone dengan badge **"Not Protected"** ⚠️
4. Klik **Create Policy**
5. Pilih access group yang sesuai:
   - **Untuk domain publik:** gunakan `public-default-bypass`
   - **Untuk domain internal:** gunakan policy autentikasi
   - **Untuk penggunaan campuran:** gunakan policy yang paling ketat

### Praktik Terbaik

- ✅ **Selalu buat zone policy** untuk domain produksi
- ✅ **Gunakan policy autentikasi** untuk zone internal atau privat
- ✅ **Gunakan public bypass** hanya untuk zone yang benar-benar publik
- ✅ **Tinjau secara berkala** - periksa status perlindungan zone setiap bulan
- ⚠️ **Ingat prioritas** - specific hostname policy akan meng-override wildcard policy

### Urutan Prioritas Policy

Cloudflare mengevaluasi Access Policy dalam urutan berikut:

1. **Exact hostname match** seperti `app.example.com` - prioritas tertinggi
2. **Wildcard match** seperti `*.example.com` - fallback
3. **No match** = akses publik tanpa Access App - default

Artinya, Anda bisa punya zone default policy yang ketat sambil tetap membuat pengecualian khusus untuk layanan tertentu.

---

## Mengelola External Cloudflare Policies

### Memahami Jenis Policy

DockFlare menampilkan tiga jenis policy di halaman Access Policies, masing-masing dengan badge visual:

- **🟦 DockFlare** - policy dibuat dan dikelola oleh DockFlare, prefix `DockFlare-`
- **🟪 External** - policy dibuat di luar DockFlare, baik manual maupun lewat tool lain
- **🟧 System** - system policy yang tidak dapat dihapus, seperti `public-default-bypass` dan `authenticated-default`

### Menyinkronkan External Policies

Secara default, DockFlare hanya mengimpor policy dengan prefix `DockFlare-`. Ini menjaga daftar policy tetap bersih dan fokus pada infrastruktur container Anda.

**Untuk menyinkronkan SEMUA Cloudflare policies** termasuk yang dibuat manual:

1. Set environment variable `SYNC_ALL_CLOUDFLARE_POLICIES=true`
2. Restart DockFlare
3. Klik **"Sync from Cloudflare"** di halaman Access Policies

External policy akan muncul dengan badge ungu **"External"**.

### Mengapa Mengimpor External Policies?

**Kelebihan:**
- Visibilitas penuh atas seluruh setup Cloudflare Access Anda
- Bisa memakai ulang policy yang sudah ada tanpa membuat ulang
- Manajemen terpusat dalam satu antarmuka
- Bisa menerapkan policy apa pun ke layanan mana pun

**Kekurangan:**
- Daftar policy menjadi lebih panjang jika Anda punya banyak policy eksternal
- Ada risiko tidak sengaja mengubah policy yang dipakai layanan non-DockFlare

### Mengorganisasi Policy

**Tips:** ganti nama external policy di Cloudflare agar memakai prefix `DockFlare-`

1. Buka policy di **Cloudflare Zero Trust**
2. Ubah namanya memakai prefix `DockFlare-`, misalnya `DockFlare-LegacyVPN`
3. Klik **"Sync from Cloudflare"** di DockFlare
4. Policy itu sekarang akan muncul sebagai **DockFlare-managed** dengan badge biru

Ini memungkinkan Anda:
- ✅ Mengelompokkan semua policy yang terlihat oleh DockFlare dengan penamaan yang konsisten
- ✅ Memfilter dan mengurutkan policy berdasarkan tipe
- ✅ Membedakan "dikelola oleh DockFlare" dari "hanya terlihat di DockFlare"

### Memfilter Policy

Gunakan dropdown **Filter** untuk melihat tipe policy tertentu:

- **All Policies** - menampilkan semuanya
- **DockFlare-Managed** - hanya policy dengan badge biru
- **External** - hanya policy dengan badge ungu
- **System** - hanya system policy

### Fitur Keamanan

Saat menghapus atau mengedit external policy, DockFlare akan menampilkan peringatan:

> ⚠️ PERINGATAN: Ini adalah policy EKSTERNAL yang tidak dibuat oleh DockFlare.
>
> Mengubah policy ini dapat memengaruhi layanan di luar DockFlare.
>
> Apakah Anda benar-benar yakin?

Ini mencegah perubahan tidak sengaja pada policy yang dikelola tool lain atau konfigurasi manual.

### Praktik Terbaik

1. **Setup default yang direkomendasikan:**
   - Biarkan `SYNC_ALL_CLOUDFLARE_POLICIES=false`
   - Hanya policy yang dikelola DockFlare yang muncul
   - Daftar policy tetap bersih dan fokus

2. **Setup lanjutan:**
   - Aktifkan `SYNC_ALL_CLOUDFLARE_POLICIES=true`
   - Lihat dan kelola SEMUA policy di satu tempat
   - Ganti nama external policy menjadi `DockFlare-` agar lebih rapi

3. **Pendekatan hybrid:**
   - Biarkan sync nonaktif secara default
   - Ubah nama external policy penting menjadi `DockFlare-*` di Cloudflare
   - Policy itu akan otomatis muncul saat sync berikutnya

4. **Konvensi penamaan policy:**
   ```
   DockFlare-AccessGroup-<id>     # Dibuat otomatis oleh access groups
   DockFlare-<custom-name>        # External policy yang Anda ganti nama
   <apa pun selain itu>           # Murni eksternal
   ```
