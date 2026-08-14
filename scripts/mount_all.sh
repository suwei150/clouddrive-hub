#!/bin/bash
# =============================================
# CloudDrive Hub — 一键挂载所有网盘
# 读取 /etc/clouddrive/providers.conf 逐网盘挂载
# =============================================

CONFIG="/etc/clouddrive/providers.conf"
MOUNT_BASE="/mnt/cloud"
LOG_DIR="/var/log/clouddrive"
RCLONE_CONF="$HOME/.config/rclone/rclone.conf"

# 颜色
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

mkdir -p "$MOUNT_BASE" "$LOG_DIR"

log()  { echo -e "[$(date '+%H:%M:%S')] $1"; }
ok()   { log "${GREEN}✅ $1${NC}"; }
fail() { log "${RED}❌ $1${NC}"; }
warn() { log "${YELLOW}⚠️ $1${NC}"; }

# 检查 rclone
if ! command -v rclone &>/dev/null; then
    fail "rclone 未安装，请先 apt install rclone"
    exit 1
fi

# 检查 FUSE
if ! lsmod 2>/dev/null | grep -q fuse; then
    warn "FUSE 模块未加载，尝试 modprobe fuse"
    modprobe fuse 2>/dev/null || fail "FUSE 不可用"
fi

# 检查配置文件
if [ ! -f "$RCLONE_CONF" ]; then
    fail "rclone 配置文件不存在: $RCLONE_CONF"
    fail "请先运行 rclone config 配置网盘"
    exit 1
fi

# 获取所有网盘列表
echo ""
echo "========== CloudDrive Hub 一键挂载 =========="
echo "配置文件: $RCLONE_CONF"
echo "挂载目录: $MOUNT_BASE"
echo "日志目录: $LOG_DIR"
echo "=============================================="
echo ""

# 列出所有网盘
REMOTES=$(rclone listremotes 2>/dev/null | sed 's/:$//')
if [ -z "$REMOTES" ]; then
    fail "没有找到任何网盘配置"
    exit 1
fi

COUNT=0
for REMOTE in $REMOTES; do
    MOUNT_POINT="$MOUNT_BASE/$REMOTE"
    LOG_FILE="$LOG_DIR/${REMOTE}.log"
    
    # 检查是否已挂载
    if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
        ok "$REMOTE 已挂载 ($MOUNT_POINT)"
        continue
    fi
    
    mkdir -p "$MOUNT_POINT"
    
    # 启动 rclone mount
    rclone mount "$REMOTE:" "$MOUNT_POINT" \
        --daemon \
        --log-file "$LOG_FILE" \
        --vfs-cache-mode writes \
        --cache-dir "/tmp/clouddrive/cache/$REMOTE" \
        --dir-cache-time 5m \
        --vfs-read-chunk-size 32M \
        --vfs-read-chunk-size-limit 256M \
        --buffer-size 64M \
        --timeout 60s \
        --contimeout 30s \
        --low-level-retries 3 \
        --retries 3 \
        --transfers 4 \
        --checkers 8 \
        --attr-timeout 1s \
        --umask 002 \
        --allow-other 2>/dev/null
    
    if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
        ok "$REMOTE → $MOUNT_POINT"
        ((COUNT++))
    else
        fail "$REMOTE 挂载失败 (查看日志: $LOG_FILE)"
    fi
done

echo ""
echo "========== 挂载完成: $COUNT 个网盘已挂载 =========="
echo ""
echo "访问路径: $MOUNT_BASE"
echo "挂载列表:"
df -h | grep "$MOUNT_BASE" | awk '{print "  📁 " $6 " (" $4 " 可用)"}'
echo ""
