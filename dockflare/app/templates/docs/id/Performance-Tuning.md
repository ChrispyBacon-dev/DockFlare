# Tuning Performa

Untuk sebagian besar pengguna, pengaturan default DockFlare sudah memberikan keseimbangan yang baik antara performa dan penggunaan resource. Namun, pada environment yang sangat besar atau sangat dinamis, Anda mungkin mendapat manfaat dari penyesuaian beberapa parameter performa lanjutan.

Pengaturan ini dikonfigurasi melalui environment variable di `docker-compose.yml`.

---

## `CLEANUP_INTERVAL_SECONDS`

Variabel ini mengontrol seberapa sering background task DockFlare dijalankan untuk membersihkan resource yang sudah kedaluwarsa, seperti rule dari container yang sudah berhenti dan grace period-nya sudah habis.

*   **Default:** `60` detik
*   **Deskripsi:** interval yang lebih pendek membuat resource usang dibersihkan lebih cepat dari konfigurasi Cloudflare. Interval yang lebih panjang mengurangi frekuensi pengecekan sehingga sedikit menurunkan penggunaan resource.
*   **Kapan perlu di-tune:** jika environment Anda sangat dinamis dengan banyak container berumur pendek dan Anda ingin cleanup hampir seketika.

```yaml
environment:
  - CLEANUP_INTERVAL_SECONDS=30
```

---

## `MAX_CONCURRENT_DNS_OPS`

Variabel ini menetapkan jumlah maksimum operasi DNS yang berjalan bersamaan.

*   **Default:** `3`
*   **Deskripsi:** ini adalah kontrol tuning langsung untuk environment dengan jumlah service yang besar. Saat DockFlare baru start atau saat banyak container dijalankan bersamaan, pengaturan ini membatasi jumlah request paralel ke Cloudflare API untuk perubahan DNS.
*   **Kapan perlu di-tune:** jika Anda mengelola ratusan service dan startup awal atau deployment massal terasa lambat saat membuat DNS record.

```yaml
environment:
  - MAX_CONCURRENT_DNS_OPS=5
```

---

## `RECONCILIATION_BATCH_SIZE`

Ini mengontrol ukuran batch untuk berbagai background reconciliation task.

*   **Default:** `3`
*   **Deskripsi:** beberapa task latar belakang di DockFlare memproses item dalam batch agar sistem dan Cloudflare API tidak kewalahan.
*   **Kapan perlu di-tune:** ini pengaturan sangat lanjutan. Untuk sebagian besar pengguna, nilai default tidak perlu diubah.

```yaml
environment:
  - RECONCILIATION_BATCH_SIZE=5
```

---

## `SCAN_ALL_NETWORKS`

Variabel ini mengubah cara DockFlare menemukan alamat IP container.

*   **Default:** `false`
*   **Deskripsi:** secara default, DockFlare mengharapkan container target berada pada jaringan Docker yang sama. Jika `SCAN_ALL_NETWORKS=true`, DockFlare akan memeriksa semua jaringan yang ditempeli container untuk menemukan network yang dibagi bersama.
*   **Kapan perlu di-tune:** hanya aktifkan jika Anda punya setup jaringan Docker yang kompleks dan application container tidak berada di jaringan yang sama dengan DockFlare.

```yaml
environment:
  - SCAN_ALL_NETWORKS=true
```
