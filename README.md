# CloudDrive Hub 🌐

> 开源网盘聚合挂载系统 — 站在社区巨人的肩膀上

## 核心理念

本项目**不自己造轮子**，而是把以下开源王牌项目通过胶水代码（glue code）整合：

| 组件 | 项目 | ⭐ | 作用 |
|------|------|:--:|------|
| **网盘聚合** | [Alist](https://github.com/AlistGo/alist) | 50k+ | 50+云存储 → WebDAV/HTTP API |
| **FUSE 挂载** | [rclone](https://github.com/rclone/rclone) | 50k+ | WebDAV → 本地文件系统 |
| **AI 调度** | Operit Agent | — | 自然语言控制、智能同步、事件响应 |
| **安全网络** | [Tailscale](https://github.com/tailscale/tailscale) | 22k+ | Mesh VPN，零配置穿透，私有访问 |
| **反检测** | Obscura | — | 自动化登录、反爬、验证码处理 |

## 架构

```
用户终端 (Tailscale Mesh)
  │
  ▼
CloudDrive Hub 核心
  ├── Alist (端口 5244) — 网盘聚合网关
  │   ├── 阿里云盘  ├── 百度网盘  ├── Google Drive
  │   ├── OneDrive  ├── 天翼云盘  ├── 123云盘
  │   └── ... 50+ 种存储
  │
  ├── rclone mount — FUSE 本地挂载
  │   └── WebDAV → /mnt/cloud/
  │
  ├── Operit Agent — AI 调度中枢
  │   ├── 自然语言文件管理
  │   ├── 智能同步调度
  │   ├── 缓存自动清理
  │   └── Workflow 集成
  │
  └── Obscura — 反检测承载层
      ├── 自动化登录 / Cookie 刷新
      └── 验证码处理 / 会话管理
```

## 快速开始

### 1. 安装 Alist
```bash
# 一键安装
curl -fsSL "https://alist.nn.ci/v3.sh" | bash -s install

# 或 Docker
docker run -d --restart=always -v /etc/alist:/opt/alist/data \
  -p 5244:5244 --name=alist xhofe/alist:latest
```

### 2. 配置网盘
在 Alist WebUI (http://localhost:5244) 添加存储驱动，支持：
阿里云盘 · 百度网盘 · Google Drive · OneDrive · 天翼云盘
123云盘 · PikPak · 夸克网盘 · 迅雷云盘 · 移动云盘 · S3

### 3. 挂载到本地
```bash
# 配置 rclone
rclone config create alist-webdav webdav \
  url=http://localhost:5244/dav \
  vendor=other user=admin \
  pass=$(rclone obscure "你的密码")

# 挂载
mkdir -p /mnt/cloud
rclone mount alist-webdav: /mnt/cloud --daemon \
  --vfs-cache-mode writes --allow-other
```

### 4. 启动 Agent
```bash
pip install -r agent/requirements.txt
python3 agent/main.py
```

### 5. Tailscale 远程访问
```bash
tailscale up --accept-routes
tailscale serve --bg 5244     # Alist WebUI
tailscale serve --bg /mnt/cloud  # 挂载目录
```

## 项目结构

```
clouddrive-hub/
├── README.md
├── scripts/
│   ├── setup.sh           # 一键部署
│   ├── mount.sh           # 挂载管理
│   └── patrol.sh          # 巡检脚本
├── agent/
│   ├── main.py            # AI 调度中枢
│   ├── orchestrator.py    # 工作流编排
│   └── handlers/          # 事件处理器
├── obscura/
│   ├── auth_flow.py       # 自动化登录
│   └── session_manager.py
├── tailscale/
│   ├── setup.sh
│   └── acl.hujson
└── config/
    ├── agent.yaml.example
    └── rclone.conf.example
```

## 社区项目

- [Alist](https://github.com/AlistGo/alist) — ⭐50k+ 多存储文件列表
- [rclone](https://github.com/rclone/rclone) — ⭐50k+ 云存储同步工具
- [Tailscale](https://github.com/tailscale/tailscale) — ⭐22k+ Mesh VPN
- [OpenList](https://github.com/OpenListTeam/OpenList) — ⭐24k+ Alist 分支

## License

MIT
