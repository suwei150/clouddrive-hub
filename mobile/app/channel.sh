#!/system/bin/sh
# =============================================
# CloudDrive Hub — 手机版独立通道管理
# 隧道转发 / 端口映射 / 连接管理
# =============================================

WORKSPACE="/data/user/0/com.ai.assistance.operit/files/workspace/2ecd5358-7768-462e-ad65-c2bf4d6cde7a"
TOOLS="$WORKSPACE/tools"
ADB_SHELL="$TOOLS/adb_server_shell"

case "${1:-help}" in
    status)
        echo "=== 通道状态 ==="
        echo "ADB server:  $(timeout 2 bash -c 'exec 3<>/dev/tcp/127.0.0.1/5037' 2>/dev/null && echo OK || echo DEAD)"
        echo "无线调试:    $(timeout 2 bash -c 'exec 3<>/dev/tcp/192.168.43.8/34953' 2>/dev/null && echo OK || echo DEAD)"
        echo "iAdb root:   $(timeout 2 bash -c 'exec 3<>/dev/tcp/127.0.0.1/39291' 2>/dev/null && echo OK || echo DEAD)"
        echo "MT MCP:      $(timeout 2 bash -c 'exec 3<>/dev/tcp/127.0.0.1/8787' 2>/dev/null && echo OK || echo DEAD)"
        echo "独立通道:    $([ -x /data/local/tmp/adb_server_shell ] && echo READY || echo MISSING)"
        echo "RSA Key:     $([ -f /root/.android/adbkey ] && echo OK || echo MISSING)"
        ;;

    test)
        echo "=== 独立通道测试 ==="
        if [ -x /data/local/tmp/adb_server_shell ]; then
            /data/local/tmp/adb_server_shell 2>&1 | head -10
            echo "EXIT: $?"
        else
            echo "adb_server_shell 未部署"
            echo "请运行: adb push tools/adb_server_shell /data/local/tmp/"
        fi
        ;;

    tunnel)
        # 隧道转发: 通过 proot 转发端口到手机
        HOST="${2:-localhost}"
        PORT="${3:-5244}"
        echo "建立隧道: $HOST:$PORT ..."
        /data/user/0/com.ai.assistance.operit/files/usr/bin/proot \
          -0 -r /data/user/0/com.ai.assistance.operit/files/usr/var/lib/proot-distro/installed-rootfs/ubuntu \
          --link2symlink \
          -b /dev -b /proc -b /sys \
          -b /storage/emulated/0:/sdcard \
          bash -c "exec 3<>/dev/tcp/$HOST/$PORT && echo '隧道建立成功: $HOST:$PORT' || echo '连接失败'"
        ;;

    adb_connect)
        # 通过 adb_server_shell 建立连接
        if [ -x /data/local/tmp/adb_server_shell ]; then
            /data/local/tmp/adb_server_shell
        else
            echo "正在部署独立通道工具..."
            cp "$ADB_SHELL" /data/local/tmp/ 2>/dev/null
            chmod 755 /data/local/tmp/adb_server_shell 2>/dev/null
            /data/local/tmp/adb_server_shell
        fi
        ;;

    help|*)
        echo "用法: channel.sh <命令> [参数]"
        echo ""
        echo "命令:"
        echo "  status             查看通道状态"
        echo "  test               测试独立通道"
        echo "  tunnel <host> <port> 建立隧道"
        echo "  adb_connect        连接独立 shell"
        ;;
esac
