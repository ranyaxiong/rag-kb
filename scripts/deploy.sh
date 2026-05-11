#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_APP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

APP_DIR="${APP_DIR:-$DEFAULT_APP_DIR}"
REPO_URL="${REPO_URL:-}"
DOMAIN="${DOMAIN:-}"
EMAIL="${EMAIL:-}"
API_KEY="${API_KEY:-}"
EMBEDDING_API_KEY="${EMBEDDING_API_KEY:-}"
JWT_SECRET="${JWT_SECRET:-}"
ADMIN_PASSWORD_HASH="${ADMIN_PASSWORD_HASH:-}"

if [ "${EUID}" -ne 0 ]; then
  echo "ERROR: run as root. Use sudo -i, then bash scripts/deploy.sh"
  exit 1
fi

for v in DOMAIN EMAIL; do
  if [ -z "${!v:-}" ]; then
    echo "ERROR: missing environment variable: $v"
    exit 1
  fi
done

install_docker_if_needed() {
  apt-get update
  apt-get install -y ca-certificates curl gnupg git openssl cron

  if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    . /etc/os-release
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list

    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  fi

  systemctl enable --now docker
  systemctl enable --now cron
  docker compose version >/dev/null
}

ensure_directory() {
  local path="$1"
  if [ -e "$path" ] && [ ! -d "$path" ]; then
    echo "ERROR: path exists but is not a directory: $path"
    exit 1
  fi
  mkdir -p "$path"
}

write_secret() {
  local path="$1"
  local value="$2"
  local label="$3"

  if [ -n "$value" ]; then
    printf '%s' "$value" > "$path"
    chmod 600 "$path"
    echo "Wrote $label: $path"
  fi
}

require_secret_file() {
  local path="$1"
  local label="$2"

  if [ ! -s "$path" ]; then
    echo "ERROR: missing $label: $path"
    exit 1
  fi
}

set_env_value() {
  local file="$1"
  local key="$2"
  local value="$3"

  if grep -q "^${key}=" "$file"; then
    sed -i "s|^${key}=.*|${key}=${value}|g" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" >> "$file"
  fi
}

render_nginx_template() {
  local source="$1"
  local target="$2"

  cp "$source" "$target"
  sed -i "s|\${DOMAIN}|${DOMAIN}|g" "$target"
}

COMPOSE_FILES=(
  -f docker/docker-compose.yml
  -f docker/docker-compose.production.yml
  -f docker/docker-compose.certbot.override.yml
)

echo "========================================"
echo "Starting RAG KB deployment to Debian 12"
echo "APP_DIR=$APP_DIR"
echo "DOMAIN=$DOMAIN"
echo "EMAIL=$EMAIL"
echo "========================================"

install_docker_if_needed

if [ ! -f "$APP_DIR/docker/docker-compose.yml" ]; then
  if [ -z "$REPO_URL" ]; then
    echo "ERROR: $APP_DIR is not a project directory and REPO_URL is not set"
    exit 1
  fi
  mkdir -p "$(dirname "$APP_DIR")"
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

ensure_directory data/uploads
ensure_directory data/chroma_db
ensure_directory data/job_status
ensure_directory data/quotas
ensure_directory logs/nginx
ensure_directory docker/certbot/conf
ensure_directory docker/certbot/www
ensure_directory secrets
ensure_directory secrets/openai_api_key
ensure_directory secrets/jwt_secret
ensure_directory secrets/admin_password_hash

write_secret secrets/openai_api_key/deepseek_api_key "$API_KEY" "LLM API Key"
write_secret secrets/embedding_api_key "$EMBEDDING_API_KEY" "Embedding API Key"

if [ ! -s secrets/jwt_secret/token_secret ]; then
  if [ -n "$JWT_SECRET" ]; then
    write_secret secrets/jwt_secret/token_secret "$JWT_SECRET" "JWT Secret"
  else
    openssl rand -hex 32 > secrets/jwt_secret/token_secret
    chmod 600 secrets/jwt_secret/token_secret
    echo "Generated JWT Secret: secrets/jwt_secret/token_secret"
  fi
fi

if [ -n "$ADMIN_PASSWORD_HASH" ]; then
  ADMIN_PASSWORD_HASH="${ADMIN_PASSWORD_HASH#ADMIN_PASSWORD_HASH=}"
  write_secret secrets/admin_password_hash/password_hash "$ADMIN_PASSWORD_HASH" "Admin Password Hash"
fi

require_secret_file secrets/openai_api_key/deepseek_api_key "LLM API Key"
require_secret_file secrets/embedding_api_key "Embedding API Key"
require_secret_file secrets/jwt_secret/token_secret "JWT Secret"
require_secret_file secrets/admin_password_hash/password_hash "Admin Password Hash"

# Generate .env.production from template (the actual file is gitignored)
if [ ! -f .env.production ]; then
  if [ -f .env.production.template ]; then
    cp .env.production.template .env.production
    echo "Created .env.production from .env.production.template"
  else
    echo "ERROR: missing .env.production.template"
    exit 1
  fi
fi
cp .env.production ".env.production.bak.$(date +%F-%H%M%S)"
set_env_value .env.production JWT_SECRET_FILE /run/secrets/jwt_secret/token_secret
set_env_value .env.production ADMIN_PASSWORD_HASH_FILE /run/secrets/admin_password_hash/password_hash
set_env_value .env.production API_KEY_FILE /run/secrets/openai_api_key/deepseek_api_key
set_env_value .env.production EMBEDDING_API_KEY_FILE /run/secrets/embedding_api_key
set_env_value .env.production BACKEND_URL_CLIENT "https://${DOMAIN}"
set_env_value .env.production ALLOWED_ORIGINS "https://${DOMAIN},https://www.${DOMAIN}"
set_env_value .env.production DEBUG False
set_env_value .env.production ENABLE_API_DOCS False
sed -i "s|https://yourdomain.com|https://${DOMAIN}|g" .env.production
sed -i "s|https://www.yourdomain.com|https://www.${DOMAIN}|g" .env.production

echo "Updated .env.production"
grep -E 'API_KEY_FILE|EMBEDDING_API_KEY_FILE|BACKEND_URL_CLIENT|ALLOWED_ORIGINS|DEBUG|ENABLE_API_DOCS' .env.production || true

# Generate docker-compose.production.yml from template (the actual file is gitignored)
if [ ! -f docker/docker-compose.production.yml ]; then
  if [ -f docker/docker-compose.production.yml.template ]; then
    cp docker/docker-compose.production.yml.template docker/docker-compose.production.yml
    echo "Created docker/docker-compose.production.yml from template"
  else
    echo "ERROR: missing docker/docker-compose.production.yml.template"
    exit 1
  fi
fi

if [ ! -f docker/nginx/conf.d/production-init.conf.template ]; then
  echo "ERROR: missing docker/nginx/conf.d/production-init.conf.template"
  exit 1
fi

render_nginx_template docker/nginx/conf.d/production-init.conf.template docker/nginx/conf.d/production-init.conf
sed -i 's|^      - ./nginx/conf.d/production.conf:/etc/nginx/conf.d/default.conf:ro|      - ./nginx/conf.d/production-init.conf:/etc/nginx/conf.d/default.conf:ro|g' docker/docker-compose.production.yml

cat > docker/docker-compose.certbot.override.yml <<'EOF'
services:
  certbot:
    image: certbot/certbot
    container_name: rag-kb-certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    networks:
      - rag_network
EOF

docker compose "${COMPOSE_FILES[@]}" up -d --build backend frontend nginx

echo "Checking whether ports 8000/8501 are publicly published..."
if [ -x scripts/check-public-ports.sh ]; then
  scripts/check-public-ports.sh
fi

echo "Waiting for services to start..."
sleep 10
curl -fsS "http://${DOMAIN}/health" || echo "HTTP health check failed for now; continuing certificate issuance"

docker compose "${COMPOSE_FILES[@]}" run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  -d "${DOMAIN}" -d "www.${DOMAIN}" \
  --email "${EMAIL}" --agree-tos --no-eff-email \
  --non-interactive --keep-until-expiring

render_nginx_template docker/nginx/conf.d/production.conf.template docker/nginx/conf.d/production.conf
sed -i 's|# ssl_certificate /etc/letsencrypt|ssl_certificate /etc/letsencrypt|g' docker/nginx/conf.d/production.conf
sed -i 's|# ssl_certificate_key /etc/letsencrypt|ssl_certificate_key /etc/letsencrypt|g' docker/nginx/conf.d/production.conf

if [ -f docker/certbot/conf/options-ssl-nginx.conf ]; then
  sed -i 's|# include /etc/letsencrypt|include /etc/letsencrypt|g' docker/nginx/conf.d/production.conf
else
  echo "WARNING: options-ssl-nginx.conf not found; keeping include commented"
fi

if [ -f docker/certbot/conf/ssl-dhparams.pem ]; then
  sed -i 's|# ssl_dhparam /etc/letsencrypt|ssl_dhparam /etc/letsencrypt|g' docker/nginx/conf.d/production.conf
else
  echo "WARNING: ssl-dhparams.pem not found; keeping ssl_dhparam commented"
fi

sed -i 's|^      - ./nginx/conf.d/production-init.conf:/etc/nginx/conf.d/default.conf:ro|      - ./nginx/conf.d/production.conf:/etc/nginx/conf.d/default.conf:ro|g' docker/docker-compose.production.yml

docker compose "${COMPOSE_FILES[@]}" up -d --force-recreate nginx
docker exec rag-kb-nginx-prod nginx -t

cat > /etc/cron.d/rag-kb-certbot-renew <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
17 3 * * * root cd ${APP_DIR} && /usr/bin/docker compose -f docker/docker-compose.yml -f docker/docker-compose.production.yml -f docker/docker-compose.certbot.override.yml run --rm certbot renew --webroot -w /var/www/certbot --quiet && /usr/bin/docker exec rag-kb-nginx-prod nginx -s reload >> /var/log/rag-kb-certbot-renew.log 2>&1
EOF
systemctl restart cron

echo "Deployment complete, verifying HTTPS..."
curl -I "https://${DOMAIN}" || true
curl "https://${DOMAIN}/health" || true

echo "========================================"
echo "Deployment complete"
echo "URL: https://${DOMAIN}"
echo "Status: docker compose -f docker/docker-compose.yml -f docker/docker-compose.production.yml -f docker/docker-compose.certbot.override.yml ps"
echo "Logs: docker compose -f docker/docker-compose.yml -f docker/docker-compose.production.yml -f docker/docker-compose.certbot.override.yml logs -f"
echo "Renewal dry run: docker compose -f docker/docker-compose.yml -f docker/docker-compose.production.yml -f docker/docker-compose.certbot.override.yml run --rm certbot renew --webroot -w /var/www/certbot --dry-run"
echo "========================================"

