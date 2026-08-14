#!/bin/bash
set -e

# =============================================
# CloudDrive Hub — 一键部署脚本
# 整合 Alist + rclone + Tailscale + Operit Agent
# =============================================

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "[$(date '+%H:%M:%S')] $1"; }
ok()   { log "${GREEN}✅ $1${NC}"; }
fail() { log "${RED}❌ $1${NC}"; exit 1; }
warn() { log "${YELLOW}⚠️ $1${NC}"; }

echo ""
echo "============================================"
echo "  CloudDrive Hub — 一键部署"
echo "============================================"
echo ""

# 1. 检查系统
log "检查系统环境..."
ARCH=$(uname -m)
case "$ARCH" in
    aarch64|arm64) ARCH="arm64" ;;
    x86_64|amd64)  ARCH="amd64" ;;
    *) fail "不支持的架构: $ARCH" ;;
esac
ok "系统: $(uname -s) $ARCH"

# 2. 安装依赖
log "安装系统依赖..."
apt-get update -qq
apt-get install -y -qq curl wget fuse3 2>&1 | tail -1
ok "系统依赖已安装"

# 3. 安装 rclone
if ! command -v rclone &>/dev/null; then
    log "安装 rclone..."
    curl -fsSL https://rclone.org/install.sh | bash
    ok "rclone 已安装: $(rclone version | head -1)"
else
    ok "rclone 已存在: $(rclone version | head -1)"
fi

# 4. 安装 Alist
if ! command -v alist &>/dev/null && [ ! -f /opt/alist/alist ]; then
    log "安装 Alist..."
    curl -fsSL "https://alist.nn.ci/v3.sh" | bash -s install
    ok "Alist 已安装"
else
    ok "Alist 已存在"
fi

# 5. 安装 Tailscale
if ! command -v tailscale &>/dev/null; then
    log "安装 Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
    ok "Tailscale 已安装"
else
    ok "Tailscale 已存在: $(tailscale version 2>/dev/null | head -1)"
fi

# 6. 创建目录结构
log "创建目录结构..."
mkdir -p /mnt/cloud
mkdir -p /etc/clouddrive
mkdir -p /var/log/clouddrive
mkdir -p /tmp/clouddrive/cache
ok "目录结构已创建"

# 7. 启动 Alist
log "启动 Alist..."
if systemctl is-active --quiet alist 2>/dev/null; then
    ok "Alist 已在运行"
else
    systemctl start alist 2>/dev/null || /opt/alist/alist server 2>/dev/null &
    sleep 2
    ok "Alist 已启动 (http://localhost:5244)"
fi

# 8. 配置 rclone WebDAV
log "配置 rclone WebDAV (指向 Alist)..."
ALIST_PASS=$(/opt/alist/alist admin 2>/dev/null | grep password | awk '{print $NF}')
if [ -n "$ALIST_PASS" ]; then
    rclone config create alist-webdav webdav \
        url=http://localhost:5244/dav \
        vendor=other user=admin \
        pass=$(rclone obscure "$ALIST_PASS") 2>/dev/null
    ok "rclone WebDAV 已配置 (admin / $ALIST_PASS)"
else
    warn "请手动配置 Alist 后运行 rclone config"
fi

# 9. 挂载
log "挂载 Alist 到本地..."
mkdir -p /mnt/cloud
rclone mount alist-webdav: /mnt/cloud \
    --daemon \
    --vfs-cache-mode writes \
    --allow-other \
    --dir-cache-time 5m 2>/dev/null || warn "挂载失败，请手动执行 mount.sh"
ok "网盘已挂载到 /mnt/cloud"

# 10. 复制独立通道工具
log "部署独立 ADB 通道工具..."
TOOLS_DIR="/opt/clouddrive-hub/tools"
mkdir -p "$TOOLS_DIR"
if [ -f /data/user/0/com.ai.assistance.operit/files/workspace/2ecd5358-7768-462e-ad65-c2bf4d6cde7a/tools/adb_server_shell ]; then
    cp /data/user/0/com.ai.assistance.operit/files/workspace/2ecd5358-7768-462e-ad65-c2bf4d6cde7a/tools/* "$TOOLS_DIR/" 2>/dev/null
    chmod +x "$TOOLS_DIR"/*.sh "$TOOLS_DIR"/adb_* 2>/dev/null
    ok "独立通道工具已部署"
fi

echo ""
echo "============================================"
echo "  ✅ CloudDrive Hub 部署完成!"
echo ""
echo "  Alist WebUI:  http://localhost:5244"
echo "  挂载目录:     /mnt/cloud/"
echo "  rclone 配置:  rclone config"
echo "  Tailscale:    tailscale up"
echo "  Agent:        python3 agent/main.py"
echo ""
echo "  默认密码: 运行 alist admin 获取"
echo "============================================"
echo ""
