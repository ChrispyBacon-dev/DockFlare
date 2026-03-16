# Masalah Umum

Halaman ini mencantumkan beberapa masalah umum yang mungkin ditemui pengguna beserta cara mengatasinya.

---

### Masalah: Container DockFlare gagal start atau terus restart

**Solusi:**
1. Cek log Docker:
   ```bash
   docker logs dockflare
   ```
2. Cari pesan error. Penyebab umum:
   *   file `docker-compose.yml` tidak valid
   *   masalah pada Docker daemon
   *   masalah konektivitas atau permission pada `docker-socket-proxy` atau pengaturan `DOCKER_HOST`

---

### Masalah: DNS record tidak dibuat di Cloudflare

**Solusi:**
1. Cek log DockFlare untuk error terkait Cloudflare API
2. Verifikasi API token punya permission:
   *   `Zone:DNS:Edit`
   *   `Zone:Zone:Read`
3. Verifikasi konfigurasi zone:
   *   pastikan **Zone ID** benar
   *   jika memakai `dockflare.zonename`, pastikan nama zone ditulis dengan tepat

---

### Masalah: Access Policy tidak diterapkan ke layanan

**Solusi:**
1. Pastikan API token punya `Account:Access: Apps and Policies:Edit`
2. Cek apakah rule memiliki status **UI Override**
3. Pastikan ID pada `dockflare.access.group` persis sama dengan ID Access Group di halaman **Access Policies**
4. Cek dashboard Cloudflare Zero Trust pada **Access -> Applications**

---

### Masalah: Muncul error `ERR_TOO_MANY_REDIRECTS`

**Solusi:**
Masalah ini hampir selalu terjadi karena konfigurasi SSL/TLS yang salah antara origin service dan Cloudflare.

1. Pastikan mode SSL/TLS di Cloudflare diset ke **Full (Strict)**
2. Hindari redirect ganda
3. Gunakan `https://` pada `dockflare.service` bila backend mendukung HTTPS

---

### Masalah: Service di balik Traefik/Proxmox hanya berfungsi jika "Match SNI to Host" diaktifkan

**Solusi:**
1. Edit manual rule di DockFlare dan aktifkan **Match SNI to Host**
2. Simpan rule dan verifikasi route di Cloudflare Zero Trust
3. Jika perlu mempertahankan field route di sisi Cloudflare yang tidak dimodelkan DockFlare, aktifkan **Preserve Unmanaged Cloudflare Ingress Fields**

---

### Masalah: Container `cloudflared-agent` gagal start dengan error "stale network"

**Solusi:**
1. Restart DockFlare:
   ```bash
   docker compose restart dockflare
   ```
2. Saat startup, DockFlare akan memeriksa kesehatan agent dan otomatis membuat ulang container agent yang rusak bila menemukan masalah ini.
