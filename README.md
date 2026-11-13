# WorkBuddy Linux 更新镜像（每日自动检测）

通过 **GitHub Actions** 每日定时检测 [WorkBuddy](https://www.workbuddy.cn) 官方更新接口，
自动把最新的 Linux 安装包（`deb` / `rpm`）镜像发布到本仓库的 **GitHub Releases**，
并通过 **GitHub Pages** 提供一个快速查阅下载链接与校验信息的页面。

![每日检测](../../actions/workflows/check-update.yml/badge.svg)

## 功能

- **每日检测**：北京时间每天 09:30（cron `30 1 * * *` UTC）请求官方更新接口：
  - deb：<https://www.workbuddy.cn/v2/update?platform=workbuddy-linux-x64-deb>
  - rpm：<https://www.workbuddy.cn/v2/update?platform=workbuddy-linux-x64-rpm>
- **有更新才发布**：接口返回的 `version` 对应的 Release（标签 `v<version>`）不存在时，
  自动下载安装包 → **校验 SHA-256**（与接口返回的 `sha256hash` 比对）→ 创建 Release 并附带：
  - `deb` / `rpm` 安装包（官方 CDN 原文件，未做任何修改）
  - `checksums.txt`（两个包的 SHA-256）
  - Release 说明：**官方下载直链**、SHA-256、官方接口地址，方便用户逐项核对
- **GitHub Pages**：自动部署前端页面，展示最新版本、GitHub/官方双下载链接、
  SHA-256、历史版本列表等（纯静态页 + 工作流生成的 JSON 数据，无需任何 API 调用）。

## 工作原理

```
定时触发 (cron) / 手动触发 (workflow_dispatch)
        │
        ▼
请求官方更新接口 (deb + rpm 元数据)
        │
        ▼
按 version 查找已有 Release ── 已存在 ──▶ 跳过发布（仅刷新 Pages 数据）
        │ 不存在
        ▼
下载 deb / rpm 官方安装包 → SHA-256 校验
        │
        ▼
创建 Release（安装包 + checksums.txt + 说明含官方直链）
        │
        ▼
生成 Pages 数据 (latest.json / releases.json) → 部署 GitHub Pages
```

## 使用方法

1. **创建仓库**：将本目录推送到一个 GitHub 仓库（建议 Public）：

   ```bash
   cd workbuddy-linux-update-daily
   git init -b main
   git add .
   git commit -m "feat: WorkBuddy Linux 更新镜像"
   # 用 gh 或在 GitHub 网页上创建空仓库后：
   git remote add origin git@github.com:<你的用户名>/workbuddy-linux-update-daily.git
   git push -u origin main
   ```

2. **手动跑一次验证**：仓库页 → Actions → *每日检测 WorkBuddy 更新* → *Run workflow*。
   首次运行会自动创建 Release 并部署 Pages。

3. **开启 GitHub Pages**（如自动启用失败）：
   仓库 → Settings → Pages → **Build and deployment → Source: GitHub Actions**。

4. 之后每天 09:30（北京时间）自动检测；有新版本才会产生新 Release。
   也可以在手动触发时勾选 **force_release**，删除并重建当前版本的 Release（用于修复）。

> 说明：工作流已通过顶层 `permissions:` 声明了 `contents: write`、`pages: write`、
> `id-token: write`，一般无需修改仓库默认工作流权限；若组织策略限制，请在
> Settings → Actions → General → Workflow permissions 中允许读写。

## 目录结构

```
├── .github/workflows/check-update.yml   # 每日检测 / 发布 / 部署 Pages 的主工作流
├── scripts/
│   ├── gen_release_notes.py             # 生成 Release 说明（含官方直链与 SHA-256）
│   └── build_site_data.py               # 生成 Pages 数据 latest.json / releases.json
├── public/                              # GitHub Pages 静态站点（部署时注入 data/*.json）
│   ├── index.html
│   └── assets/{style.css, app.js}
└── README.md
```

## 本地调试

```bash
mkdir -p /tmp/wbtest/build && cd /tmp/wbtest/build
curl -s "https://www.workbuddy.cn/v2/update?platform=workbuddy-linux-x64-deb" -o deb.json
curl -s "https://www.workbuddy.cn/v2/update?platform=workbuddy-linux-x64-rpm" -o rpm.json
echo '{"deb":{"fileName":"a.deb","fileSize":100},"rpm":{"fileName":"a.rpm","fileSize":100}}' > assets.json
echo '[]' > releases.json

cd <本项目目录>
python3 -I scripts/gen_release_notes.py --deb /tmp/wbtest/build/deb.json --rpm /tmp/wbtest/build/rpm.json \
  --assets /tmp/wbtest/build/assets.json --tag v5.6.2 --out /tmp/wbtest/notes.md
python3 -I scripts/build_site_data.py --meta-dir /tmp/wbtest/build --out /tmp/wbtest/site \
  --repo <你的用户名>/workbuddy-linux-update-daily --tag v5.6.2 \
  --deb-api "https://www.workbuddy.cn/v2/update?platform=workbuddy-linux-x64-deb" \
  --rpm-api "https://www.workbuddy.cn/v2/update?platform=workbuddy-linux-x64-rpm" \
  --releases-file /tmp/wbtest/build/releases.json
```

预览页面：

```bash
mkdir -p /tmp/wbtest/preview/data
cp -r public/. /tmp/wbtest/preview/
cp /tmp/wbtest/site/*.json /tmp/wbtest/preview/data/
cd /tmp/wbtest/preview && python3 -m http.server 8080
# 浏览器打开 http://127.0.0.1:8080
```

## 免责声明

本仓库仅为个人维护的**下载镜像与存档**，便于快速下载与版本追溯。
所有软件版权归 WorkBuddy 官方所有；安装包均直接取自官方 CDN 并附官方直链与 SHA-256 供核对，
请以官方渠道发布的信息为准。
