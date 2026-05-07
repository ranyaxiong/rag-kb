#!/bin/bash
set -euo pipefail

echo "🔍 检查 Docker 端口发布情况..."

if ! command -v docker >/dev/null 2>&1; then
  echo "❌ docker 未安装或不可用"
  exit 1
fi

echo ""
echo "当前容器端口发布："
docker ps --format 'table {{.Names}}\t{{.Ports}}'

echo ""
echo "检查是否存在公网发布的 8000/8501..."

published_ports="$(docker ps --format '{{.Names}} {{.Ports}}' || true)"

if echo "$published_ports" | grep -E '0\.0\.0\.0:8000|:::8000|0\.0\.0\.0:8501|:::8501' >/dev/null 2>&1; then
  echo "❌ 检测到 8000/8501 被发布到公网网卡，请移除对应 ports 映射！"
  echo "$published_ports" | grep -E '8000|8501' || true
  exit 1
fi

if echo "$published_ports" | grep -E '127\.0\.0\.1:8000|127\.0\.0\.1:8501' >/dev/null 2>&1; then
  echo "⚠️  检测到 8000/8501 仅绑定 127.0.0.1，适合本机调试，但生产建议完全不发布。"
fi

echo "✅ Docker 端口检查通过：未发现 8000/8501 公网发布。"

echo ""
echo "🔍 检查宿主机监听端口..."

if command -v ss >/dev/null 2>&1; then
  ss -lntp | grep -E ':8000|:8501' || true
elif command -v netstat >/dev/null 2>&1; then
  netstat -lntp | grep -E ':8000|:8501' || true
else
  echo "⚠️  未找到 ss/netstat，跳过宿主机端口监听检查。"
fi

echo ""
echo "✅ 检查完成。请同时确认云安全组只开放 80/443。"