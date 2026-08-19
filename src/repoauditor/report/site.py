"""Multi-page static report: dashboard + repo pages + person pages."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from repoauditor import PRIVACY
from repoauditor.auditor.schema import CHECKLIST_IDS
from repoauditor.auditor.score import (
    SCORED_IDS,
    TAGS,
    inspector_score,
    item_status,
    repo_tag_scores,
    rubric_label,
)
from repoauditor.report.charts import bar_chart, day_heatmap, esc
from repoauditor.report.format import compact_number, display_date, name_from_key

REPO_DEFAULT_COLS = ("repo", "score", "tags", "last", "commits", "humans", "churn", "flags")
PEOPLE_DEFAULT_COLS = ("name", "first", "last", "commits", "churn", "days")

CSS = """
:root { --ink:#142017; --muted:#5c6b60; --line:#d5ddd7; --bg:#f6f8f6; --card:#fff;
        --ok:#1b7f4e; --concern:#b45309; --unknown:#8a938c; --head:#0f3d24; }
* { box-sizing:border-box; }
body { margin:0; font:15px/1.45 ui-sans-serif,system-ui,sans-serif; color:var(--ink); background:var(--bg); }
a { color:#0b5c38; }
header { background:var(--head); color:#fff; padding:1rem 1.5rem; }
header a { color:#fff; text-decoration:none; font-weight:650; }
header .meta { opacity:.85; font-size:.9rem; margin-top:.25rem; }
main { padding:1.25rem 1.5rem 3rem; max-width:1400px; }
h1,h2,h3 { font-weight:650; }
h1 { font-size:1.4rem; margin:.2rem 0 1rem; }
h2 { font-size:1.15rem; margin:1.6rem 0 .6rem; }
.stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:.6rem; }
.stat { background:var(--card); border:1px solid var(--line); padding:.75rem; }
.stat b { display:block; font-size:1.4rem; }
.stat span { color:var(--muted); font-size:.85rem; }
.kvs { display:grid; grid-template-columns:repeat(auto-fill,minmax(9.5rem,1fr)); gap:.5rem; }
.kv { border:1px solid var(--line); background:#fff; padding:.55rem .6rem; }
.kv b { display:block; font-size:1.15rem; overflow-wrap:anywhere; word-break:break-word; }
.kv span { color:var(--muted); font-size:.8rem; }
.card { background:var(--card); border:1px solid var(--line); padding:1rem; margin:1rem 0; }
.card > h2 { margin:.15rem 0 .7rem; }
.muted { color:var(--muted); }
table { border-collapse:collapse; width:100%; background:var(--card); font-size:.86rem; }
th,td { border-bottom:1px solid var(--line); padding:.4rem .5rem; text-align:left; vertical-align:top; }
th { cursor:pointer; user-select:none; background:#eef3ef; white-space:nowrap; }
th[aria-sort="asc"]::after { content:" \\25B2"; }
th[aria-sort="desc"]::after { content:" \\25BC"; }
tr:hover td { background:#f3f7f4; }
.chart { width:100%; height:168px; background:#fff; display:block; }
.chart-label { font-size:10px; fill:#5c6b60; }
.chart-zoom { position:relative; }
.chart-help { margin:.2rem 0 .4rem; }
.chart-tools { display:flex; gap:.6rem; align-items:center; min-height:1.6rem; margin-bottom:.3rem; }
.chart-reset { border:1px solid var(--line); background:#fff; padding:.2rem .55rem; cursor:pointer; font:inherit; }
.chart-stage { position:relative; user-select:none; }
.chart-stage .chart { cursor:crosshair; }
.chart-brush { position:absolute; top:12px; bottom:28px; background:rgba(11,92,56,.12); border:1px solid #0b5c38; pointer-events:none; }
.minis { display:flex; gap:4px; min-width:140px; }
.mini { flex:1; background:#e6eee8; height:18px; position:relative; display:block; }
.mini i { display:block; height:100%; background:var(--ok); }
.mini em { position:absolute; inset:0; font-style:normal; font-size:10px; text-align:center; line-height:18px; }
.mini-tags { display:inline-flex; gap:2px; align-items:center; flex-wrap:nowrap; }
.mini-tags i { width:10px; height:10px; display:inline-block; background:#e8ece9; }
.mini-tags i.ok { background:#1b7f4e; }
.mini-tags i.concern { background:#e6a23c; }
.mini-tags em { font-style:normal; font-size:.8rem; margin-left:.35rem; }
.scorecard { display:grid; grid-template-columns:repeat(auto-fill,minmax(10.5rem,1fr)); gap:6px; }
.box { border:1px solid var(--line); padding:.45rem .5rem; font-size:.78rem; background:#fff; min-height:3.4rem; }
.box.ok { border-color:#9dceb3; background:#f1faf5; }
.box.concern { border-color:#e8b86d; background:#fff7ed; }
.box.unknown { color:var(--muted); }
.box .id { display:block; font-weight:650; overflow-wrap:anywhere; word-break:break-word; line-height:1.25; }
.heatmap-wrap { overflow-x:auto; max-width:100%; padding-bottom:.4rem; }
.heatmap { display:grid; grid-auto-flow:column; grid-template-rows:16px repeat(7,10px); gap:2px; width:max-content; }
.heat { width:10px; height:10px; background:#e8ece9; }
.heat-label { font-size:9px; color:var(--muted); line-height:16px; white-space:nowrap; overflow:visible; }
.heat.l1 { background:#c6e6d4; }
.heat.l2 { background:#7dc49c; }
.heat.l3 { background:#3a9a68; }
.heat.l4 { background:#1b7f4e; }
.finding { border:1px solid var(--line); padding:.8rem; margin:.8rem 0; background:#fff; }
.finding .when { color:var(--muted); font-size:.9rem; }
table.grid th.col-hidden, table.grid td.col-hidden { display:none; }
.col-bar { display:flex; flex-wrap:wrap; gap:.4rem; align-items:center; margin:.4rem 0 .6rem; font-size:.82rem; }
.col-bar label { display:inline-flex; gap:.25rem; align-items:center; background:#fff; border:1px solid var(--line); padding:.15rem .4rem; }
.col-reset { border:1px solid var(--line); background:#fff; padding:.2rem .55rem; cursor:pointer; font:inherit; }
.table-wrap { overflow-x:auto; max-width:100%; }
.prose { white-space:pre-wrap; }
.check { margin:.8rem 0; padding:.7rem; background:#fff; border:1px solid var(--line); }
.check.concern { border-left:4px solid var(--concern); }
footer { color:var(--muted); font-size:.8rem; padding:0 1.5rem 2rem; }
"""

JS = """
function applyCols(table) {
  const show = new Set(
    [...table.tHead.rows[0].cells]
      .filter((th) => !th.classList.contains("col-hidden"))
      .map((th) => th.dataset.col)
  );
  [...table.tHead.rows[0].cells].forEach((th) => {
    th.classList.toggle("col-hidden", !show.has(th.dataset.col));
  });
  [...table.tBodies[0].rows].forEach((row) => {
    [...row.cells].forEach((td) => {
      td.classList.toggle("col-hidden", !show.has(td.dataset.col));
    });
  });
  const key = "ra-cols-v3-" + (table.dataset.table || "");
  if (table.dataset.table) localStorage.setItem(key, JSON.stringify([...show]));
}

function cellVal(row, col) {
  const td = [...row.cells].find((c) => c.dataset.col === col);
  return td ? (td.dataset.sort ?? td.innerText) : "";
}

document.querySelectorAll("table.sortable").forEach((table) => {
  const heads = () => [...table.tHead.rows[0].cells];
  const stored = table.dataset.table && localStorage.getItem("ra-cols-v3-" + table.dataset.table);
  if (stored) {
    try {
      const show = new Set(JSON.parse(stored));
      heads().forEach((th) => th.classList.toggle("col-hidden", !show.has(th.dataset.col)));
    } catch (e) {}
  }
  applyCols(table);
  heads().forEach((th) => {
    th.addEventListener("click", () => {
      const col = th.dataset.col;
      const type = th.dataset.type || "str";
      const body = table.tBodies[0];
      const rows = [...body.rows];
      const next = th.getAttribute("aria-sort") === "asc" ? "desc" : "asc";
      heads().forEach((h) => h.removeAttribute("aria-sort"));
      th.setAttribute("aria-sort", next);
      const dir = next === "asc" ? 1 : -1;
      rows.sort((a, b) => {
        const av = cellVal(a, col);
        const bv = cellVal(b, col);
        if (type === "num") {
          const an = av === "" || av === undefined ? null : Number(av);
          const bn = bv === "" || bv === undefined ? null : Number(bv);
          const aOk = an !== null && Number.isFinite(an);
          const bOk = bn !== null && Number.isFinite(bn);
          if (!aOk && !bOk) return 0;
          if (!aOk) return 1;
          if (!bOk) return -1;
          return dir * (an - bn);
        }
        return dir * String(av).localeCompare(String(bv), undefined, { numeric: true });
      });
      rows.forEach((row) => body.appendChild(row));
    });
    th.draggable = true;
    th.addEventListener("dragstart", (ev) => ev.dataTransfer.setData("text/col", th.dataset.col));
    th.addEventListener("dragover", (ev) => ev.preventDefault());
    th.addEventListener("drop", (ev) => {
      ev.preventDefault();
      const fromCol = ev.dataTransfer.getData("text/col");
      const toCol = th.dataset.col;
      if (!fromCol || fromCol === toCol) return;
      const move = (row) => {
        const cells = [...row.cells];
        const from = cells.find((c) => c.dataset.col === fromCol);
        const to = cells.find((c) => c.dataset.col === toCol);
        if (!from || !to) return;
        if (cells.indexOf(from) < cells.indexOf(to)) to.after(from);
        else to.before(from);
      };
      move(table.tHead.rows[0]);
      [...table.tBodies[0].rows].forEach(move);
    });
  });
  const wrap = table.parentElement;
  const bar = document.querySelector('.col-bar[data-for="' + (table.dataset.table || "") + '"]')
    || (wrap && wrap.classList.contains("table-wrap") ? wrap.previousElementSibling : table.previousElementSibling);
  if (bar && bar.classList.contains("col-bar")) {
    bar.querySelectorAll("input[type=checkbox]").forEach((box) => {
      const th = heads().find((h) => h.dataset.col === box.value);
      box.checked = Boolean(th && !th.classList.contains("col-hidden"));
      box.addEventListener("click", (ev) => ev.stopPropagation());
      box.addEventListener("change", () => {
        const head = heads().find((h) => h.dataset.col === box.value);
        if (!head) return;
        head.classList.toggle("col-hidden", !box.checked);
        applyCols(table);
      });
    });
    const reset = bar.querySelector(".col-reset");
    if (reset) {
      reset.addEventListener("click", () => {
        const order = (bar.dataset.defaults || "").split(",").filter(Boolean);
        bar.querySelectorAll("input[type=checkbox]").forEach((box) => {
          box.checked = box.defaultChecked;
        });
        const orderAll = order.concat(
          heads().map((h) => h.dataset.col).filter((c) => c && !order.includes(c))
        );
        const applyOrder = (row) => {
          orderAll.forEach((col) => {
            const cell = [...row.cells].find((c) => c.dataset.col === col);
            if (cell) row.appendChild(cell);
          });
        };
        applyOrder(table.tHead.rows[0]);
        [...table.tBodies[0].rows].forEach(applyOrder);
        heads().forEach((h) => {
          const box = bar.querySelector('input[type=checkbox][value="' + h.dataset.col + '"]');
          const on = box ? box.defaultChecked : !h.classList.contains("col-hidden");
          h.classList.toggle("col-hidden", !on);
        });
        applyCols(table);
      });
    }
  }
});

(function () {
  const W = 720, H = 168, L = 42, R = 10, T = 12, B = 28;
  function compact(n) {
    const a = Math.abs(n);
    if (a < 1000) return String(n);
    if (a >= 1e6) return (n / 1e6).toPrecision(3).replace(/\\.0+$/, "") + "M";
    return (n / 1e3).toPrecision(3).replace(/\\.0+$/, "") + "K";
  }
  function shortX(label) {
    const t = String(label);
    if (t.length <= 10) return t;
    if (t[4] === "-" && t.indexOf("T") !== -1) return t.slice(0, 10);
    return t.slice(0, 10);
  }
  function xTicks(n) {
    if (n <= 1) return [0];
    if (n <= 6) return [...Array(n).keys()];
    return [...new Set([0, Math.floor(n / 4), Math.floor(n / 2), Math.floor((3 * n) / 4), n - 1])].sort((a, b) => a - b);
  }
  function yTicks(peak) {
    if (peak <= 1) return [0, 1];
    const mid = Math.max(1, Math.round(peak / 2));
    return mid === peak ? [0, peak] : [0, mid, peak];
  }
  function draw(stage, rows, lo, hi) {
    const slice = rows.slice(lo, hi + 1);
    if (!slice.length) return;
    const peak = Math.max(...slice.map((r) => r[1])) || 1;
    const innerW = W - L - R;
    const innerH = H - T - B;
    const n = slice.length;
    const gap = n > 80 ? 2 : 3;
    const barW = Math.max(2, Math.floor((innerW - gap * (n + 1)) / n));
    let bars = "";
    slice.forEach((row, i) => {
      const h = row[1] ? Math.floor(innerH * (row[1] / peak)) : 0;
      const x = L + gap + i * (barW + gap);
      const y = T + (innerH - h);
      bars += '<rect class="chart-bar" data-i="' + (lo + i) + '" x="' + x + '" y="' + y +
        '" width="' + barW + '" height="' + h + '" fill="#1b7f4e"><title>' +
        row[0] + ": " + row[1] + "</title></rect>";
    });
    let axis = '<line x1="' + L + '" y1="' + T + '" x2="' + L + '" y2="' + (T + innerH) +
      '" stroke="#d5ddd7"/><line x1="' + L + '" y1="' + (T + innerH) + '" x2="' + (W - R) +
      '" y2="' + (T + innerH) + '" stroke="#d5ddd7"/>';
    yTicks(peak).forEach((value) => {
      const y = T + innerH - Math.floor(innerH * (value / peak));
      axis += '<line x1="' + (L - 3) + '" y1="' + y + '" x2="' + L + '" y2="' + y +
        '" stroke="#8a938c"/><text x="' + (L - 6) + '" y="' + (y + 3) +
        '" text-anchor="end" class="chart-label">' + compact(value) + "</text>";
    });
    let labels = "";
    xTicks(n).forEach((i) => {
      const x = L + gap + i * (barW + gap) + barW / 2;
      labels += '<text x="' + x.toFixed(1) + '" y="' + (H - 8) +
        '" text-anchor="middle" class="chart-label">' + shortX(slice[i][0]) + "</text>";
    });
    stage.innerHTML = '<svg class="chart" viewBox="0 0 ' + W + " " + H +
      '" role="img" aria-label="Activity bars" data-lo="' + lo + '" data-hi="' + hi + '">' +
      axis + bars + labels + "</svg>";
  }
  function indexAt(svg, clientX, n) {
    const rect = svg.getBoundingClientRect();
    const x = ((clientX - rect.left) / rect.width) * W;
    const innerW = W - L - R;
    const t = Math.min(1, Math.max(0, (x - L) / innerW));
    return Math.min(n - 1, Math.max(0, Math.floor(t * n)));
  }
  document.querySelectorAll(".chart-zoom").forEach((box) => {
    const dataEl = box.querySelector(".chart-data");
    const stage = box.querySelector(".chart-stage");
    const reset = box.querySelector(".chart-reset");
    const win = box.querySelector(".chart-window");
    if (!dataEl || !stage) return;
    let rows;
    try { rows = JSON.parse(dataEl.textContent || "[]"); } catch (e) { return; }
    if (!rows.length) return;
    let brush = null;
    function showRange(lo, hi) {
      if (win) win.textContent = rows[lo][0] + " → " + rows[hi][0];
      if (reset) reset.hidden = lo === 0 && hi === rows.length - 1;
    }
    const first = stage.querySelector("svg");
    if (first) showRange(0, rows.length - 1);
    if (reset) {
      reset.addEventListener("click", () => {
        draw(stage, rows, 0, rows.length - 1);
        showRange(0, rows.length - 1);
      });
    }
    let drag = null;
    stage.addEventListener("mousedown", (ev) => {
      const svg = stage.querySelector("svg");
      if (!svg || ev.button !== 0) return;
      ev.preventDefault();
      const start = indexAt(svg, ev.clientX, rows.length);
      drag = { start, from: ev.clientX };
      brush = document.createElement("div");
      brush.className = "chart-brush";
      const boxR = stage.getBoundingClientRect();
      brush.style.left = (ev.clientX - boxR.left) + "px";
      brush.style.width = "0px";
      stage.appendChild(brush);
    });
    window.addEventListener("mousemove", (ev) => {
      if (!drag || !brush) return;
      const boxR = stage.getBoundingClientRect();
      const a = Math.min(drag.from, ev.clientX) - boxR.left;
      const b = Math.max(drag.from, ev.clientX) - boxR.left;
      brush.style.left = Math.max(0, a) + "px";
      brush.style.width = Math.max(2, b - a) + "px";
    });
    window.addEventListener("mouseup", (ev) => {
      if (!drag) return;
      const svg = stage.querySelector("svg");
      if (brush) brush.remove();
      brush = null;
      const start = drag.start;
      drag = null;
      if (!svg) return;
      const end = indexAt(svg, ev.clientX, rows.length);
      const lo = Math.min(start, end);
      const hi = Math.max(start, end);
      if (hi - lo < 1) return;
      draw(stage, rows, lo, hi);
      showRange(lo, hi);
    });
  });
})();
"""


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return (cleaned[:80] or "item")


def _page(
    title: str,
    body: str,
    *,
    asset_prefix: str,
    as_of: date,
    input_path: str,
    since: date | None = None,
) -> str:
    home = f"{asset_prefix}index.html" if asset_prefix else "index.html"
    window = f"as-of {as_of.isoformat()}"
    if since:
        window = f"since {since.isoformat()} · {window}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{esc(title)}</title>
  <link rel="stylesheet" href="{asset_prefix}assets/style.css">
</head>
<body>
  <header>
    <a href="{home}">RepoAuditor</a>
    <div class="meta">Input <code>{esc(input_path)}</code> · {window} · commit authors</div>
  </header>
  <main>{body}</main>
  <footer>{esc(PRIVACY)}</footer>
  <script src="{asset_prefix}assets/tables.js"></script>
</body>
</html>
"""


def _activity_pairs(items: list[dict], key: str) -> list[tuple[str, int]]:
    return [(str(row.get(key) or ""), int(row.get("count") or 0)) for row in items]


def _day_map(items: list[dict] | None) -> dict[str, int]:
    return {str(row.get("date")): int(row.get("count") or 0) for row in items or [] if row.get("date")}


def _dashboard_series(repos: list[dict]) -> list[tuple[str, int]]:
    weeks: dict[str, int] = {}
    months: dict[str, int] = {}
    for repo in repos:
        for row in repo.get("activity_by_week") or []:
            weeks[row["week"]] = weeks.get(row["week"], 0) + int(row.get("count") or 0)
        for row in repo.get("activity_by_month") or []:
            months[row["month"]] = months.get(row["month"], 0) + int(row.get("count") or 0)
    if len(weeks) <= 26:
        return [(k, weeks[k]) for k in sorted(weeks)]
    return [(k, months[k]) for k in sorted(months)]


def _analysis_by_repo(analysis: list[dict]) -> dict[str, dict]:
    return {row.get("repo_id"): row for row in analysis if row.get("repo_id")}


def _status_for(item: dict | None) -> str:
    return item_status(item)


def _tag_strip(report: dict | None) -> str:
    scores = repo_tag_scores(report)
    total = inspector_score(report)
    bits = []
    for cid in SCORED_IDS:
        value = scores[cid]
        if value is None:
            cls = ""
        elif value < 0:
            cls = "concern"
        elif value > 0:
            cls = "ok"
        else:
            cls = ""
        bits.append(
            f'<i class="{cls}" title="{esc(cid)}: {esc(TAGS.get(cid, cid))} ({value if value is not None else "—"})"></i>'
        )
    label = "—" if total is None else total
    return f'<span class="mini-tags">{"".join(bits)}<em>{esc(label)}</em></span>'


def _scorecard(report: dict | None) -> str:
    by_id = {item.get("id"): item for item in (report or {}).get("checklist") or []}
    total = inspector_score(report)
    if report and report.get("analyze_error"):
        heading = (
            f'<p class="muted">Analyze did not finish: '
            f"<code>{esc(str(report.get('analyze_error'))[:400])}</code></p>"
        )
    elif total is not None:
        heading = (
            f'<p class="muted">score <strong>{esc(total)}</strong> '
            f"(+1 ok / 0 cannot tell / −1 concern). Sum of the 14 scored tags.</p>"
        )
    else:
        heading = '<p class="muted">No inspector score yet (analyze still running or --no-analyze).</p>'
    boxes = []
    for cid in CHECKLIST_IDS:
        item = by_id.get(cid)
        status = _status_for(item)
        label = {"ok": "ok", "concern": "concern", "unknown": "cannot tell"}[status]
        tag = TAGS.get(cid, cid)
        boxes.append(
            f'<div class="box {status}" title="{esc(tag)}">'
            f'<span class="id">{esc(rubric_label(cid))}</span>{esc(label)}</div>'
        )
    return f"{heading}<div class=\"scorecard\">{''.join(boxes)}</div>"


def _kv_cell(label: str, value: object, typ: str = "num") -> str:
    if typ == "num":
        shown = compact_number(value)
    elif typ == "date":
        shown = display_date(value)
    elif value is None or value == "":
        shown = "—"
    else:
        shown = esc(value)
    return f'<div class="kv"><b>{shown}</b><span>{esc(label)}</span></div>'


def _kv_card(title: str, rows: list[tuple[str, object, str]]) -> str:
    cells = "".join(_kv_cell(label, value, typ) for label, value, typ in rows)
    return f'<section class="card"><h2>{esc(title)}</h2><div class="kvs">{cells}</div></section>'


def _th(label: str, col: str, typ: str = "num", *, visible: bool = True, sort: str | None = None) -> str:
    hidden = "" if visible else " col-hidden"
    aria = f' aria-sort="{esc(sort)}"' if sort else ""
    return (
        f'<th class="{hidden.strip()}" data-col="{esc(col)}" data-type="{esc(typ)}"{aria}>'
        f"{esc(label)}</th>"
    )


def _td(
    value: object,
    *,
    href: str | None = None,
    typ: str = "num",
    col: str = "",
    visible: bool = True,
) -> str:
    raw = "" if value is None else value
    if typ == "num":
        shown = compact_number(value)
        sort = raw
    elif typ == "date":
        shown = display_date(value)
        sort = raw
    else:
        shown = esc(raw)
        sort = raw
    if href:
        shown = f'<a href="{esc(href)}">{shown}</a>'
    hidden = "" if visible else " col-hidden"
    return (
        f'<td class="{hidden.strip()}" data-col="{esc(col)}" data-sort="{esc(sort)}" '
        f'data-type="{esc(typ)}">{shown}</td>'
    )


def _col_bar(columns: list[tuple[str, str]], default: set[str], table_id: str = "") -> str:
    boxes = []
    for col, label in columns:
        checked = " checked" if col in default else ""
        boxes.append(
            f'<label><input type="checkbox" value="{esc(col)}"{checked}>{esc(label)}</label>'
        )
    defaults = ",".join(col for col, _label in columns if col in default)
    return (
        f'<div class="col-bar" data-for="{esc(table_id)}" data-defaults="{esc(defaults)}">'
        f"Columns {''.join(boxes)}"
        f'<button type="button" class="col-reset">Reset columns</button></div>'
    )


def write_report(
    out_dir: Path,
    repos: list[dict],
    people: list[dict],
    findings: list[dict],
    as_of: date,
    input_path: str,
    analysis: list[dict] | None = None,
    assistance: dict | None = None,
    executive: dict | None = None,
    rankings: dict | None = None,
    since: date | None = None,
) -> Path:
    del rankings
    root = out_dir / "report"
    (root / "assets").mkdir(parents=True, exist_ok=True)
    (root / "repos").mkdir(parents=True, exist_ok=True)
    (root / "people").mkdir(parents=True, exist_ok=True)
    for folder in (root / "repos", root / "people"):
        for leftover in folder.glob("*.html"):
            leftover.unlink()
    (root / "assets" / "style.css").write_text(CSS, encoding="utf-8")
    (root / "assets" / "tables.js").write_text(JS, encoding="utf-8")

    analysis = analysis or []
    humans = [p for p in people if not p.get("is_bot")]
    repo_slugs = {repo["repo_id"]: slug(repo["repo_id"]) for repo in repos}
    person_slugs = {p["identity_key"]: slug(p["identity_key"]) for p in humans}
    findings_by_repo: dict[str, list[dict]] = {}
    findings_by_person: dict[str, list[dict]] = {}
    for finding in findings:
        if finding.get("lens") == "repo":
            findings_by_repo.setdefault(finding.get("subject_id") or "", []).append(finding)
        elif finding.get("lens") == "person":
            findings_by_person.setdefault(finding.get("subject_id") or "", []).append(finding)
    analysis_map = _analysis_by_repo(analysis)

    index = _dashboard_html(
        repos,
        humans,
        findings,
        as_of,
        input_path,
        analysis_map,
        assistance or {},
        executive,
        repo_slugs,
        person_slugs,
        findings_by_repo,
        since=since,
    )
    (root / "index.html").write_text(index, encoding="utf-8")

    for repo in repos:
        page = _repo_page(
            repo,
            humans,
            findings_by_repo.get(repo["repo_id"]) or [],
            analysis_map.get(repo["repo_id"]),
            as_of,
            input_path,
            person_slugs,
            since=since,
        )
        (root / "repos" / f"{repo_slugs[repo['repo_id']]}.html").write_text(page, encoding="utf-8")

    for person in humans:
        page = _person_page(
            person,
            repos,
            as_of,
            input_path,
            repo_slugs,
            findings_by_person.get(person["identity_key"]) or [],
            since=since,
        )
        (root / "people" / f"{person_slugs[person['identity_key']]}.html").write_text(
            page, encoding="utf-8"
        )
    return root / "index.html"


def render_html(
    repos: list[dict],
    people: list[dict],
    rankings: dict,
    findings: list[dict],
    as_of: date,
    input_path: str,
    analysis: list[dict] | None = None,
    assistance: dict | None = None,
    executive: dict | None = None,
) -> str:
    # Tests and callers that only want the dashboard string.
    humans = [p for p in people if not p.get("is_bot")]
    repo_slugs = {repo["repo_id"]: slug(repo["repo_id"]) for repo in repos}
    person_slugs = {p["identity_key"]: slug(p["identity_key"]) for p in humans}
    findings_by_repo: dict[str, list[dict]] = {}
    for finding in findings:
        if finding.get("lens") == "repo":
            findings_by_repo.setdefault(finding.get("subject_id") or "", []).append(finding)
    return _dashboard_html(
        repos,
        humans,
        findings,
        as_of,
        input_path,
        _analysis_by_repo(analysis or []),
        assistance or {},
        executive,
        repo_slugs,
        person_slugs,
        findings_by_repo,
    )


def _dashboard_html(
    repos: list[dict],
    humans: list[dict],
    findings: list[dict],
    as_of: date,
    input_path: str,
    analysis_map: dict[str, dict],
    assistance: dict,
    executive: dict | None,
    repo_slugs: dict[str, str],
    person_slugs: dict[str, str],
    findings_by_repo: dict[str, list[dict]],
    since: date | None = None,
) -> str:
    commits = sum(int(r.get("commit_count") or 0) for r in repos)
    stats = (
        '<div class="stats">'
        f'<div class="stat"><b>{compact_number(len(humans))}</b><span>human contributors</span></div>'
        f'<div class="stat"><b>{compact_number(commits)}</b><span>commits</span></div>'
        f'<div class="stat"><b>{compact_number(len(repos))}</b><span>repos scanned</span></div>'
        f'<div class="stat"><b>{compact_number(len(findings))}</b><span>flags</span></div>'
        "</div>"
    )
    chart = bar_chart(_dashboard_series(repos))
    repo_table = _repo_table(repos, repo_slugs, findings_by_repo, analysis_map)
    people_table = _people_table(humans, person_slugs)
    cards = []
    for repo in repos:
        cards.append(
            '<section class="card">'
            f"<h3><a href=\"repos/{repo_slugs[repo['repo_id']]}.html\">{esc(repo['repo_id'])}</a></h3>"
            f"{_scorecard(analysis_map.get(repo['repo_id']))}"
            "</section>"
        )
    assist_rows = "".join(
        "<tr>"
        f"<td>{esc(row.get('id'))}</td>"
        f"<td>{esc(row.get('commit_count'))}</td>"
        f"<td>{esc(row.get('repo_count'))}</td>"
        "</tr>"
        for row in assistance.get("assistants") or []
    )
    assist_html = (
        "<h2>Coding assistance</h2>"
        + (
            f"<table><thead><tr><th>assistant</th><th>commits</th><th>repos</th></tr></thead>"
            f"<tbody>{assist_rows}</tbody></table>"
            if assist_rows
            else "<p class=\"muted\">No assistant fingerprints.</p>"
        )
    )
    body = f"""
    <h1>Department dashboard</h1>
    {stats}
    <section class="card">
      <h2>Activity</h2>
      {chart}
    </section>
    <h2>Repos</h2>
    <p class="muted">Repos default to <strong>score</strong>, lowest first (most concern). Click <strong>score</strong> to flip. Tag columns use the same names as the scorecard. Rubric: notes/WIKI/scoring.md.</p>
    {repo_table}
    <h2>People</h2>
    <p class="muted">No single winner. Commits, churn, and distinct days are separate columns.</p>
    {people_table}
    <h2>Inspector scorecards</h2>
    <p class="muted">concern / ok / cannot tell. Written answers are on the repo page. Empty when scan used --no-analyze.</p>
    {''.join(cards) or '<p class="muted">No repos.</p>'}
    {assist_html}
    """
    return _page(
        "RepoAuditor dashboard",
        body,
        asset_prefix="",
        as_of=as_of,
        input_path=input_path,
        since=since,
    )


def _repo_table(
    repos: list[dict],
    slugs: dict[str, str],
    findings_by_repo: dict[str, list[dict]],
    analysis_map: dict[str, dict],
) -> str:
    spec = [
        ("repo", "repo", "str"),
        ("score", "score", "num"),
        ("tags", "tags", "str"),
        ("last", "last commit", "date"),
        ("commits", "commits", "num"),
        ("humans", "humans", "num"),
        ("churn", "churn", "num"),
        ("branches", "branches", "num"),
        ("flags", "flags", "num"),
        ("head", "head", "str"),
        ("first", "first commit", "date"),
        ("bots", "bots", "num"),
        ("add", "additions", "num"),
        ("del", "deletions", "num"),
        ("net", "net", "num"),
        ("files", "files", "num"),
        ("paths", "unique paths", "num"),
        ("merges", "merges", "num"),
        ("bin", "binaries", "num"),
        ("git-tags", "git tags", "num"),
        ("remotes", "remotes", "num"),
        ("headfiles", "HEAD files", "num"),
        ("occ", "occupancy days", "num"),
        ("weeks", "active weeks", "num"),
        ("weekday", "weekday", "num"),
        ("weekend", "weekend", "num"),
        ("maxc", "max churn", "num"),
        ("meanc", "mean churn", "num"),
        ("cpd", "commits/day", "num"),
        ("concerns", "concerns", "num"),
    ]
    spec.extend((f"t-{cid}", rubric_label(cid), "num") for cid in SCORED_IDS)
    default = set(REPO_DEFAULT_COLS)
    headers = "".join(
        _th(
            label,
            col,
            typ,
            visible=col in default,
            sort="asc" if col == "score" else None,
        )
        for col, label, typ in spec
    )
    rows = []

    def _repo_sort(repo: dict) -> tuple:
        scored = inspector_score(analysis_map.get(repo["repo_id"]))
        if scored is None:
            return (1, 0, -(repo.get("commit_count") or 0))
        return (0, scored, -(repo.get("commit_count") or 0))

    for repo in sorted(repos, key=_repo_sort):
        flags = findings_by_repo.get(repo["repo_id"]) or []
        report = analysis_map.get(repo["repo_id"])
        concerns = 0
        if report:
            concerns = sum(1 for item in report.get("checklist") or [] if item.get("concern"))
        tag_scores = repo_tag_scores(report)
        score = inspector_score(report)
        href = f"repos/{slugs[repo['repo_id']]}.html"
        values = {
            "repo": repo["repo_id"],
            "score": score,
            "last": repo.get("last_commit"),
            "commits": repo.get("commit_count"),
            "humans": repo.get("human_contributor_count"),
            "churn": repo.get("churn"),
            "branches": repo.get("branch_count"),
            "flags": len(flags),
            "head": repo.get("head_ref"),
            "first": repo.get("first_commit"),
            "bots": repo.get("bot_contributor_count"),
            "add": repo.get("additions"),
            "del": repo.get("deletions"),
            "net": repo.get("net"),
            "files": repo.get("files_changed"),
            "paths": repo.get("unique_path_count"),
            "merges": repo.get("merge_count"),
            "bin": repo.get("binary_touch_count"),
            "git-tags": repo.get("tag_count"),
            "remotes": repo.get("remote_count"),
            "headfiles": repo.get("head_file_count"),
            "occ": repo.get("occupancy_days"),
            "weeks": repo.get("active_week_count"),
            "weekday": repo.get("weekday_commits"),
            "weekend": repo.get("weekend_commits"),
            "maxc": repo.get("max_commit_churn"),
            "meanc": repo.get("mean_commit_churn"),
            "cpd": repo.get("commits_per_active_day"),
            "concerns": concerns,
        }
        for cid in SCORED_IDS:
            values[f"t-{cid}"] = tag_scores[cid]
        cells = []
        for col, _label, typ in spec:
            if col == "tags":
                hidden = "" if col in default else " col-hidden"
                cells.append(
                    f'<td class="{hidden.strip()}" data-col="tags" '
                    f'data-sort="{esc(score if score is not None else "")}" data-type="num">'
                    f"{_tag_strip(report)}</td>"
                )
                continue
            href_cell = href if col == "repo" else None
            cells.append(
                _td(
                    values[col],
                    href=href_cell,
                    typ=typ,
                    col=col,
                    visible=col in default,
                )
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    bar = _col_bar([(c, lab) for c, lab, _ in spec], default, "repos")
    return (
        f"{bar}<div class=\"table-wrap\">"
        f'<table class="sortable grid" data-table="repos"><thead><tr>{headers}</tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _people_table(humans: list[dict], slugs: dict[str, str]) -> str:
    spec = [
        ("name", "name", "str"),
        ("first", "first commit", "date"),
        ("last", "last commit", "date"),
        ("commits", "commits", "num"),
        ("churn", "churn", "num"),
        ("days", "days", "num"),
        ("email", "email", "str"),
        ("repos", "repos", "num"),
        ("durable", "durable", "num"),
        ("thin", "thin", "num"),
        ("add", "additions", "num"),
        ("del", "deletions", "num"),
        ("net", "net", "num"),
        ("files", "files", "num"),
        ("occ", "occupancy days", "num"),
        ("weeks", "active weeks", "num"),
        ("weekday", "weekday", "num"),
        ("weekend", "weekend", "num"),
        ("maxc", "max churn", "num"),
        ("meanc", "mean churn", "num"),
        ("cpd", "commits/day", "num"),
    ]
    default = set(PEOPLE_DEFAULT_COLS)
    headers = "".join(
        _th(label, col, typ, visible=col in default) for col, label, typ in spec
    )
    rows = []
    for person in sorted(humans, key=lambda p: p.get("last_commit") or "", reverse=True):
        href = f"people/{slugs[person['identity_key']]}.html"
        values = {
            "name": person.get("author_name"),
            "first": person.get("first_commit"),
            "last": person.get("last_commit"),
            "commits": person.get("commit_count"),
            "churn": person.get("churn"),
            "days": person.get("distinct_days"),
            "email": person.get("author_email"),
            "repos": person.get("repo_count"),
            "durable": person.get("durable_repo_count"),
            "thin": person.get("thin_repo_count"),
            "add": person.get("additions"),
            "del": person.get("deletions"),
            "net": person.get("net"),
            "files": person.get("files_changed"),
            "occ": person.get("occupancy_days"),
            "weeks": person.get("active_week_count"),
            "weekday": person.get("weekday_commits"),
            "weekend": person.get("weekend_commits"),
            "maxc": person.get("max_commit_churn"),
            "meanc": person.get("mean_commit_churn"),
            "cpd": person.get("commits_per_active_day"),
        }
        cells = []
        for col, _label, typ in spec:
            cells.append(
                _td(
                    values[col],
                    href=href if col == "name" else None,
                    typ=typ,
                    col=col,
                    visible=col in default,
                )
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    bar = _col_bar([(c, lab) for c, lab, _ in spec], default, "people")
    return (
        f"{bar}<div class=\"table-wrap\">"
        f'<table class="sortable grid" data-table="people"><thead><tr>{headers}</tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _finding_card(finding: dict) -> str:
    evidence = finding.get("evidence") or {}
    metrics = evidence.get("metrics") or {}
    hashes = evidence.get("commit_hashes") or []
    hash_list = "".join(f"<li><code>{esc(h)}</code></li>" for h in hashes)
    details = _finding_details(finding.get("pattern") or "", metrics)
    return (
        f'<article class="finding" data-pattern="{esc(finding.get("pattern"))}">'
        f"<h3>{esc(finding.get('pattern'))}</h3>"
        f"<p>{esc(finding.get('summary'))}</p>"
        f"{details}"
        f"<p class=\"muted\">Evidence hashes</p><ul>{hash_list}</ul></article>"
    )


def _finding_details(pattern: str, metrics: dict) -> str:
    if not metrics:
        return ""
    if pattern == "hot_potato":
        first = metrics.get("first") or {}
        second = metrics.get("second") or {}
        return (
            f'<p class="when">{esc(first.get("name") or name_from_key(first.get("identity_key")))} '
            f'{esc(first.get("start"))}–{esc(first.get("end"))} → {esc(metrics.get("gap_days"))}-day gap → '
            f'{esc(second.get("name") or name_from_key(second.get("identity_key")))} '
            f'{esc(second.get("start"))}–{esc(second.get("end"))}</p>'
        )
    items = []
    for key, value in metrics.items():
        if isinstance(value, (dict, list)):
            continue
        items.append(f"<li><strong>{esc(key)}</strong> {esc(value)}</li>")
    if not items:
        return ""
    return f'<ul class="when">{"".join(items)}</ul>'


def _repo_page(
    repo: dict,
    humans: list[dict],
    findings: list[dict],
    report: dict | None,
    as_of: date,
    input_path: str,
    person_slugs: dict[str, str],
    since: date | None = None,
) -> str:
    authors = [a for a in repo.get("authors") or [] if not a.get("is_bot")]
    author_rows = []
    for author in sorted(authors, key=lambda a: a.get("last_commit") or "", reverse=True):
        key = author.get("identity_key") or ""
        href = f"../people/{person_slugs[key]}.html" if key in person_slugs else None
        author_rows.append(
            "<tr>"
            + _td(author.get("author_name"), href=href, typ="str", col="name")
            + _td(author.get("author_email"), typ="str", col="email")
            + _td(author.get("first_commit"), typ="date", col="first")
            + _td(author.get("last_commit"), typ="date", col="last")
            + _td(author.get("commit_count"), col="commits")
            + _td(len(author.get("days") or []), col="days")
            + "</tr>"
        )
    finding_html = [_finding_card(finding) for finding in findings]
    checks = []
    for item in (report or {}).get("checklist") or []:
        cls = "check concern" if item.get("concern") else "check"
        hashes = ", ".join(item.get("evidence_hashes") or [])
        paths = ", ".join(item.get("evidence_paths") or [])
        checks.append(
            f'<article class="{cls}" id="check-{esc(item.get("id"))}">'
            f"<h3>{esc(item.get('id'))}</h3>"
            f"<p>{esc(item.get('answer'))}</p>"
            f"<p class=\"muted\">hashes: {esc(hashes) or '—'} · paths: {esc(paths) or '—'}</p>"
            "</article>"
        )
    inspect = "".join(
        f"<li><code>{esc(item.get('hash'))}</code> — {esc(item.get('why'))}</li>"
        for item in (report or {}).get("next_inspect") or []
    )
    purpose = ""
    exec_html = ""
    if report:
        purpose = f"<p><strong>{esc(report.get('category'))}</strong> — {esc(report.get('purpose'))}</p>"
        if report.get("headline") or report.get("executive_summary"):
            exec_html = (
                '<section class="card"><h2>Executive summary</h2>'
                f"<p><strong>{esc(report.get('headline'))}</strong></p>"
                f'<div class="prose">{esc(report.get("executive_summary"))}</div></section>'
            )
    concerns = sum(1 for item in (report or {}).get("checklist") or [] if item.get("concern"))
    score = inspector_score(report)
    tag_scores = repo_tag_scores(report)
    git_card = _kv_card(
        "Git",
        [
            ("HEAD", repo.get("head_ref"), "str"),
            ("first commit", repo.get("first_commit"), "date"),
            ("last commit", repo.get("last_commit"), "date"),
            ("branches", repo.get("branch_count"), "num"),
            ("remotes", repo.get("remote_count"), "num"),
            ("git tags", repo.get("tag_count"), "num"),
            ("HEAD files", repo.get("head_file_count"), "num"),
        ],
    )
    volume_card = _kv_card(
        "Volume",
        [
            ("commits", repo.get("commit_count"), "num"),
            ("additions", repo.get("additions"), "num"),
            ("deletions", repo.get("deletions"), "num"),
            ("net", repo.get("net"), "num"),
            ("churn", repo.get("churn"), "num"),
            ("files", repo.get("files_changed"), "num"),
            ("unique paths", repo.get("unique_path_count"), "num"),
            ("merges", repo.get("merge_count"), "num"),
            ("binaries", repo.get("binary_touch_count"), "num"),
        ],
    )
    people_card = _kv_card(
        "People",
        [
            ("humans", repo.get("human_contributor_count"), "num"),
            ("bots", repo.get("bot_contributor_count"), "num"),
            ("flags", len(findings), "num"),
            ("score", score, "num"),
            ("concerns", concerns, "num"),
        ],
    )
    cadence_card = _kv_card(
        "Cadence",
        [
            ("occupancy days", repo.get("occupancy_days"), "num"),
            ("active weeks", repo.get("active_week_count"), "num"),
            ("weekday", repo.get("weekday_commits"), "num"),
            ("weekend", repo.get("weekend_commits"), "num"),
            ("max churn", repo.get("max_commit_churn"), "num"),
            ("mean churn", repo.get("mean_commit_churn"), "num"),
            ("commits/day", repo.get("commits_per_active_day"), "num"),
        ],
    )
    tag_card = _kv_card(
        "Inspector tags",
        [(rubric_label(cid), tag_scores[cid], "num") for cid in SCORED_IDS],
    )
    body = f"""
    <p><a href="../index.html">← dashboard</a></p>
    <h1>Repo {esc(repo['repo_id'])}</h1>
    {purpose}
    {exec_html}
    {git_card}{volume_card}{people_card}{cadence_card}{tag_card}
    <section class="card"><h2>Day calendar</h2>{day_heatmap(_day_map(repo.get('activity_by_day')))}</section>
    <section class="card"><h2>Week bars</h2>{bar_chart(_activity_pairs(repo.get('activity_by_week') or [], 'week'))}</section>
    <h2>Contributors in this repo</h2>
    <p class="muted">First and last commit are for this repo only. Sort by last commit to see who is still active here.</p>
    <table class="sortable"><thead><tr>{_th('name','name','str')}{_th('email','email','str')}{_th('first commit','first','str')}{_th('last commit','last','str')}{_th('commits','commits')}{_th('days','days')}</tr></thead>
    <tbody>{''.join(author_rows)}</tbody></table>
    <h2>Flags</h2>
    {''.join(finding_html) or '<p class="muted">No founding-pattern flags.</p>'}
    <h2>Inspector checklist</h2>
    {_scorecard(report)}
    {''.join(checks) or '<p class="muted">No Grok checklist yet. Product scan runs analyze; --no-analyze leaves this empty.</p>'}
    <h2>Open first</h2>
    <ul>{inspect or '<li class="muted">None yet.</li>'}</ul>
    """
    return _page(
        f"Repo {repo['repo_id']}",
        body,
        asset_prefix="../",
        as_of=as_of,
        input_path=input_path,
        since=since,
    )


def _person_page(
    person: dict,
    repos: list[dict],
    as_of: date,
    input_path: str,
    repo_slugs: dict[str, str],
    findings: list[dict] | None = None,
    since: date | None = None,
) -> str:
    repo_rows = []
    by_id = {r["repo_id"]: r for r in repos}
    for repo_id in person.get("repos") or []:
        repo = by_id.get(repo_id) or {"repo_id": repo_id}
        href = f"../repos/{repo_slugs[repo_id]}.html" if repo_id in repo_slugs else None
        span = next(
            (s for s in person.get("occupancy_spans") or [] if s.get("repo_id") == repo_id),
            {},
        )
        repo_rows.append(
            "<tr>"
            + _td(repo_id, href=href, typ="str", col="repo")
            + _td(span.get("start"), typ="date", col="first")
            + _td(span.get("end"), typ="date", col="last")
            + _td(repo.get("commit_count"), col="commits")
            + _td(repo.get("churn"), col="churn")
            + "</tr>"
        )
    identity_card = _kv_card(
        "Identity",
        [
            ("name", person.get("author_name"), "str"),
            ("email", person.get("author_email"), "str"),
            ("first commit", person.get("first_commit"), "date"),
            ("last commit", person.get("last_commit"), "date"),
        ],
    )
    volume_card = _kv_card(
        "Volume",
        [
            ("commits", person.get("commit_count"), "num"),
            ("additions", person.get("additions"), "num"),
            ("deletions", person.get("deletions"), "num"),
            ("net", person.get("net"), "num"),
            ("churn", person.get("churn"), "num"),
            ("files", person.get("files_changed"), "num"),
        ],
    )
    presence_card = _kv_card(
        "Presence",
        [
            ("days", person.get("distinct_days"), "num"),
            ("occupancy days", person.get("occupancy_days"), "num"),
            ("repos", person.get("repo_count"), "num"),
            ("durable", person.get("durable_repo_count"), "num"),
            ("thin", person.get("thin_repo_count"), "num"),
        ],
    )
    cadence_card = _kv_card(
        "Cadence",
        [
            ("active weeks", person.get("active_week_count"), "num"),
            ("weekday", person.get("weekday_commits"), "num"),
            ("weekend", person.get("weekend_commits"), "num"),
            ("max churn", person.get("max_commit_churn"), "num"),
            ("mean churn", person.get("mean_commit_churn"), "num"),
            ("commits/day", person.get("commits_per_active_day"), "num"),
        ],
    )
    body = f"""
    <p><a href="../index.html">← dashboard</a></p>
    <h1>{esc(person.get('author_name'))}</h1>
    <p class="muted"><code>{esc(person.get('author_email'))}</code></p>
    {identity_card}{volume_card}{presence_card}{cadence_card}
    <section class="card"><h2>Day calendar</h2>{day_heatmap(_day_map(person.get('activity_by_day')))}</section>
    <section class="card"><h2>Week bars</h2>{bar_chart(_activity_pairs(person.get('activity_by_week') or [], 'week'))}</section>
    <h2>Flags</h2>
    {''.join(_finding_card(f) for f in findings or []) or '<p class="muted">No person-lens flags.</p>'}
    <h2>Repos touched</h2>
    <table class="sortable"><thead><tr>{_th('repo','repo','str')}{_th('first here','first','date')}{_th('last here','last','date')}{_th('repo commits','commits')}{_th('repo churn','churn')}</tr></thead>
    <tbody>{''.join(repo_rows)}</tbody></table>
    """
    return _page(
        person.get("author_name") or "person",
        body,
        asset_prefix="../",
        as_of=as_of,
        input_path=input_path,
        since=since,
    )
