#!/system/bin/sh
# =============================================
# CloudDrive Hub — 手机版入口
# 不依赖 Shizuku binder，通过独立 ADB 通道
# =============================================

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "[$(date '+%H:%M:%S')] $1"; }
ok()   { log "${GREEN}✅ $1${NC}"; }
fail() { log "${RED}❌ $1${NC}"; }
warn() { log "${YELLOW}⚠️ $1${NC}"; }

WORKSPACE="/data/user/0/com.ai.assistance.operit/files/workspace/2ecd5358-7768-462e-ad65-c2bf4d6cde7a"
TOOLS="$WORKSPACE/tools"
ADB_SHELL="$TOOLS/adb_server_shell"
PATROL="$TOOLS/patrol.sh"

echo ""
echo "======================================"
echo "  CloudDrive Hub — 手机版 v1.0"
echo "  独立通道 · 零依赖 · 自愈"
echo "======================================"
echo ""

case "${1:-help}" in
    start|up)
        log "启动独立通道..."
        if [ -x "$ADB_SHELL" ]; then
            ok "独立通道工具就绪"
            $ADB_SHELL 2>&1 | head -3
        else
            fail "adbd_server_shell 未找到: $ADB_SHELL"
            exit 1
        fi
        ;;

    patrol|check)
        log "运行巡检..."
        if [ -x "$PATROL" ]; then
            bash "$PATROL"
        else
            fail "patrol.sh 未找到"
            # 降级巡检
            echo "--- 5037 ---"
            timeout 2 bash -c 'exec 3<>/dev/tcp/127.0.0.1/5037' 2>/dev/null && echo "OK" || echo "DEAD"
            echo "--- 34953 ---"
            timeout 2 bash -c 'exec 3<>/dev/tcp/192.168.43.8/34953' 2>/dev/null && echo "OK" || echo "DEAD"
            echo "--- 8787 ---"
            timeout 2 bash -c 'exec 3<>/dev/tcp/127.0.0.1/8787' 2>/dev/null && echo "OK" || echo "DEAD"
            echo "--- Shizuku ---"
            pidof moe.shizuku.privileged.api 2>/dev/null && echo "ALIVE" || echo "DEAD"
        fi
        ;;

    heal|fix)
        log "自愈模式..."
        # 1. 修复 ADB server
        timeout 2 bash -c 'exec 3<>/dev/tcp/127.0.0.1/5037' 2>/dev/null
        if [ $? -ne 0 ]; then
            warn "ADB server 挂了，修复中..."
            # 通过 proot 重启 adb server
            /data/user/0/com.ai.assistance.operit/files/usr/bin/proot \
              -0 -r /data/user/0/com.ai.assistance.operit/files/usr/var/lib/proot-distro/installed-rootfs/ubuntu \
              --link2symlink \
              -b /dev -b /proc -b /sys \
              -b /storage/emulated/0:/sdcard \
              /usr/bin/adb kill-server 2>/dev/null
            /data/user/0/com.ai.assistance.operit/files/usr/bin/proot \
              -0 -r /data/user/0/com.ai.assistance.operit/files/usr/var/lib/proot-distro/installed-rootfs/ubuntu \
              --link2symlink \
              -b /dev -b /proc -b /sys \
              -b /storage/emulated/0:/sdcard \
              /usr/bin/adb start-server 2>/dev/null &
            sleep 2
            timeout 2 bash -c 'exec 3<>/dev/tcp/127.0.0.1/5037' 2>/dev/null && ok "ADB server 已恢复" || fail "ADB server 修复失败"
        else
            ok "ADB server 正常"
        fi

        # 2. 修复 Shizuku
        pidof moe.shizuku.privileged.api 2>/dev/null
        if [ $? -ne 0 ]; then
            warn "Shizuku 挂了，重启服务..."
            am start-service -n moe.shizuku.privileged.api/moe.shizuku.server.ShizukuService 2>/dev/null
            sleep 3
            pidof moe.shizuku.privileged.api 2>/dev/null && ok "Shizuku 已恢复" || fail "Shizuku 修复失败"
        else
            ok "Shizuku 正常"
        fi

        # 3. 修复 iAdb
        timeout 2 bash -c 'exec 3<>/dev/tcp/127.0.0.1/39291' 2>/dev/null
        if [ $? -ne 0 ]; then
            warn "iAdb root adbd 未运行，启动 iAdb..."
            am start -n com.iadb.helper/.MainActivity 2>/dev/null
            sleep 3
            timeout 2 bash -c 'exec 3<>/dev/tcp/127.0.0.1/39291' 2>/dev/null && ok "iAdb 已恢复" || warn "iAdb 需要手动授权"
        else
            ok "iAdb root adbd 正常"
        fi
        ;;

    status|stats)
        echo "=== 系统状态 ==="
        echo "ADB server:  $(timeout 2 bash -c 'exec 3<>/dev/tcp/127.0.0.1/5037' 2>/dev/null && echo OK || echo DEAD)"
        echo "无线调试:    $(timeout 2 bash -c 'exec 3<>/dev/tcp/192.168.43.8/34953' 2>/dev/null && echo OK || echo DEAD)"
        echo "iAdb:        $(timeout 2 bash -c 'exec 3<>/dev/tcp/127.0.0.1/39291' 2>/dev/null && echo OK || echo DEAD)"
        echo "MT MCP:      $(timeout 2 bash -c 'exec 3<>/dev/tcp/127.0.0.1/8787' 2>/dev/null && echo OK || echo DEAD)"
        echo "Shizuku:     $(pidof moe.shizuku.privileged.api 2>/dev/null && echo ALIVE || echo DEAD)"
        echo "独立通道:    $([ -x /data/local/tmp/adb_server_shell ] && echo READY || echo MISSING)"
        ;;

    shell)
        log "打开独立 ADB shell 通道..."
        if [ -x "$ADB_SHELL" ]; then
            $ADB_SHELL
        else
            fail "adb_server_shell 未找到"
        fi
        ;;

    help|*)
        echo "用法: hub.sh <命令>"
        echo ""
        echo "命令:"
        echo "  start|up     启动独立通道"
        echo "  patrol|check 运行巡检"
        echo "  heal|fix     自愈修复 (ADB/Shizuku/iAdb)"
        echo "  status|stats 查看系统状态"
        echo "  shell        打开独立 shell"
        echo "  help         显示帮助"
        echo ""
        echo "示例:"
        echo "  hub.sh status"
        echo "  hub.sh heal"
        echo "  hub.sh patrol"
        ;;
esac
