/* WorkBuddy Linux 更新镜像 — 前端逻辑
 * 数据文件由 GitHub Actions 工作流生成：data/latest.json 与 data/releases.json
 */
(async function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function fmtSize(n) {
    if (!Number.isFinite(n) || n <= 0) return "—";
    var units = ["B", "KiB", "MiB", "GiB"];
    var v = n, i = 0;
    while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
    return (i === 0 ? v : v.toFixed(1)) + " " + units[i];
  }

  function fmtTime(iso) {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleString("zh-CN", {
        timeZone: "Asia/Shanghai", hour12: false,
        year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit"
      });
    } catch (e) { return iso; }
  }

  function fetchJSON(url) {
    return fetch(url, { cache: "no-store" }).then(function (res) {
      if (!res.ok) throw new Error(url + " -> HTTP " + res.status);
      return res.json();
    });
  }

  function setStatus(kind, html) {
    var el = $("status");
    el.className = "status " + kind;
    el.innerHTML = '<span class="dot"></span><span>' + html + "</span>";
  }

  function card(p) {
    return '' +
      '<article class="card">' +
      '  <div class="card-head">' +
      '    <span class="badge badge-' + esc(p.platform) + '">' + esc(p.platform) + "</span>" +
      '    <span class="ver">v' + esc(p.version) + "</span>" +
      "  </div>" +
      '  <div class="card-actions">' +
      '    <a class="btn btn-primary" href="' + esc(p.githubDownloadUrl) + '" target="_blank" rel="noopener">GitHub 下载</a>' +
      '    <a class="btn btn-ghost" href="' + esc(p.officialDownloadUrl) + '" target="_blank" rel="noopener">官方直链 ↗</a>' +
      "  </div>" +
      '  <dl class="meta">' +
      '    <div><dt>文件</dt><dd class="mono">' + esc(p.fileName) + "</dd></div>" +
      '    <div><dt>大小</dt><dd>' + fmtSize(p.fileSize) + "</dd></div>" +
      '    <div><dt>构建时间</dt><dd>' + esc(fmtTime(p.buildTime)) + "</dd></div>" +
      '    <div><dt>官方接口</dt><dd><a class="link" href="' + esc(p.officialApiUrl) +
      '" target="_blank" rel="noopener">update?platform=…-' + esc(p.platform) + "</a></dd></div>" +
      '    <div class="hash"><dt>SHA-256</dt><dd class="mono hash-line"><span>' + esc(p.sha256) +
      '</span><button class="copy" data-copy="' + esc(p.sha256) + '">复制</button></dd></div>' +
      "  </dl>" +
      "</article>";
  }

  function renderLatest(latest) {
    var repo = latest.repositoryUrl || "#";
    $("nav-repo").href = repo;
    $("nav-releases").href = repo + "/releases";
    $("all-releases").href = repo + "/releases";
    $("footer-repo").textContent = repo;

    var byPlatform = {};
    (latest.packages || []).forEach(function (p) { byPlatform[p.platform] = p; });
    if (byPlatform.deb) $("link-deb-api").href = byPlatform.deb.officialApiUrl;
    if (byPlatform.rpm) $("link-rpm-api").href = byPlatform.rpm.officialApiUrl;

    $("packages").innerHTML = (latest.packages || []).map(card).join("");
    $("packages").hidden = false;

    Array.prototype.forEach.call(document.querySelectorAll("[data-copy]"), function (btn) {
      btn.addEventListener("click", function () { copyText(btn.getAttribute("data-copy"), btn); });
    });
  }

  function renderStatus(latest) {
    setStatus("is-ok",
      "最新版本 <strong>v" + esc(latest.latestVersion) + "</strong> · 最近检测：" +
      esc(fmtTime(latest.generatedAt)) + "（北京时间）");
  }

  function renderHistory(releases) {
    var el = $("history");
    if (!Array.isArray(releases) || releases.length === 0) {
      el.innerHTML = '<p class="muted">暂无历史版本记录。</p>';
      return;
    }
    var rows = releases.slice(0, 20).map(function (r) {
      var assets = r.assets || [];
      var deb = assets.filter(function (a) { return /\.deb$/i.test(a.name); })[0];
      var rpm = assets.filter(function (a) { return /\.rpm$/i.test(a.name); })[0];
      function dl(a) {
        return a ? '<a class="link" href="' + esc(a.downloadUrl) + '">下载</a>' : "—";
      }
      return "<tr>" +
        "<td><strong>" + esc(r.tag) + "</strong></td>" +
        "<td>" + esc(fmtTime(r.publishedAt)) + "</td>" +
        "<td>" + dl(deb) + "</td>" +
        "<td>" + dl(rpm) + "</td>" +
        '<td><a class="link" href="' + esc(r.url) + '">详情</a></td>' +
        "</tr>";
    }).join("");
    el.innerHTML =
      "<table><thead><tr><th>版本</th><th>发布时间（北京时间）</th><th>deb</th><th>rpm</th>" +
      "<th>Release</th></tr></thead><tbody>" + rows + "</tbody></table>";
  }

  function copyText(text, btn) {
    function done() {
      var old = btn.textContent;
      btn.textContent = "已复制 ✓";
      setTimeout(function () { btn.textContent = old; }, 1200);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallback(); });
    } else { fallback(); }
    function fallback() {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch (e) { /* 忽略 */ }
      ta.remove();
      done();
    }
  }

  var results = await Promise.allSettled([
    fetchJSON("data/latest.json"),
    fetchJSON("data/releases.json")
  ]);

  var latestRes = results[0], releasesRes = results[1];

  if (latestRes.status === "fulfilled") {
    try {
      renderLatest(latestRes.value);
      renderStatus(latestRes.value);
    } catch (e) {
      setStatus("is-error", "数据渲染失败：" + esc(e.message));
    }
  } else {
    setStatus("is-error",
      "暂无检测数据：请确认 Actions 工作流已运行，且已在 Settings → Pages 将 Source 设为 <strong>GitHub Actions</strong>。");
  }

  if (releasesRes.status === "fulfilled") {
    renderHistory(releasesRes.value);
  } else {
    $("history").innerHTML = '<p class="muted">历史数据尚未生成。</p>';
  }
})();
