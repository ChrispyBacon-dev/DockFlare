# Utilitas CLI DockFlare

## Cleanup Duplicate Policies

DockFlare kini menyertakan utilitas CLI untuk mendeteksi dan menghapus reusable policy duplikat di akun Cloudflare Anda.

### Masalah

Saat menjalankan beberapa instance DockFlare atau ketika terjadi drift pada `state.json`, Cloudflare bisa berisi policy dengan nama yang sama. Utilitas ini akan mengonsolidasikannya dengan mempertahankan policy tertua dan menghapus duplikat yang lebih baru.

### Penggunaan

#### Preview (Dry Run) - Langkah Awal yang Direkomendasikan

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --dry-run
```

Perintah ini akan:
- memindai semua reusable policy di akun Cloudflare Anda
- mengidentifikasi policy dengan nama ganda
- menunjukkan policy mana yang akan dihapus
- menunjukkan policy ID mana yang akan dipertahankan
- menunjukkan update `state.json` yang akan dilakukan
- **tidak membuat perubahan apa pun**

#### Eksekusi Cleanup

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --apply
```

Perintah ini akan:
- menghapus semua policy duplikat sambil mempertahankan yang tertua
- memperbarui `state.json` agar mereferensikan policy ID yang benar
- **benar-benar membuat perubahan pada akun Cloudflare Anda**

### Apa yang Dilakukan

1. Mengambil semua reusable policy dari akun Cloudflare
2. Mengelompokkan policy berdasarkan nama
3. Mengurutkan berdasarkan tanggal pembuatan dan mempertahankan yang tertua
4. Memeriksa Access Application yang memakai policy duplikat
5. Memperbarui application yang terdampak lalu menghapus policy duplikat
6. Memperbarui `state.json` agar semua access group menunjuk ke policy ID yang benar

### Fitur Keamanan

- **Dry run sebagai default**
- **Mempertahankan policy tertua**
- **Perlindungan Access Application**
- **Memperbarui `state.json` secara otomatis**
- **Logging yang detail**

### Kapan Dipakai

- Setelah menemukan system policy duplikat
- Setelah menjalankan banyak instance DockFlare
- Sebelum upgrade besar
- Saat troubleshooting masalah terkait policy

### Catatan

- Utilitas ini membutuhkan kredensial Cloudflare yang valid
- Operasinya berlaku pada **semua reusable policy** di akun Anda
- Jalankan selalu dengan `--dry-run` terlebih dahulu
- Penghapusan bersifat permanen
