#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# DockFlare Master — Install Script
# https://dockflare.app
#
# Usage (interactive — recommended):
#   bash <(curl -fsSL https://dockflare.app/install.sh)
#
#
# Optional env overrides (non-interactive / pipe mode):
#   DOCKFLARE_PORT    — host port to expose DockFlare UI on     (default: 5000)
#   DOCKFLARE_DIR     — install directory                        (default: $HOME/dockflare)
#   DOCKFLARE_UID     — UID for data volume ownership            (default: 65532)
#   DOCKFLARE_GID     — GID for data volume ownership            (default: 65532)
#   DOCKFLARE_EMAIL   — set to "true" to enable email profile    (default: false)
#   DOCKFLARE_TLD     — base domain e.g. example.com             (required if EMAIL=true)
#   DOCKFLARE_DOMAIN  — DockFlare master domain                  (default: dockflare.$DOCKFLARE_TLD)
#
# Examples:
#   bash <(curl -fsSL https://dockflare.app/install.sh)
#   local run  
#   bash install.sh 
# -----------------------------------------------------------------------------

DOCKFLARE_PORT="${DOCKFLARE_PORT:-5000}"
DOCKFLARE_DIR="${DOCKFLARE_DIR:-$HOME/dockflare}"
DOCKFLARE_UID="${DOCKFLARE_UID:-65532}"
DOCKFLARE_GID="${DOCKFLARE_GID:-65532}"
DOCKFLARE_EMAIL="${DOCKFLARE_EMAIL:-false}"
DOCKFLARE_TLD="${DOCKFLARE_TLD:-}"
DOCKFLARE_DOMAIN="${DOCKFLARE_DOMAIN:-}"

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
BLUE="\033[0;34m"
ORANGE="\033[0;33m"
RESET="\033[0m"

# Detect interactive mode (stdin is a TTY)
if [ -t 0 ]; then
  IS_INTERACTIVE=true
else
  IS_INTERACTIVE=false
fi

banner() {
  # Split each line at position 35: DOCK (blue) | FLARE (orange)
  local lines=(
    "  ██████╗  ██████╗  ██████╗██╗  ██╗███████╗██╗      █████╗ ██████╗ ███████╗"
    "  ██╔══██╗██╔═══██╗██╔════╝██║ ██╔╝██╔════╝██║     ██╔══██╗██╔══██╗██╔════╝"
    "  ██║  ██║██║   ██║██║     █████╔╝ █████╗  ██║     ███████║██████╔╝█████╗  "
    "  ██║  ██║██║   ██║██║     ██╔═██╗ ██╔══╝  ██║     ██╔══██║██╔══██╗██╔══╝  "
    "  ██████╔╝╚██████╔╝╚██████╗██║  ██╗██║     ███████╗██║  ██║██║  ██║███████╗"
    "  ╚═════╝  ╚═════╝  ╚═════╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝"
  )
  echo ""
  for line in "${lines[@]}"; do
    echo -e "${BLUE}${BOLD}${line:0:35}${ORANGE}${line:35}${RESET}"
  done
  echo ""
  echo -e "  ${BOLD}Master Installer${RESET}  ·  https://dockflare.app"
  echo ""
}

info()    { echo -e "  ${GREEN}✔${RESET}  $*"; }
warn()    { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
error()   { echo -e "  ${RED}✖${RESET}  $*" >&2; }
section() { echo ""; echo -e "  ${BOLD}$*${RESET}"; echo "  $(printf '─%.0s' {1..60})"; }

# prompt <var_name> <label> <default>
# Reads user input; falls back to default if empty or non-interactive.
prompt() {
  local var_name="$1"
  local label="$2"
  local default="$3"
  local input=""

  if [ "$IS_INTERACTIVE" = true ]; then
    echo -e "\n  ${CYAN}?${RESET}  ${label}"
    printf "      [default: %s]: " "$default"
    read -r input </dev/tty
  fi

  [ -z "$input" ] && input="$default"
  printf -v "$var_name" '%s' "$input"
}

# prompt_yn <var_name> <label> <default: y|n>
# Sets named variable to "true" or "false".
prompt_yn() {
  local var_name="$1"
  local label="$2"
  local default="${3:-n}"
  local hint input=""

  [ "$default" = "y" ] && hint="Y/n" || hint="y/N"

  if [ "$IS_INTERACTIVE" = true ]; then
    echo -e "\n  ${CYAN}?${RESET}  ${label}"
    printf "      [%s]: " "$hint"
    read -r input </dev/tty
  fi

  [ -z "$input" ] && input="$default"

  case "$input" in
    [Yy]*) printf -v "$var_name" '%s' "true"  ;;
    *)     printf -v "$var_name" '%s' "false" ;;
  esac
}

banner

# Stash original defaults so "start over" can reset to them
DOCKFLARE_DIR_ORIG="$DOCKFLARE_DIR"
DOCKFLARE_PORT_ORIG="$DOCKFLARE_PORT"

# -----------------------------------------------------------------------------
# Interactive configuration
# -----------------------------------------------------------------------------
while true; do

if [ "$IS_INTERACTIVE" = true ]; then
  section "Configuration"
  echo -e "  Press ${BOLD}Enter${RESET} to accept each default."
else
  section "Configuration  (non-interactive — using defaults / env overrides)"
fi

# 1. Install directory
prompt DOCKFLARE_DIR "Where should DockFlare be installed?" "$DOCKFLARE_DIR"

# 2. Port
prompt DOCKFLARE_PORT "Local UI port — DockFlare will be reachable at http://localhost:${DOCKFLARE_PORT} (change if that port is already in use)" "$DOCKFLARE_PORT"

# 3. Email features
EMAIL_ENABLED=false
if [ "$DOCKFLARE_EMAIL" = "true" ]; then
  EMAIL_ENABLED=true
else
  prompt_yn EMAIL_ENABLED "Enable DockFlare Email features? (dockflare-mail-manager + dockflare-webmail)" "n"
fi

if [ "$EMAIL_ENABLED" = "true" ]; then
  # 3a. Base domain
  prompt DOCKFLARE_TLD "Enter your base domain (e.g. example.com):" "${DOCKFLARE_TLD:-}"

  if [ -z "$DOCKFLARE_TLD" ]; then
    error "A base domain is required when Email features are enabled."
    exit 1
  fi

  # 3b. DockFlare master domain
  _default_domain="dockflare.${DOCKFLARE_TLD}"
  prompt DOCKFLARE_DOMAIN "DockFlare master domain?" "${DOCKFLARE_DOMAIN:-$_default_domain}"

  # 3c. Webmail domain
  _default_mail="mail.${DOCKFLARE_TLD}"
  prompt MAIL_DOMAIN "Webmail domain?" "${_default_mail}"

  echo ""
  info "Base domain:         ${DOCKFLARE_TLD}"
  info "DockFlare domain:    ${DOCKFLARE_DOMAIN}"
  info "Webmail domain:      ${MAIL_DOMAIN}"
else
  # 4. Cloudflare Tunnel self-expose for DockFlare (email disabled path)
  TUNNEL_ENABLED=false
  prompt_yn TUNNEL_ENABLED "Expose DockFlare via a Cloudflare Tunnel? (sets up dockflare labels)" "n"

  if [ "$TUNNEL_ENABLED" = "true" ]; then
    prompt DOCKFLARE_DOMAIN "DockFlare tunnel domain? (e.g. dockflare.example.com)" "${DOCKFLARE_DOMAIN:-}"

    if [ -z "$DOCKFLARE_DOMAIN" ]; then
      error "A domain is required to set up the Cloudflare Tunnel label."
      exit 1
    fi
  else
    # Placeholders kept in compose so the user can manually fill them in later
    DOCKFLARE_DOMAIN="dockflare.TLD"
  fi

  MAIL_DOMAIN="mail.dockflare.TLD"
fi

echo ""
info "Install directory:   ${DOCKFLARE_DIR}"
info "UI port:             ${DOCKFLARE_PORT}"
info "Email profile:       ${EMAIL_ENABLED}"
if [ "$EMAIL_ENABLED" = "false" ]; then
  if [ "${TUNNEL_ENABLED:-false}" = "true" ]; then
    info "Tunnel domain:       ${DOCKFLARE_DOMAIN}"
  else
    info "Cloudflare Tunnel:   disabled (labels left as comments)"
  fi
fi

# Summary confirmation — skip loop in non-interactive mode
CONFIG_OK=true
prompt_yn CONFIG_OK "Does this look correct? (No = start over)" "y"
[ "$CONFIG_OK" = "true" ] && break

echo ""
warn "Starting over — your answers have been cleared."
DOCKFLARE_DIR="${DOCKFLARE_DIR_ORIG}"
DOCKFLARE_PORT="${DOCKFLARE_PORT_ORIG}"
DOCKFLARE_TLD=""
DOCKFLARE_DOMAIN=""

done

# -----------------------------------------------------------------------------
# Preflight checks
# -----------------------------------------------------------------------------
section "Checking prerequisites"

if ! command -v docker &>/dev/null; then
  error "Docker is not installed. Please install Docker first: https://docs.docker.com/get-docker/"
  exit 1
fi
info "Docker found: $(docker --version)"

COMPOSE_CMD=""
if docker compose version &>/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose &>/dev/null; then
  COMPOSE_CMD="docker-compose"
else
  error "Docker Compose (v2) is not available. Please install it: https://docs.docker.com/compose/install/"
  exit 1
fi
info "Docker Compose found: $($COMPOSE_CMD version --short 2>/dev/null || $COMPOSE_CMD version)"

if ! docker info &>/dev/null; then
  error "Docker daemon is not running or current user lacks permissions."
  error "Try: sudo usermod -aG docker \$USER  then log out and back in."
  exit 1
fi
info "Docker daemon is running"

# -----------------------------------------------------------------------------
# Install directory
# -----------------------------------------------------------------------------
section "Setting up install directory"

if [ -d "$DOCKFLARE_DIR" ]; then
  info "Directory exists: $DOCKFLARE_DIR"
  if [ -f "$DOCKFLARE_DIR/docker-compose.yml" ]; then
    warn "Existing docker-compose.yml found at ${DOCKFLARE_DIR}/docker-compose.yml"
    echo ""
    echo -e "  How would you like to proceed?"
    echo -e "  ${BOLD}  1)${RESET} Overwrite the existing file"
    echo -e "  ${BOLD}  2)${RESET} Rename it (timestamped backup) and continue"
    echo -e "  ${BOLD}  3)${RESET} Abort — exit so you can review the file manually"
    echo ""

    COMPOSE_ACTION=""
    if [ "$IS_INTERACTIVE" = true ]; then
      printf "      [1/2/3, default: 1]: "
      read -r COMPOSE_ACTION </dev/tty
    fi
    [ -z "$COMPOSE_ACTION" ] && COMPOSE_ACTION="1"

    case "$COMPOSE_ACTION" in
      2)
        _backup="${DOCKFLARE_DIR}/docker-compose.yml.$(date +%Y-%m-%d_%H%M%S)"
        mv "$DOCKFLARE_DIR/docker-compose.yml" "$_backup"
        info "Existing file renamed to: $_backup"
        ;;
      3)
        echo ""
        echo -e "  ${YELLOW}Aborted.${RESET} No changes made."
        echo -e "  Review your file at: ${DOCKFLARE_DIR}/docker-compose.yml"
        echo ""
        exit 0
        ;;
      *)
        info "Existing file will be overwritten."
        ;;
    esac
  fi
else
  mkdir -p "$DOCKFLARE_DIR"
  info "Created directory: $DOCKFLARE_DIR"
fi

# -----------------------------------------------------------------------------
# Docker network
# -----------------------------------------------------------------------------
section "Preparing Docker network"

if docker network inspect cloudflare-net &>/dev/null 2>&1; then
  info "Network 'cloudflare-net' already exists"
else
  docker network create cloudflare-net
  info "Created network: cloudflare-net"
fi

# -----------------------------------------------------------------------------
# Build compose fragments based on configuration
# -----------------------------------------------------------------------------

# Self-expose labels block for the dockflare service.
# The entire labels: key is included or fully commented out to avoid YAML null-mapping errors.
#   - Email enabled OR tunnel enabled → labels: uncommented with real domain
#   - Neither                         → entire block commented out (safe placeholder for later)
if [ "$EMAIL_ENABLED" = "true" ] || [ "${TUNNEL_ENABLED:-false}" = "true" ]; then
  LABELS_BLOCK="\
    labels:
      - dockflare.enable=true
      - dockflare.hostname=${DOCKFLARE_DOMAIN}
      - dockflare.service=http://dockflare:5000
      #- dockflare.access.group=YOUR-ACCESS-GROUP-ID"
else
  LABELS_BLOCK="\
    # -- Cloudflare Tunnel labels (via DockFlare) OPTIONAL --
    # Uncomment and replace dockflare.TLD with your domain to expose DockFlare via its own tunnel:
    #labels:
    #  - dockflare.enable=true
    #  - dockflare.hostname=dockflare.TLD
    #  - dockflare.service=http://dockflare:5000
    #  - dockflare.access.group=YOUR-ACCESS-GROUP-ID"
fi

# Webmail label comment — only needed when placeholders are still in place
if [ "$EMAIL_ENABLED" = "true" ]; then
  WEBMAIL_LABEL_NOTE=""
else
  WEBMAIL_LABEL_NOTE="      # Replace dockflare.TLD / mail.dockflare.TLD with your actual domain"$'\n'
fi

# -----------------------------------------------------------------------------
# Write docker-compose.yml
# -----------------------------------------------------------------------------
section "Writing docker-compose.yml"

cat > "$DOCKFLARE_DIR/docker-compose.yml" <<COMPOSE
version: '3.8'

services:

  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:v0.4.1
    container_name: docker-socket-proxy
    restart: unless-stopped
    logging:
      driver: "none"
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
      - CONTAINERS=1
      - EVENTS=1
      - NETWORKS=1
      - IMAGES=1
      - POST=1
      - PING=1
      - INFO=1
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal

  dockflare-init:
    image: alpine:3.20
    command: ["sh", "-c", "chown -R ${DOCKFLARE_UID}:${DOCKFLARE_GID} /app/data"]
    volumes:
      - dockflare_data:/app/data
    networks:
      - dockflare-internal
    restart: "no"

  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    ports:
      - "${DOCKFLARE_PORT}:5000" # Optional: comment out once exposed via Cloudflare Tunnel with an Access Policy to restrict access to tunnel-only
${LABELS_BLOCK}
    volumes:
      - dockflare_data:/app/data
    environment:
      - REDIS_URL=redis://redis:6379/0
      - REDIS_DB_INDEX=0
      - DOCKER_HOST=tcp://docker-socket-proxy:2375
      #- LOG_LEVEL=DEBUG
    depends_on:
      docker-socket-proxy:
        condition: service_started
      dockflare-init:
        condition: service_completed_successfully
      redis:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

  redis:
    image: redis:7-alpine
    container_name: dockflare-redis
    restart: unless-stopped
    command: ["redis-server", "--save", "", "--appendonly", "no"]
    logging:
      driver: "none"
    volumes:
      - dockflare_redis:/data
    networks:
      - dockflare-internal

  dockflare-mail-manager:
    image: alplat/dockflare-mail-manager:stable
    container_name: dockflare-mail-manager
    restart: unless-stopped
    profiles: ["email"]
    environment:
      - DOCKFLARE_MASTER_URL=http://dockflare:5000
      - MAIL_DATA_PATH=/data
    volumes:
      - mail_data:/data
    depends_on:
      dockflare:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

  dockflare-webmail:
    image: alplat/dockflare-webmail:stable
    container_name: dockflare-webmail
    restart: unless-stopped
    profiles: ["email"]
    environment:
      - DOCKFLARE_MASTER_URL=https://${DOCKFLARE_DOMAIN}
    labels:
${WEBMAIL_LABEL_NOTE}      - dockflare.enable=true
      - dockflare.hostname=${MAIL_DOMAIN}
      - dockflare.service=http://dockflare-webmail:80
    depends_on:
      dockflare-mail-manager:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  dockflare_data:
  dockflare_redis:
  mail_data:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
COMPOSE

info "docker-compose.yml written to $DOCKFLARE_DIR"
echo ""
echo -e "  ${CYAN}Review:${RESET}  ${DOCKFLARE_DIR}/docker-compose.yml"

SHOW_COMPOSE=false
prompt_yn SHOW_COMPOSE "Show the generated docker-compose.yml?" "n"
if [ "$SHOW_COMPOSE" = "true" ]; then
  echo ""
  echo -e "  ${BOLD}$(printf '─%.0s' {1..60})${RESET}"
  cat "$DOCKFLARE_DIR/docker-compose.yml"
  echo -e "  ${BOLD}$(printf '─%.0s' {1..60})${RESET}"
  echo ""
fi

# -----------------------------------------------------------------------------
# Pull images & start
# -----------------------------------------------------------------------------
PROFILE_FLAGS=""
if [ "$EMAIL_ENABLED" = "true" ]; then
  PROFILE_FLAGS="--profile email"
fi

START_NOW=true
prompt_yn START_NOW "Pull images and start DockFlare now?" "y"

if [ "$START_NOW" = "false" ]; then
  echo ""
  echo -e "  ${YELLOW}Skipped. To start manually:${RESET}"
  if [ "$EMAIL_ENABLED" = "true" ]; then
    echo -e "    cd ${DOCKFLARE_DIR} && ${COMPOSE_CMD} --profile email up -d"
  else
    echo -e "    cd ${DOCKFLARE_DIR} && ${COMPOSE_CMD} up -d"
  fi
  echo ""
  echo -e "  ${YELLOW}${BOLD}Security recommendation:${RESET}"
  echo -e "  Once DockFlare is fully configured, it is recommended to remove the exposed port"
  echo -e "  and restrict access exclusively via a Cloudflare Tunnel with an Access Policy."
  echo -e "  See the ${BOLD}ports:${RESET} comment in ${DOCKFLARE_DIR}/docker-compose.yml for details."
  echo ""
  echo -e "  ${CYAN}Docs:${RESET}  https://dockflare.app/docs"
  echo ""
  exit 0
fi

section "Pulling images"
$COMPOSE_CMD -f "$DOCKFLARE_DIR/docker-compose.yml" $PROFILE_FLAGS pull

section "Starting DockFlare"
$COMPOSE_CMD -f "$DOCKFLARE_DIR/docker-compose.yml" $PROFILE_FLAGS up -d

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo -e "  ${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "  ${GREEN}${BOLD}  DockFlare is running!${RESET}"
echo -e "  ${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "  ${BOLD}Local access:${RESET}    http://localhost:${DOCKFLARE_PORT}"
echo -e "  ${BOLD}Network access:${RESET}  http://${LOCAL_IP}:${DOCKFLARE_PORT}"
echo -e "  ${BOLD}Install path:${RESET}    ${DOCKFLARE_DIR}"
echo ""
echo -e "  ${YELLOW}${BOLD}Next steps:${RESET}"
echo -e "  ${YELLOW}1.${RESET} Open the URL above and complete the setup wizard"
echo -e "  ${YELLOW}2.${RESET} Add your Cloudflare API credentials"
echo -e "  ${YELLOW}3.${RESET} DockFlare will start managing your tunnels automatically"
if [ "$EMAIL_ENABLED" = "true" ]; then
  echo ""
  echo -e "  ${YELLOW}${BOLD}Email profile:${RESET}"
  echo -e "  ${YELLOW}4.${RESET} DockFlare will be reachable at https://${DOCKFLARE_DOMAIN}"
  echo -e "  ${YELLOW}5.${RESET} Webmail will be reachable at  https://${MAIL_DOMAIN}"
  echo -e "  ${YELLOW}6.${RESET} Restart if needed: cd ${DOCKFLARE_DIR} && docker compose --profile email up -d"
fi
echo ""
echo -e "  ${YELLOW}${BOLD}Security recommendation:${RESET}"
echo -e "  Once DockFlare is fully configured, it is recommended to remove the exposed local port"
echo -e "  and restrict access exclusively via a Cloudflare Tunnel with an CloudFlare Zero Trust Access Policy."
echo -e "  See the ${BOLD}ports:${RESET} comment in ${DOCKFLARE_DIR}/docker-compose.yml for details."
echo ""
echo -e "  ${CYAN}Docs:${RESET}  https://dockflare.app/docs"
echo ""
