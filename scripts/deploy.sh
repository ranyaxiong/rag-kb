#!/bin/bash
set -euo pipefail

# Debian 12 一键部署脚本（Docker + Nginx + Certbot）
# 用法：
#   export REPO_URL='https://your.git.repo.git'
#   export DOMAIN='example.com'
#   export EMAIL='admin@example.com'
#   export API_KEY='your-llm-api-key'
#   bash scripts/deploy.sh

APP_DIR="${APP_DIR:-/opt/rag_kb}"
REPO_URL="${REPO_URL:-}"
DOMAIN="${DOMAIN:-}"
EMAIL="${EMAIL:-}"
API_KEY="${API_KEY:-}"

if [ "${EUID}" -ne 0 ]; then
  echo "❌ 请使用 root 运行：sudo -i 后再执行 bash scripts/deploy.sh"
  exit 1
fi

for v in REPO_URL DOMAIN EMAIL API_KEY; do
  if [ -z "${!v:-}" ]; then
    echo "❌ 缺少环境变量: $v"
    exit 1
  fi
done

echo "========================================"
echo "🚀 开始部署 RAG KB 到 Debian 12"
echo "APP_DIR=$APP_DIR"
echo "DOMAIN=$DOMAIN"
echo "EMAIL=$EMAIL"
echo "========================================"

apt-get update
apt-get install -y git curl ca-certificates cron docker-compose-plugin
systemctl enable --now cron

mkdir -p /opt
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

mkdir -p data/uploads data/chroma_db logs/nginx docker/certbot/conf docker/certbot/www secrets

# Generate .env.production from template (the actual file is gitignored)
if [ ! -f .env.production ]; then
  if [ -f .env.production.template ]; then
    cp .env.production.template .env.production
    echo "✅ 已从 .env.production.template 创建 .env.production"
  else
    echo "❌ 未找到 .env.production.template"
    exit 1
  fi
fi
cp .env.production ".env.production.bak.$(date +%F-%H%M%S)"
sed -i "s|https://yourdomain.com|https://${DOMAIN}|g" .env.production
sed -i "s|https://www.yourdomain.com|https://www.${DOMAIN}|g" .env.production
sed -i "s|^BACKEND_URL_CLIENT=.*|BACKEND_URL_CLIENT=https://${DOMAIN}|g" .env.production
sed -i "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}|g" .env.production
sed -i "s|^DEBUG=.*|DEBUG=False|g" .env.production

echo "✅ 已更新 .env.production"
grep -E 'BACKEND_URL_CLIENT|ALLOWED_ORIGINS|DEBUG' .env.production || true

# Generate docker-compose.production.yml from template (the actual file is gitignored)
if [ ! -f docker/docker-compose.production.yml ]; then
  if [ -f docker/docker-compose.production.yml.template ]; then
    cp docker/docker-compose.production.yml.template docker/docker-compose.production.yml
    echo "✅ 已从 docker-compose.production.yml.template 创建 docker-compose.production.yml"
  else
    echo "❌ 未找到 docker/docker-compose.production.yml.template"
    exit 1
  fi
fi

# Generate certbot override compose
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

# Initial phase: use production-init.conf (HTTP-only, already in repo)
# This config allows certbot ACME challenge on port 80
# No need to generate production.conf yet — it will be created after cert issuance

export API_KEY

docker compose -f docker/docker-compose.yml -f docker/docker-compose.production.yml -f docker/docker-compose.certbot.override.yml up -d --build backend frontend nginx

echo "🔎检查8000/8501是否被公网发布..."
if [ -x scripts/check-public-ports.sh ]; then
  scripts/check-public-ports.sh
fi

echo "⏳ 等待服务启动..."
sleep 10
curl -fsS "http://${DOMAIN}/health" || echo "⚠️ HTTP 健康检查暂未通过，继续尝试签发证书"

docker compose -f docker/docker-compose.yml -f docker/docker-compose.production.yml -f docker/docker-compose.certbot.override.yml run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  -d "${DOMAIN}" -d "www.${DOMAIN}" \
  --email "${EMAIL}" --agree-tos --no-eff-email

# Certificate issued successfully — switch from HTTP-only to full HTTPS config
cp docker/nginx/conf.d/production.conf.template docker/nginx/conf.d/production.conf
sed -i "s|\${DOMAIN}|${DOMAIN}|g" docker/nginx/conf.d/production.conf
sed -i 's|# ssl_certificate /etc/letsencrypt|ssl_certificate /etc/letsencrypt|g' docker/nginx/conf.d/production.conf
sed -i 's|# ssl_certificate_key /etc/letsencrypt|ssl_certificate_key /etc/letsencrypt|g' docker/nginx/conf.d/production.conf
sed -i 's|# include /etc/letsencrypt|include /etc/letsencrypt|g' docker/nginx/conf.d/production.conf

# Update docker-compose.production.yml to mount production.conf instead of production-init.conf
sed -i 's|production-init.conf|production.conf|g' docker/docker-compose.production.yml

docker compose -f docker/docker-compose.yml -f docker/docker-compose.production.yml -f docker/docker-compose.certbot.override.yml restart nginx

cat > /etc/cron.d/rag-kb-certbot-renew <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
17 3 * * * root cd ${APP_DIR} && /usr/bin/docker compose -f docker/docker-compose.yml -f docker/docker-compose.production.yml -f docker/docker-compose.certbot.override.yml run --rm certbot renew --webroot -w /var/www/certbot --quiet && /usr/bin/docker exec rag-kb-nginx-prod nginx -s reload >> /var/log/rag-kb-certbot-renew.log 2>&1
EOF
systemctl restart cron

echo "✅ 部署完成，正在验证 HTTPS..."
curl -I "https://${DOMAIN}" || true
curl "https://${DOMAIN}/health" || true

echo "========================================"
echo "🎉 部署完成"
echo "访问地址: https://${DOMAIN}"
echo "查看状态: docker compose -f docker/docker-compose.yml -f docker/docker-compose.production.yml -f docker/docker-compose.certbot.override.yml ps"
echo "查看日志: docker compose -f docker/docker-compose.yml -f docker/docker-compose.production.yml -f docker/docker-compose.certbot.override.yml logs -f"
echo "续期测试: docker compose -f docker/docker-compose.yml -f docker/docker-compose.production.yml -f docker/docker-compose.certbot.override.yml run --rm certbot renew --webroot -w /var/www/certbot --dry-run"
echo "========================================"

