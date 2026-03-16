# Persistensi State

DockFlare adalah aplikasi yang stateful. DockFlare perlu melacak layanan yang dikelola, UI override, dan detail konfigurasi lain. State ini disimpan ke disk agar konfigurasi Anda tidak hilang saat container DockFlare direstart atau dibuat ulang.

## Cara Penyimpanan State

DockFlare menyimpan state dalam tiga file penting di direktori `/app/data` di dalam container:

1.  `dockflare_config.dat`: file paling kritis. Berisi pengaturan inti dan informasi sensitif dalam format **terenkripsi**, termasuk:
    *   Cloudflare API Token dan Account ID
    *   hash password UI DockFlare
    *   pengaturan inti seperti Tunnel Name dan Zone ID

2.  `agent_keys.dat`: penyimpanan terenkripsi berisi semua agent API key dan metadata-nya

3.  `state.json`: file JSON biasa yang menyimpan state dinamis dari layanan yang dikelola, termasuk:
    *   daftar semua ingress rule yang dikelola DockFlare
    *   UI override pada access policy
    *   semua Access Group yang Anda buat
    *   status `pending deletion` untuk layanan yang dihentikan tetapi masih berada dalam grace period

## Pentingnya Persistent Volume

Karena seluruh konfigurasi disimpan di direktori `/app/data`, maka **sangat penting** untuk memetakan direktori ini ke volume persisten di host Anda.

Jika Anda tidak memakai persistent volume, **semua pengaturan, password UI, dan konfigurasi rule akan hilang** setiap kali container DockFlare dihapus lalu dibuat ulang.

### Konfigurasi Docker Compose yang Direkomendasikan

```yaml
services:
  dockflare:
    # ... pengaturan lain
    volumes:
      - ./dockflare_data:/app/data

volumes:
  dockflare_data:
```

Dengan konfigurasi ini, `dockflare_config.dat`, `agent_keys.dat`, dan `state.json` akan tersimpan di direktori `dockflare_data` pada host Anda.

## Backup dan Restore

DockFlare kini membungkus semua data penting ke dalam satu arsip backup terenkripsi. Cache Redis tidak disertakan karena dapat dibangun ulang dengan aman. Panel **Settings → Backup & Restore** memungkinkan Anda mengunduh `.zip` yang berisi:

* `dockflare_config.dat`
* `dockflare.key`
* `agent_keys.dat`
* `state.json`
* manifest checksum untuk verifikasi integritas

Saat arsip dipulihkan, DockFlare akan membuat ulang file-file tersebut dan memuatnya ke instance yang sedang berjalan. Upload legacy `state.json` tetap didukung, tetapi hanya memulihkan metadata rule. Setelah full archive restore, DockFlare akan merestart container secara otomatis agar konfigurasi terenkripsi langsung dimuat.
