# 独立 ADB 通道工具集 🔧

> 这套工具为 Android 设备提供**不依赖 Shizuku binder** 的独立 ADB shell 通道。

## 工具列表

| 文件 | 说明 | 来源 |
|------|------|------|
| `adb_server_shell` | 裸 ADB 协议客户端 (二进制, arm64) | 自编译 |
| `adb_server_shell.c` | 源码 — 通过 5037 adb server 协议直连 shell | 自编译 |
| `adb_connect` | 裸 ADB 协议客户端 (含 TLS 握手, 二进制, arm64) | 自编译 |
| `adb_connect.c` | 源码 — 支持 TLS 直连 34953 无线调试端口 | 自编译 |
| `patrol.sh` | 巡检脚本 — 一键检查所有通道状态 | 自写 |

## 使用方法

```bash
# 独立 shell 通道 (最快)
cd /tmp && ./adb_server_shell
# 输出: INDEPENDENT_OK → shell 就绪

# 完整巡检
bash patrol.sh
```

## 核心原理

```
proot (adb_server_shell) → 127.0.0.1:5037 (adb server) → 192.168.43.8:34953 (无线调试 adbd) → shell
```

**完全不依赖 Shizuku binder**，binder 断了也不影响。
