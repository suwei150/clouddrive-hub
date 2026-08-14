# CloudDrive Hub 🌐

> 开源网盘聚合挂载系统 — FUSE 本地挂载 + Operit Agent + Tailscale + Obscura APK 承载

## 架构总览

```
┌─────────────────────────────────────────────────────┐
│                   用户终端                            │
│  (手机/PC/平板 — 通过 Tailscale 组成安全网络)         │
└──────────┬──────────────────────────────────────────┘
           │ Tailscale Tailnet
           ▼
┌─────────────────────────────────────────────────────┐
│              CloudDrive Hub 核心节点                  │
│                                                     │
│  ┌─────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ rclone  │  │  FUSE    │  │  Operit Agent    │   │
│  │ 网盘驱动│─▶│ 本地挂载 │─▶│  AI 调度中枢     │   │
│  │ (50+种) │  │ /mnt/    │  │  · 文件管理      │   │
│  └─────────┘  └──────────┘  │  · 同步策略      │   │
│                              │  · 缓存管理      │   │
│  ┌─────────┐  ┌──────────┐  │  · 自动清理      │   │
│  │Tailscale│  │ Obscura  │  │  · 事件响应      │   │
│  │ 安全网络│─▶│ APK承载  │  └──────────────────┘   │
│  │ mesh VPN│  │ 浏览器&  │                         │
│  └─────────┘  │ 自动化   │                         │
│               └──────────┘                         │
└─────────────────────────────────────────────────────┘
```

## 核心能力

### 🔗 网盘聚合 (rclone)
- **50+ 云存储支持**：Google Drive、OneDrive、Dropbox、阿里云盘、百度网盘、WebDAV、S3 等
- **统一 FUSE 挂载**：所有网盘以本地目录形式呈现，路径为 `/mnt/cloud/{provider}/{path}`
- **透明缓存**：智能 LRU 缓存，支持按文件类型/大小配置缓存策略
- **并发限速**：每网盘独立带宽限制，避免单网盘拖垮整体

### 🤖 Operit Agent
- **AI 驱动文件管理**：自然语言操作文件（"把昨天的备份同步到百度网盘"）
- **智能调度**：根据网络状况、电量、时间自动调度同步任务
- **事件响应**：文件变更自动触发同步/备份/清理
- **Workflow 集成**：与 Operit Workflow 系统联动

### 🌐 Tailscale 网络
- **安全 Mesh VPN**：所有设备通过 Tailscale 组成私有网络
- **零配置穿透**：无需公网 IP，自动 NAT 穿透
- **专用子网路由**：通过 Tailscale 子网路由暴露挂载目录
- **ACL 控制**：基于标签的访问控制策略

### 📱 Obscura APK 承载
- **反检测浏览器**：绕过网盘/云存储的人机验证和反爬限制
- **自动化登录**：自动处理 OAuth 流程和 Cookie 刷新
- **会话管理**：多账号隔离，长会话维护
- **页面内 AI 操作**：通过 Page Agent 处理复杂交互

## 快速开始

### 前提条件
```bash
# 安装依赖
apt install -y rclone fuse3 tailscale openssl
# 确保 FUSE 已启用
modprobe fuse
```

### 配置网盘
```bash
# 交互式配置（rclone 标准流程）
rclone config

# 或使用配置文件
cp config/rclone.conf.example ~/.config/rclone/rclone.conf
```

### 启动挂载
```bash
# 一键挂载所有网盘
./scripts/mount_all.sh

# 挂载单个网盘
./scripts/mount.sh aliyundrive
```

### 启动 Operit Agent
```bash
# 启动 Agent 守护进程
python3 agent/main.py --config agent/config.yaml
```

## 项目结构

```
clouddrive-hub/
├── README.md                    # 项目文档
├── LICENSE                      
├── config/                      # 配置文件
│   ├── rclone.conf.example      # rclone 配置示例
│   ├── agent.yaml.example       # Agent 配置示例
│   └── tailscale/               # Tailscale 配置
├── scripts/                     # 运维脚本
│   ├── mount_all.sh             # 一键挂载所有网盘
│   ├── mount.sh                 # 挂载单个网盘
│   ├── umount.sh                # 卸载
│   ├── health_check.sh          # 健康检查
│   └── patrol.sh                # 巡检脚本（基于独立通道）
├── agent/                       # Operit Agent
│   ├── main.py                  # 入口
│   ├── orchestrator.py          # 调度中枢
│   ├── handlers/                # 事件处理器
│   │   ├── file_event.py        # 文件变更事件
│   │   ├── sync_event.py        # 同步事件
│   │   └── cleanup_event.py     # 清理事件
│   └── workflows/               # Workflow 定义
│       ├── auto_sync.yaml       # 自动同步
│       └── cleanup.yaml         # 自动清理
├── obscura/                     # Obscura 承载层
│   ├── auth_flow.py             # 自动化登录流程
│   ├── session_manager.py       # 会话管理
│   └── captcha_solver.py        # 验证码处理
├── tailscale/                   # Tailscale 网络层
│   ├── setup.sh                 # 安装配置脚本
│   ├── serve.sh                 # 暴露服务
│   └── acl.hujson               # ACL 策略
└── tools/                       # 独立通道工具
    ├── adb_server_shell         # 独立 ADB 通道
    ├── adb_connect              # 裸 ADB 协议客户端
    └── patrol.sh                # 巡检脚本
```

## 许可证

MIT
