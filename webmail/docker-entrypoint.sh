#!/bin/sh
MASTER_URL="${DOCKFLARE_MASTER_URL:-}"
INTERNAL_URL="${DOCKFLARE_INTERNAL_URL:-http://dockflare:5000}"
echo "{\"masterUrl\": \"${MASTER_URL}\"}" > /usr/share/nginx/html/config.json

cat > /etc/nginx/conf.d/default.conf << EOF
server {
    listen 80;
    server_name _;
    client_max_body_size 25m;
    add_header Content-Security-Policy "default-src 'self'; img-src 'self' data: https: blob:; style-src 'self' 'unsafe-inline'; script-src 'self' https://static.cloudflareinsights.com; worker-src 'self'; connect-src 'self' https://fcm.googleapis.com https://*.googleapis.com https://cloudflareinsights.com;";

    location /api/ {
        proxy_pass http://dockflare-mail-manager:8025/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location = /email/auth/login {
        proxy_pass ${INTERNAL_URL}/email/auth/login;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header CF-Connecting-IP \$http_cf_connecting_ip;
    }

    location = /sw.js {
        root /usr/share/nginx/html;
        add_header Cache-Control "no-cache";
        add_header Service-Worker-Allowed "/";
    }

    location = /manifest.webmanifest {
        root /usr/share/nginx/html;
        add_header Cache-Control "no-cache";
        types { application/manifest+json webmanifest; }
    }

    location = /config.json {
        root /usr/share/nginx/html;
        add_header Cache-Control "no-store";
    }

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    location ~* \\.(?:ico|css|js|gif|jpe?g|png|woff2?|eot|ttf|svg|mp4|webm)$ {
        root /usr/share/nginx/html;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

exec nginx -g "daemon off;"
