#!/bin/bash
set -e

echo "=== CloudDrive Hub — Tailscale 网络配置 ==="

# 安装 Tailscale
if ! command -v tailscale &>/dev/null; then
    echo "安装 Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
fi

# 启动并认证
echo "启动 Tailscale..."
tailscale up --accept-routes --advertise-routes=192.168.43.0/24

# 暴露 Alist WebUI
echo "暴露 Alist WebUI..."
tailscale serve --bg 5244

# 暴露挂载目录（通过 WebDAV）
echo "暴露挂载目录..."
tailscale serve --bg /mnt/cloud

# 设置 ACL
echo "配置 ACL..."
cp acl.hujson /etc/tailscale/acl.hujson 2>/dev/null || true

echo ""
echo "✅ Tailscale 配置完成!"
echo "Tailscale IP: $(tailscale ip -4 2>/dev/null)"
echo "Alist WebUI:  http://$(tailscale ip -4 2>/dev/null):5244"
echo "挂载目录:     /mnt/cloud"
echo ""
