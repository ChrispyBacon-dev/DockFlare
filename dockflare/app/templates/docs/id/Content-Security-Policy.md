# Content Security Policy (CSP)

## Apa itu Content Security Policy?

Content Security Policy atau CSP adalah standar keamanan web yang membantu mencegah jenis serangan tertentu, terutama Cross-Site Scripting (XSS) dan serangan injeksi data. CSP bekerja dengan memberi tahu browser sumber konten mana yang tepercaya dan boleh dimuat pada sebuah halaman web.

## CSP di DockFlare

DockFlare memiliki antarmuka web sendiri. Untuk melindungi antarmuka itu dan menjaga keamanannya, DockFlare menerapkan Content Security Policy yang ketat pada UI-nya.

Ini adalah fitur keamanan internal yang penting untuk melindungi Anda sebagai administrator dari potensi kerentanan berbasis browser saat memakai dashboard DockFlare.

## Cakupan CSP

Penting untuk dipahami bahwa CSP milik DockFlare **hanya berlaku untuk DockFlare Web UI itu sendiri**.

CSP ini **tidak** memengaruhi, mengubah, atau menambahkan header CSP ke trafik yang sedang diproksikan melalui Cloudflare Tunnel menuju aplikasi Anda sendiri. Jika Anda ingin menerapkan CSP pada aplikasi milik Anda, konfigurasikan itu di aplikasi atau web server Anda sendiri.

## Konfigurasi

CSP DockFlare adalah bagian integral dari posture keamanannya dan **tidak dapat dikonfigurasi oleh pengguna**. Policy ini dirancang seketat mungkin sambil tetap memastikan UI berfungsi dengan benar.

Jika Anda ingin mempelajari CSP lebih lanjut, lihat dokumentasi [MDN Web Docs on CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP).
