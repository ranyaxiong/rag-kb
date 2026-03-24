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

if [ ! -f .env.production ]; then
  echo "❌ 未找到 .env.production，请先确认仓库包含该文件"
  exit 1
fi
cp .env.production ".env.production.bak.$(date +%F-%H%M%S)"
sed -i "s|^BACKEND_URL_CLIENT=.*|BACKEND_URL_CLIENT=https://${DOMAIN}|g" .env.production
sed -i "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}|g" .env.production
sed -i "s|^DEBUG=.*|DEBUG=False|g" .env.production

echo "✅ 已更新 .env.production"
grep -E 'BACKEND_URL_CLIENT|ALLOWED_ORIGINS|DEBUG' .env.production || true

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

cat > docker/nginx/conf.d/production.conf <<EOF
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location /health {
        proxy_pass http://backend:8000/health;
        access_log off;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        client_max_body_size 50M;
    }

    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    location / {
        proxy_pass http://frontend:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
        proxy_connect_timeout 60;
        proxy_send_timeout 60;
        proxy_buffering off;
        proxy_cache off;
        client_max_body_size 50M;
    }
}
EOF

export API_KEY

docker compose -f docker/docker-compose.yml -f docker/docker-compose.production.yml -f docker/docker-compose.certbot.override.yml up -d --build backend frontend nginx

echo "⏳ 等待服务启动..."
sleep 10
curl -fsS "http://${DOMAIN}/health" || echo "⚠️ HTTP 健康检查暂未通过，继续尝试签发证书"

docker compose -f docker/docker-compose.yml -f docker/docker-compose.production.yml -f docker/docker-compose.certbot.override.yml run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  -d "${DOMAIN}" -d "www.${DOMAIN}" \
  --email "${EMAIL}" --agree-tos --no-eff-email

cp docker/nginx/conf.d/production.conf.template docker/nginx/conf.d/production.conf
sed -i "s|\${DOMAIN}|${DOMAIN}|g" docker/nginx/conf.d/production.conf
sed -i 's|# ssl_certificate /etc/letsencrypt|ssl_certificate /etc/letsencrypt|g' docker/nginx/conf.d/production.conf
sed -i 's|# include /etc/letsencrypt|include /etc/letsencrypt|g' docker/nginx/conf.d/production.conf

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

