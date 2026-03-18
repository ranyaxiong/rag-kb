#!/bin/bash
# Production HTTPS Configuration Wizard
# Helps you choose and configure the right SSL strategy

set -e

echo "========================================"
echo "🚀 生产环境 HTTPS 配置向导"
echo "========================================"
echo ""
echo "请选择生产环境 HTTPS 方案："
echo ""
echo "1. 独立服务器 + Let's Encrypt（推荐自建服务器）"
echo "   ✓ 免费证书"
echo "   ✓ 自动续期"
echo "   ✓ 完全控制"
echo ""
echo "2. 云厂商 SLB/ALB SSL 卸载（推荐云部署）⭐"
echo "   ✓ 最简单"
echo "   ✓ 无需管理证书"
echo "   ✓ 高可用 + 负载均衡"
echo ""
echo "3. Nginx + 云厂商证书（中间方案）"
echo "   ✓ 灵活性高"
echo "   ✓ 证书由云厂商管理"
echo "   ✓ 便于迁移"
echo ""
read -p "请选择 (1-3): " choice
echo ""

read -p "请输入你的域名（例如：example.com）: " domain

case $choice in
  1)
    echo ""
    echo "========================================="
    echo "📝 方案 1: 独立服务器 + Let's Encrypt"
    echo "========================================="
    echo ""
    echo "这个方案使用 Certbot 自动获取和续期 Let's Encrypt 证书"
    echo ""
    echo "前置条件："
    echo "  ✓ 域名 DNS 已指向服务器公网 IP"
    echo "  ✓ 服务器防火墙开放 80 和 443 端口"
    echo ""
    echo "配置步骤："
    echo ""
    echo "1. 创建必要的目录"
    mkdir -p docker/certbot/conf
    mkdir -p docker/certbot/www
    echo "   ✓ 目录已创建"
    echo ""
    
    echo "2. 配置 Nginx"
    cp docker/nginx/conf.d/production.conf.template docker/nginx/conf.d/production.conf
    sed -i "s/\${DOMAIN}/$domain/g" docker/nginx/conf.d/production.conf
    # Uncomment Let's Encrypt lines
    sed -i 's|# ssl_certificate /etc/letsencrypt|ssl_certificate /etc/letsencrypt|g' docker/nginx/conf.d/production.conf
    sed -i 's|# include /etc/letsencrypt|include /etc/letsencrypt|g' docker/nginx/conf.d/production.conf
    echo "   ✓ Nginx 配置已生成"
    echo ""
    
    echo "3. 获取 SSL 证书"
    echo "   运行以下命令获取证书："
    echo ""
    echo "   docker-compose -f docker/docker-compose.production.yml run --rm certbot certonly \\"
    echo "     --webroot \\"
    echo "     --webroot-path=/var/www/certbot \\"
    echo "     -d $domain \\"
    echo "     -d www.$domain \\"
    echo "     --email your-email@example.com \\"
    echo "     --agree-tos \\"
    echo "     --no-eff-email"
    echo ""
    
    echo "4. 启动服务"
    echo "   cd docker && docker-compose -f docker-compose.production.yml up -d"
    echo ""
    ;;
    
  2)
    echo ""
    echo "========================================="
    echo "☁️  方案 2: 云厂商 SLB/ALB SSL 卸载"
    echo "========================================="
    echo ""
    echo "这是最推荐的生产环境方案！"
    echo ""
    echo "优势："
    echo "  ✓ 证书由云厂商自动管理，无需手动续期"
    echo "  ✓ 支持自动扩展和负载均衡"
    echo "  ✓ 应用配置最简单"
    echo "  ✓ 未来可以轻松切换到独立服务器"
    echo ""
    echo "配置步骤："
    echo ""
    echo "1. 在云厂商控制台申请 SSL 证书"
    echo "   - 阿里云：免费版 DV SSL（1年有效，可续期）"
    echo "   - 腾讯云：免费版 SSL 证书"
    echo "   - AWS：AWS Certificate Manager（完全免费）"
    echo ""
    echo "2. 配置负载均衡器 (SLB/ALB)"
    echo "   - 创建负载均衡实例"
    echo "   - 添加 HTTPS 监听器（443 端口）"
    echo "   - 绑定 SSL 证书"
    echo "   - 配置后端服务器（你的 ECS/服务器）"
    echo "   - 前端监听：HTTPS:443 -> 后端转发：HTTP:80"
    echo ""
    echo "3. 更新应用配置"
    echo "   如需新建配置，可先复制 .env.production.template 为 .env.production 后再编辑："
    echo "   ALLOWED_ORIGINS=https://$domain,https://www.$domain"
    echo "   DEBUG=False"
    echo ""
    echo "4. 启动应用（使用标准 HTTP 配置）"
    echo "   cd docker && docker-compose up -d"
    echo ""
    echo "5. 配置域名解析"
    echo "   将域名 A 记录指向负载均衡器的公网 IP"
    echo ""
    echo "💡 注意："
    echo "   使用这个方案时，你的应用只需要监听 HTTP 端口"
    echo "   SSL 加密/解密由云厂商的负载均衡器处理"
    echo ""
    ;;
    
  3)
    echo ""
    echo "========================================="
    echo "🔧 方案 3: Nginx + 云厂商证书"
    echo "========================================="
    echo ""
    echo "这个方案在你的服务器上使用 Nginx 处理 SSL，"
    echo "但证书从云厂商下载（通常有效期 1 年）"
    echo ""
    echo "配置步骤："
    echo ""
    echo "1. 在云厂商控制台申请并下载证书"
    echo "   - 选择 Nginx 格式下载"
    echo "   - 会得到两个文件："
    echo "     * 证书文件（.pem 或 .crt）"
    echo "     * 私钥文件（.key）"
    echo ""
    
    echo "2. 将证书文件放置到指定位置"
    mkdir -p docker/nginx/certs
    echo "   请将证书文件复制到："
    echo "   - docker/nginx/certs/production-cert.pem"
    echo "   - docker/nginx/certs/production-key.pem"
    echo ""
    
    echo "3. 配置 Nginx"
    cp docker/nginx/conf.d/production.conf.template docker/nginx/conf.d/production.conf
    sed -i "s/\${DOMAIN}/$domain/g" docker/nginx/conf.d/production.conf
    # Uncomment cloud provider certificate lines
    sed -i 's|# ssl_certificate /etc/nginx/certs/production|ssl_certificate /etc/nginx/certs/production|g' docker/nginx/conf.d/production.conf
    echo "   ✓ Nginx 配置已生成"
    echo ""
    
    echo "4. 更新 Docker Compose 配置"
    echo "   取消注释 docker-compose.production.yml 中的证书挂载行"
    echo ""
    
    echo "5. 启动服务"
    echo "   cd docker && docker-compose -f docker-compose.production.yml up -d"
    echo ""
    
    echo "⚠️  证书过期提醒："
    echo "   云厂商证书通常有效期 1 年，需要手动续期"
    echo "   建议设置日历提醒，或考虑方案 1（Let's Encrypt）的自动续期"
    echo ""
    ;;
    
  *)
    echo "❌ 无效选择"
    exit 1
    ;;
esac

echo "========================================="
echo "🔐 通用配置（所有方案适用）"
echo "========================================="
echo ""
echo "1. 创建生产环境配置文件（基于模板）"
if [ ! -f .env.production ]; then
    cp .env.production.template .env.production
    sed -i "s|https://yourdomain.com|https://$domain|g" .env.production
    sed -i "s|https://www.yourdomain.com|https://www.$domain|g" .env.production
    echo "   ✓ 已基于 .env.production.template 创建 .env.production"
else
    echo "   ℹ️  .env.production 已存在，请手动更新"
fi
echo ""

echo "2. 安全配置检查清单"
echo "   [ ] API Key 使用安全存储方式（环境变量/Docker Secrets/密钥环）"
echo "   [ ] DEBUG 设置为 False"
echo "   [ ] ALLOWED_ORIGINS 设置为实际域名"
echo "   [ ] 防火墙只开放必要端口（80, 443）"
echo "   [ ] 定期备份数据目录"
echo ""

echo "3. 测试 HTTPS 配置"
echo "   curl -I https://$domain"
echo "   curl https://$domain/health"
echo ""
echo "4. SSL 安全性测试"
echo "   访问: https://www.ssllabs.com/ssltest/"
echo "   输入你的域名进行全面安全检查"
echo ""

echo "========================================="
echo "✅ 配置向导完成！"
echo "========================================="
echo ""
echo "📚 相关文档："
echo "   - 本地开发: README.md"
echo "   - 安全配置: SECURITY.md"
echo "   - Docker 部署: docker/README.md"
echo ""



