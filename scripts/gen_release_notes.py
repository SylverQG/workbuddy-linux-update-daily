#!/usr/bin/env python3
"""生成 GitHub Release 说明（Markdown）。

内容包含：deb / rpm 的 GitHub 下载与官方直链、SHA-256 校验值、官方核对渠道，
方便用户核对镜像文件与官方发布文件的一致性。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib

TZ_BEIJING = dt.timezone(dt.timedelta(hours=8))


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024:
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"


def build_time(meta: dict) -> str:
    ts = meta.get("timestamp")
    if not ts:
        return "未知"
    t = dt.datetime.fromtimestamp(int(ts), TZ_BEIJING)
    return t.strftime("%Y-%m-%d %H:%M") + "（北京时间）"


def package_section(title: str, meta: dict, asset: dict, api_url: str) -> str:
    sha = (meta.get("sha256hash") or "未知").lower()
    return f"""### {title}

| 项目 | 内容 |
| --- | --- |
| 版本 | `{meta.get('version', '未知')}` |
| 文件 | `{asset['fileName']}`（{human_size(asset['fileSize'])}） |
| SHA-256 | `{sha}` |
| 官方构建时间 | {build_time(meta)} |

- **GitHub 下载**：`{asset['fileName']}`（见本页底部 Assets）
- **官方直链**：{meta.get('url', '未知')}
- **官方更新接口**：{api_url}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deb", required=True, help="deb 官方元数据 JSON")
    parser.add_argument("--rpm", required=True, help="rpm 官方元数据 JSON")
    parser.add_argument("--assets", required=True, help="资产清单 JSON（文件名与大小）")
    parser.add_argument("--tag", required=True, help="Release 标签，如 v5.6.2")
    parser.add_argument("--deb-api", required=True)
    parser.add_argument("--rpm-api", required=True)
    parser.add_argument("--official-site", default="https://www.workbuddy.cn")
    parser.add_argument("--out", required=True, help="输出 Markdown 路径")
    args = parser.parse_args()

    deb = load_json(args.deb)
    rpm = load_json(args.rpm)
    assets = load_json(args.assets)

    notes = f"""# WorkBuddy {args.tag}

> 本 Release 由 GitHub Actions 每日自动检测 WorkBuddy 官方更新接口后发布。
> 安装包从官方 CDN 下载后**原样上传，未做任何修改**，SHA-256 与官方接口返回值一致，可放心核对。

## deb（Ubuntu / Debian）

{package_section('deb 安装包', deb, assets['deb'], args.deb_api)}

## rpm（Fedora / openSUSE / RHEL）

{package_section('rpm 安装包', rpm, assets['rpm'], args.rpm_api)}

## 如何校验文件

```bash
# 下载后计算哈希，与上表数值（或 checksums.txt）比对
sha256sum {assets['deb']['fileName']}
sha256sum {assets['rpm']['fileName']}
```

## 官方渠道核对

- 官方网站：{args.official_site}
- deb 更新接口：{args.deb_api}
- rpm 更新接口：{args.rpm_api}
- 项目主页（含版本历史与官方直链）：见仓库 README 与 GitHub Pages

> 免责声明：本仓库仅为个人维护的下载镜像与存档，软件版权归 WorkBuddy 官方所有，
> 使用前请以官方渠道的信息为准。
"""

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(notes, encoding="utf-8")
    print(f"已生成 {out}")


if __name__ == "__main__":
    main()
