# Backup & Restore

DockFlare 3.0 memperkenalkan arsip backup penuh sehingga Anda bisa memindahkan master ke hardware baru, memulihkan dari kegagalan, atau menyiapkan upgrade tanpa harus menyentuh direktori data mentah.

## Apa Saja yang Disimpan
- `dockflare.key` – kunci Fernet yang membuka semua file terenkripsi
- `dockflare_config.dat` – kredensial Cloudflare terenkripsi, akun UI, dan pengaturan runtime
- `agent_keys.dat` – agent API key terenkripsi beserta metadata audit
- `state.json` – salinan JSON biasa dari rules, agents, dan access groups
- `manifest.json` – checksum dan info versi untuk arsip

Semua file ini dibungkus ke dalam satu `dockflare_backup_YYYYMMDD_HHMMSS.zip`. Simpan ZIP dan hasil ekstraknya bersama; tanpa `dockflare.key`, artefak terenkripsi tidak berguna.

## Membuat Backup
1. Buka **Settings → Backup & Restore** di master UI
2. Klik **Download Backup (.zip)**
3. Simpan arsip di tempat aman. Perlakukan seperti kredensial karena berisi semua yang dibutuhkan untuk mengendalikan akun Cloudflare Anda lewat DockFlare

Backup bisa diambil saat master sedang berjalan. Setiap arsip menyertakan manifest dengan hash SHA-256 sehingga unduhan rusak mudah terdeteksi.

## Restore pada Master yang Sudah Ada
1. Buka **Settings → Backup & Restore**
2. Upload file `.zip` lewat **Restore from Backup**
3. Konfirmasikan peringatan: restore akan menimpa konfigurasi, agent key, dan rules

DockFlare akan menulis ulang file terenkripsi, memuat ulang `state.json`, dan jika perlu menulis restart flag. Beberapa detik kemudian container akan keluar agar Docker bisa menyalakannya kembali dengan konfigurasi baru. UI lalu akan terbuka lagi dengan kredensial yang sudah dipulihkan.

Legacy `state.json` masih diterima untuk partial restore. Jika Anda meng-upload file JSON biasa, hanya rules yang diganti dan konfigurasi terenkripsi tidak ikut dipulihkan.

## Restore Saat Setup Wizard

Instalasi baru kini memiliki tautan **Restore from Backup** sebelum Step 1 pada Pre-Flight wizard.

1. Upload ZIP backup
2. DockFlare akan menulis artefak terenkripsi dan state ke disk
3. Container akan restart otomatis; setelah aktif kembali, masuklah dengan akun admin hasil restore

Ini adalah cara tercepat untuk meng-clone master produksi atau memulihkan instance setelah volume data dibersihkan. Anda tidak perlu menjalankan ulang wizard atau memasukkan ulang kredensial Cloudflare.

## Setelah Restore
- Kunjungi **Settings → Backup & Restore** untuk memastikan timestamp manifest terbaru benar
- Cek **Agents → Overview** untuk memastikan agent yang sudah terdaftar tersambung kembali
- Jalankan reconciliation jika Anda me-restore ke environment berbeda lewat `Actions → Reconcile Now`

Simpan backup offline secara rutin dan padukan dengan version control untuk stack compose Anda agar seluruh deployment bisa dibangun ulang dengan cepat.
