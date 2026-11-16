#!/usr/bin/env python3
"""生成 GitHub Pages 静态数据：data/latest.json 与 data/releases.json。

数据来源：
- build/deb.json、build/rpm.json：官方更新接口元数据（工作流前置步骤抓取）
- build/assets.json：安装包文件名与大小（可选；跳过下载时缺省，
  此时文件名从官方直链推算、大小取自已有 Release 的同名资产）
- GitHub Releases：默认通过 gh api 拉取；本地调试可用 --releases-file 指定 JSON 文件
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import posixpath
import subprocess
import sys
import urllib.parse

TZ_BEIJING = dt.timezone(dt.timedelta(hours=8))


def load_json(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def now_bj() -> str:
    return dt.datetime.now(TZ_BEIJING).isoformat(timespec="seconds")


def build_time(meta: dict) -> str | None:
    ts = meta.get("timestamp")
    if not ts:
        return None
    return dt.datetime.fromtimestamp(int(ts), TZ_BEIJING).isoformat(timespec="seconds")


def fetch_releases(repo: str) -> list:
    """通过 gh api 拉取最近的 Releases；失败时返回空列表（不阻断部署）。"""
    try:
        proc = subprocess.run(
            ["gh", "api", f"repos/{repo}/releases?per_page=30"],
            capture_output=True, text=True, check=True,
        )
        return json.loads(proc.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"::warning::获取 Releases 失败，页面历史将为空：{exc}", file=sys.stderr)
        return []


def map_release(r: dict) -> dict:
    return {
        "tag": r.get("tag_name", ""),
        "name": r.get("name") or r.get("tag_name") or "",
        "url": r.get("html_url", ""),
        "publishedAt": r.get("published_at"),
        "assets": [
            {
                "name": a.get("name", ""),
                "size": a.get("size", 0),
                "downloadUrl": a.get("browser_download_url", ""),
            }
            for a in r.get("assets") or []
        ],
    }


def asset_url(release: dict | None, file_name: str, repo: str, tag: str) -> str:
    """优先使用真实 Release 资产地址；找不到时退回标准拼接规则。"""
    if release:
        for a in release["assets"]:
            if a["name"] == file_name:
                return a["downloadUrl"]
    return f"https://github.com/{repo}/releases/download/{tag}/{file_name}"


def url_basename(url: str) -> str:
    return posixpath.basename(urllib.parse.urlparse(url).path)


def package_entry(platform: str, meta: dict, asset: dict, api_url: str,
                  release: dict | None, repo: str, tag: str) -> dict:
    # 文件名优先取资产清单；跳过下载时从官方直链推算
    file_name = asset.get("fileName") or url_basename(meta.get("url", ""))

    # 大小优先取资产清单；跳过下载时取已有 Release 中同名资产的大小
    file_size = asset.get("fileSize")
    if file_size is None and release:
        for a in release["assets"]:
            if a["name"] == file_name:
                file_size = a["size"]
                break

    return {
        "platform": platform,
        "version": meta.get("version", ""),
        "fileName": file_name,
        "fileSize": file_size,
        "sha256": (meta.get("sha256hash") or "").lower(),
        "officialDownloadUrl": meta.get("url", ""),
        "officialApiUrl": api_url,
        "githubDownloadUrl": asset_url(release, file_name, repo, tag),
        "buildTime": build_time(meta),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--meta-dir", default="build", help="官方元数据与资产清单所在目录")
    parser.add_argument("--out", default="build/site", help="数据文件输出目录")
    parser.add_argument("--repo", required=True, help="GitHub 仓库，owner/name")
    parser.add_argument("--tag", required=True, help="本次检测对应的 Release 标签")
    parser.add_argument("--deb-api", required=True)
    parser.add_argument("--rpm-api", required=True)
    parser.add_argument("--official-site", default="https://www.workbuddy.cn")
    parser.add_argument("--assets-file", help="安装包清单 JSON（可选；不提供时从官方直链与 Release 资产推算）")
    parser.add_argument("--releases-file", help="调试用：从此 JSON 文件读取 Releases，而不调用 gh api")
    args = parser.parse_args()

    meta_dir = pathlib.Path(args.meta_dir)
    deb = load_json(meta_dir / "deb.json")
    rpm = load_json(meta_dir / "rpm.json")
    assets = load_json(pathlib.Path(args.assets_file)) if args.assets_file else {}

    if args.releases_file:
        raw = load_json(pathlib.Path(args.releases_file))
    else:
        raw = fetch_releases(args.repo)

    releases = [map_release(r) for r in raw if not r.get("draft") and not r.get("prerelease")]
    current = next((r for r in releases if r["tag"] == args.tag), None)

    latest = {
        "generatedAt": now_bj(),
        "officialSite": args.official_site,
        "repositoryUrl": f"https://github.com/{args.repo}",
        "checkSchedule": "每日北京时间 09:30 自动检测（cron: 30 1 * * * UTC）",
        "latestVersion": (current["tag"] if current else args.tag).lstrip("v"),
        "release": {
            "tag": args.tag,
            "url": (current and current["url"]) or f"https://github.com/{args.repo}/releases/tag/{args.tag}",
            "publishedAt": current.get("publishedAt") if current else None,
        },
        "packages": [
            package_entry("deb", deb, assets.get("deb") or {}, args.deb_api, current, args.repo, args.tag),
            package_entry("rpm", rpm, assets.get("rpm") or {}, args.rpm_api, current, args.repo, args.tag),
        ],
    }

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest.json").write_text(
        json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "releases.json").write_text(
        json.dumps(releases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成 {out / 'latest.json'} 与 {out / 'releases.json'}（共 {len(releases)} 条历史）")


if __name__ == "__main__":
    main()
