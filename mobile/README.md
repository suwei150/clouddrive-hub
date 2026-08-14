# CloudDrive Hub — 手机版 📱

> 适用于 Android 手机（Xiaomi Redmi M2104K10AC）
> 通过独立 ADB 通道 + Shizuku + Alist WebDAV 实现轻量网盘管理

## 核心设计

```
┌──────────────────────────────────────┐
│          手机版 CloudDrive Hub         │
│                                      │
│  ┌──────────────────────────────┐    │
│  │ 独立 ADB 通道 (核心引擎)       │    │
│  │ adb_server_shell              │    │
│  │  → 127.0.0.1:5037 (adb)      │    │
│  │  → 192.168.43.8:34953 (无线)  │    │
│  └──────────┬───────────────────┘    │
│             │                         │
│  ┌──────────▼───────────────────┐    │
│  │ 巡检引擎 (patrol.sh)          │    │
│  │ · 3分钟巡检 ADB 通道          │    │
│  │ · 自动修复 Shizuku            │    │
│  │ · 自动修复 iAdb              │    │
│  │ · 独立通道健康报告            │    │
│  └──────────┬───────────────────┘    │
│             │                         │
│  ┌──────────▼───────────────────┐    │
│  │ Alist 网盘网关 (远程)         │    │
│  │ · 通过独立通道 SSH 隧道访问    │    │
│  │ · 50+ 网盘统一 WebDAV        │    │
│  │ · 文件浏览/上传/下载/管理     │    │
│  └──────────┬───────────────────┘    │
│             │                         │
│  ┌──────────▼───────────────────┐    │
│  │ Operit Workflow 自愈          │    │
│  │ · 2个 Workflow 同时巡检       │    │
│  │ · 每3分钟恢复 Shizuku binder  │    │
│  │ · 独立通道不依赖 binder       │    │
│  └──────────────────────────────┘    │
└──────────────────────────────────────┘
```

## 技术栈

| 组件 | 说明 |
|------|------|
| **独立 ADB 通道** | 自研 `adb_server_shell`，绕过 Shizuku binder |
| **巡检脚本** | `patrol.sh` — 7项巡检，不依赖 binder |
| **Shizuku** | 系统授权服务，自动保活 |
| **iAdb** | root adbd 启动器 |
| **Alist** | 远程网盘聚合网关 |
| **Tailscale** | 安全远程访问 |
| **Obscura** | 浏览器自动化承载 |

## 文件结构

```
mobile/
├── app/                    # 主应用
│   ├── hub.sh             # 入口脚本（一键启动）
│   ├── channel.sh         # 独立通道管理
│   └── patrol.sh          # 巡检脚本（独立版）
├── workflows/              # Operit Workflow 定义
│   ├── keepalive.json     # 保活自愈
│   └── patrol.json        # 巡检触发
└── tools/                  # 编译好的工具
    ├── adb_server_shell   # 独立 ADB 通道客户端
    └── adb_connect        # 裸 ADB 协议客户端
```

## 快速开始

### 1. 部署独立通道
```bash
# 复制工具到手机
adb push tools/adb_server_shell /data/local/tmp/
adb push tools/adb_connect /data/local/tmp/
adb shell chmod 755 /data/local/tmp/adb_server_shell
```

### 2. 启动巡检
```bash
# 手动运行
bash app/hub.sh

# 或通过 Workflow 自动每3分钟巡检
```

### 3. 连接 Alist
```bash
# 通过独立通道转发 Alist WebDAV
bash app/channel.sh tunnel alist 5244
```

## 与 Proot 版的区别

| 维度 | 手机版 | Proot 服务器版 |
|:-----|:-------|:--------------|
| 运行环境 | Android 13 shell | Ubuntu 24 (proot) |
| 挂载方式 | 无 FUSE | FUSE 本地挂载 |
| 网盘网关 | 远程 Alist | 本地 Alist |
| 巡检通道 | 独立 ADB 通道 | 系统 bash |
| 自愈能力 | Workflow 驱动 | systemd + Workflow |
| 安装体积 | < 1MB | 50MB+ |
