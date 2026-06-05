#!/usr/bin/env python3
"""Render a branded, self-contained HTML report from a CQF Bench report/comparison JSON.

Usage (standalone):
    python scripts/render_html_report.py <report-or-compare.json> [-o out.html]

Library use:
    from render_html_report import render_html_report
    html = render_html_report(report_dict)

The generator consumes the same `report` dict the harness produces and writes a single
self-contained .html file: no external CSS, JS, fonts, or image requests. Open it in a
browser, attach it to a PR, or email it.

All correctness/latency aggregates are derived from `build_comparison_summary()` and the
canonical `classify_*` helpers in run_benchmark.py, so the HTML can never disagree with
the Markdown / SVG bundle written by `write_comparison_bundle()`.

Layout (top to bottom), per the requested emphasis:
  1. Branded header (logo + wordmark + tagline + run provenance)
  2. Per-engine scorecards  -- SPEED headline first, then capability pass/fail
  3. Correctness-vs-speed quadrant
  4. Capability + conformance outcome bars
  5. Conformance fingerprint (checks as rows, engines as columns -- fits letter width)
  6. p95-by-scenario line chart (engine latency profiles)
  7. Latency distribution (min/p50/p95/p99/max box-and-whisker per scenario)
  8. Detailed capability matrix
  9. Reproducibility / provenance footer
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from run_benchmark import (  # noqa: E402
    build_comparison_summary,
    classify_capability_result,
    classify_conformance_result,
    classify_result_label,
    _status_color,
)

# ---------------------------------------------------------------------------
# Brand (single source of truth -- mirrors docs-site landing.css).
# ---------------------------------------------------------------------------
BRAND = {
    "name": "CQF Bench",
    "tagline": "The conformance & performance benchmark for CQF / Clinical Reasoning engines",
    "org": "Carrera Group",
    "repo_url": "https://github.com/carreraGroup/cqf-bench",
    "accent": "#1a5fb4",
    "accent_soft": "#62a0ea",
    "ink": "#0f172a",
    "muted": "#64748b",
    "surface": "#f4f6f9",
    "border": "#d8dee8",
}
STATUS_DOT = {
    "PASS": "🟢", "FAIL": "🔴", "UNSUPPORTED": "🟡", "WARNING": "🟠", "NOT_RUN": "⚪",
}
# distinct per-engine series colors
SERIES = ["#1a5fb4", "#16a34a", "#9333ea", "#ea580c", "#0891b2", "#db2777"]

REPO_ROOT = _SCRIPTS.parent


def _logo_data_uri() -> str:
    for cand in (REPO_ROOT / "logo.png", REPO_ROOT / "docs-site/src/assets/logo.png"):
        if cand.exists():
            b = base64.b64encode(cand.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{b}"
    return ""


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def fmt_ms(v):
    return f"{v:.1f}ms" if isinstance(v, (int, float)) else "—"


def _is_conformance(r: dict) -> bool:
    return r.get("test_type") == "conformance" or str(r.get("scenario_id", "")).startswith("CONF")


def _headline_p95(r: dict):
    """The latency the rest of the bundle reports: avg p95 over repetitions, else p95."""
    lat = r.get("latency_ms")
    if not isinstance(lat, dict):
        return None
    v = lat.get("avg_p95_over_repetitions", lat.get("p95"))
    return float(v) if isinstance(v, (int, float)) else None


# ---------------------------------------------------------------------------
# Data shaping -- aggregates come straight from build_comparison_summary().
# ---------------------------------------------------------------------------
def engine_view(raw_engine: dict, es: dict) -> dict:
    caps = [r for r in raw_engine.get("results", []) if not _is_conformance(r)]
    conf = [r for r in raw_engine.get("results", []) if _is_conformance(r)]
    cap_counts = {"PASS": 0, "FAIL": 0, "UNSUPPORTED": 0, "NOT_RUN": 0, **(es.get("capability_counts") or {})}
    conf_counts = {"PASS": 0, "FAIL": 0, "UNSUPPORTED": 0, "WARNING": 0, **(es.get("conformance_counts") or {})}
    cap_total = sum(cap_counts.get(k, 0) for k in ("PASS", "FAIL", "UNSUPPORTED", "NOT_RUN"))
    return {
        "name": es.get("name") or raw_engine.get("name", ""),
        "adapter": es.get("adapter") or raw_engine.get("adapter", "") or "",
        "base_url": es.get("base_url") or raw_engine.get("base_url", "") or "",
        "cap_counts": cap_counts,
        "conf_counts": conf_counts,
        "cap_pass": cap_counts.get("PASS", 0),
        "cap_total": cap_total,
        "avg_p95": es.get("pass_latency_p95_avg"),
        "min_p95": es.get("pass_latency_p95_min"),
        "max_p95": es.get("pass_latency_p95_max"),
        "caps": caps,
        "conf": conf,
    }


def _views(report: dict) -> list[dict]:
    summary = build_comparison_summary(report)
    raw_by_name = {str(e.get("name", "")): e for e in report.get("engines", [])}
    out = []
    for es in summary.get("engine_summaries", []):
        out.append(engine_view(raw_by_name.get(str(es.get("name", "")), {}), es))
    return out


# ---------------------------------------------------------------------------
# SVG builders (self-contained, no JS needed)
# ---------------------------------------------------------------------------
def svg_quadrant(views: list[dict]) -> str:
    """Correctness (x, pass count) vs speed (y, avg p95 -- lower is better, so invert)."""
    W, H = 720, 460
    L, R, T, B = 70, 30, 60, 70
    pts = [v for v in views if v["avg_p95"] is not None and v["cap_total"] > 0]
    if not pts:
        return "<p class='muted'>No PASS latency data to plot.</p>"
    max_pass = (max((v["cap_total"] for v in pts), default=1) or 1) * 1.12
    max_p95 = (max((v["avg_p95"] for v in pts), default=1) or 1) * 1.15

    def px(pass_count):
        return L + (pass_count / max_pass) * (W - L - R)

    def py(p95):  # lower p95 -> higher on chart (better)
        return T + (p95 / max_p95) * (H - T - B)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" class="chart">']
    parts.append(f'<rect width="{W}" height="{H}" fill="white"/>')
    midx, midy = px(max_pass / 2), py(max_p95 / 2)
    parts.append(f'<rect x="{midx:.0f}" y="{T}" width="{W-R-midx:.0f}" height="{midy-T:.0f}" fill="#16a34a" opacity="0.06"/>')
    parts.append(f'<text x="{W-R-8:.0f}" y="{T+18}" text-anchor="end" font-size="11" fill="#16a34a">correct &amp; fast ✓</text>')
    parts.append(f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="{BRAND["border"]}"/>')
    parts.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="{BRAND["border"]}"/>')
    parts.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-22}" text-anchor="middle" font-size="12" fill="{BRAND["muted"]}">Capabilities passed  →  more correct</text>')
    parts.append(f'<text x="22" y="{(T+H-B)/2:.0f}" text-anchor="middle" font-size="12" fill="{BRAND["muted"]}" transform="rotate(-90 22 {(T+H-B)/2:.0f})">faster  ←  avg PASS p95</text>')
    for i, v in enumerate(pts):
        cx, cy = px(v["cap_pass"]), py(v["avg_p95"])
        col = SERIES[i % len(SERIES)]
        # keep labels inside the plot box: anchor toward the interior near edges
        if cx > W - R - 90:
            anchor, lx = "end", cx
        elif cx < L + 90:
            anchor, lx = "start", cx
        else:
            anchor, lx = "middle", cx
        ly_name = cy - 16 if cy - 16 > T + 6 else cy + 30
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="9" fill="{col}" opacity="0.85"/>')
        parts.append(f'<text x="{lx:.1f}" y="{ly_name:.1f}" text-anchor="{anchor}" font-size="12" font-weight="600" fill="{BRAND["ink"]}">{esc(v["name"])}</text>')
        parts.append(f'<text x="{lx:.1f}" y="{ly_name+16:.1f}" text-anchor="{anchor}" font-size="10" fill="{BRAND["muted"]}">{v["cap_pass"]}/{v["cap_total"]} · {fmt_ms(v["avg_p95"])}</text>')
    parts.append("</svg>")
    return "".join(parts)


def svg_stacked(title: str, views: list[dict], key: str, order: list[str]) -> str:
    W, H = 560, 320
    L, R, T, B = 60, 24, 60, 70
    maxv = max((sum(v[key].values()) for v in views), default=1) or 1
    bw = min(80, (W - L - R) / max(len(views), 1) * 0.55)
    gap = (W - L - R) / max(len(views), 1)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" class="chart">']
    parts.append(f'<rect width="{W}" height="{H}" fill="white"/>')
    parts.append(f'<text x="{L}" y="26" font-size="15" font-weight="600" fill="{BRAND["ink"]}">{esc(title)}</text>')
    lx = L
    for st in order:
        parts.append(f'<rect x="{lx}" y="40" width="11" height="11" fill="{_status_color(st)}"/>')
        parts.append(f'<text x="{lx+16}" y="50" font-size="10" fill="{BRAND["muted"]}">{st}</text>')
        lx += 22 + len(st) * 6.5
    base = H - B
    for i, v in enumerate(views):
        x = L + gap * i + (gap - bw) / 2
        y = base
        for st in order:
            n = v[key].get(st, 0)
            if not n:
                continue
            h = (n / maxv) * (base - T)
            y -= h
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{_status_color(st)}"/>')
            if h > 14:
                parts.append(f'<text x="{x+bw/2:.1f}" y="{y+h/2+4:.1f}" text-anchor="middle" font-size="10" fill="white">{n}</text>')
        parts.append(f'<text x="{x+bw/2:.1f}" y="{base+18:.0f}" text-anchor="middle" font-size="11" fill="{BRAND["ink"]}">{esc(v["name"])}</text>')
    parts.append("</svg>")
    return "".join(parts)


def svg_line_p95(views: list[dict]) -> str:
    """Line chart: x = capability scenarios, y = PASS p95 (ms), one line per engine.

    Lines break across scenarios an engine did not PASS (no fabricated continuity).
    """
    scen_order, seen = [], set()
    for v in views:
        for r in v["caps"]:
            if classify_capability_result(r) == "PASS" and r["scenario_id"] not in seen:
                seen.add(r["scenario_id"])
                scen_order.append(r["scenario_id"])
    if not scen_order:
        return "<p class='muted'>No PASS latency to plot.</p>"

    def p95_of(view, sid):
        for r in view["caps"]:
            if r["scenario_id"] == sid and classify_capability_result(r) == "PASS":
                return _headline_p95(r)
        return None

    maxv = 0.0
    for v in views:
        for sid in scen_order:
            p = p95_of(v, sid)
            if p is not None:
                maxv = max(maxv, p)
    maxv = (maxv or 1) * 1.12

    n = len(scen_order)
    W = max(620, 90 + n * 64)
    L, R, T, B = 60, 24, 70, 96
    plot_w = W - L - R
    H = T + 300 + (B - 70)

    def px(i):
        return L + (plot_w * (i + 0.5) / n) if n > 1 else L + plot_w / 2

    def py(val):
        return (H - B) - (val / maxv) * (H - B - T)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" class="chart">']
    parts.append(f'<rect width="{W}" height="{H}" fill="white"/>')
    parts.append(f'<text x="{L}" y="26" font-size="15" font-weight="600" fill="{BRAND["ink"]}">PASS p95 by scenario — engine profiles</text>')
    lx = L
    for i, v in enumerate(views):
        col = SERIES[i % len(SERIES)]
        parts.append(f'<line x1="{lx}" y1="46" x2="{lx+18}" y2="46" stroke="{col}" stroke-width="3"/>')
        parts.append(f'<circle cx="{lx+9}" cy="46" r="3.5" fill="{col}"/>')
        parts.append(f'<text x="{lx+24}" y="50" font-size="10" fill="{BRAND["muted"]}">{esc(v["name"])}</text>')
        lx += 40 + len(v["name"]) * 6.5
    for frac in (0, .25, .5, .75, 1.0):
        gy = py(frac * maxv)
        parts.append(f'<line x1="{L}" y1="{gy:.1f}" x2="{W-R}" y2="{gy:.1f}" stroke="#eef2f7"/>')
        parts.append(f'<text x="{L-8}" y="{gy+4:.1f}" text-anchor="end" font-size="9" fill="{BRAND["muted"]}">{frac*maxv:.0f}ms</text>')
    for i, sid in enumerate(scen_order):
        x = px(i)
        parts.append(f'<text x="{x:.1f}" y="{H-B+18:.0f}" text-anchor="end" font-size="9" fill="{BRAND["ink"]}" transform="rotate(-40 {x:.1f} {H-B+18:.0f})">{esc(sid)}</text>')
    for ei, v in enumerate(views):
        col = SERIES[ei % len(SERIES)]
        segment = []
        for i, sid in enumerate(scen_order):
            p = p95_of(v, sid)
            if p is None:
                if len(segment) >= 2:
                    ptsline = " ".join(f"{px(j):.1f},{py(val):.1f}" for j, val in segment)
                    parts.append(f'<polyline points="{ptsline}" fill="none" stroke="{col}" stroke-width="2.5"/>')
                segment = []
                continue
            segment.append((i, p))
        if len(segment) >= 2:
            ptsline = " ".join(f"{px(j):.1f},{py(val):.1f}" for j, val in segment)
            parts.append(f'<polyline points="{ptsline}" fill="none" stroke="{col}" stroke-width="2.5"/>')
        for i, sid in enumerate(scen_order):
            p = p95_of(v, sid)
            if p is not None:
                parts.append(f'<circle cx="{px(i):.1f}" cy="{py(p):.1f}" r="3.5" fill="{col}"><title>{esc(v["name"])} · {esc(sid)}: {p:.0f}ms</title></circle>')
    parts.append("</svg>")
    return "".join(parts)


def svg_distribution(views: list[dict]) -> str:
    """Box-and-whisker of PASS latency (min/p50/p95/p99/max) per scenario, grouped by engine."""
    scen_order, seen = [], set()
    for v in views:
        for r in v["caps"]:
            if classify_capability_result(r) == "PASS" and r["scenario_id"] not in seen:
                seen.add(r["scenario_id"])
                scen_order.append((r["scenario_id"], r.get("scenario_name", "")))
    if not scen_order:
        return "<p class='muted'>No PASS latency to plot.</p>"

    def lat(view, sid):
        for r in view["caps"]:
            if r["scenario_id"] == sid and classify_capability_result(r) == "PASS":
                return r.get("latency_ms") or {}
        return None

    maxv = 0.0
    for sid, _ in scen_order:
        for v in views:
            l = lat(v, sid)
            if l and l.get("max") is not None:
                maxv = max(maxv, l["max"])
    maxv = (maxv or 1) * 1.08

    row_h = 30
    n_eng = len(views)
    group_h = row_h * n_eng + 14
    W = 900
    L, R, T = 230, 90, 70
    H = T + group_h * len(scen_order) + 20
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" class="chart">']
    parts.append(f'<rect width="{W}" height="{H}" fill="white"/>')
    parts.append(f'<text x="20" y="26" font-size="15" font-weight="600" fill="{BRAND["ink"]}">PASS latency distribution — min · p50 · p95 · p99 · max</text>')
    lx = 20
    for i, v in enumerate(views):
        parts.append(f'<rect x="{lx}" y="40" width="11" height="11" fill="{SERIES[i%len(SERIES)]}"/>')
        parts.append(f'<text x="{lx+16}" y="50" font-size="10" fill="{BRAND["muted"]}">{esc(v["name"])}</text>')
        lx += 26 + len(v["name"]) * 6.5

    def sx(val):
        return L + (val / maxv) * (W - L - R)

    for frac in (0, .25, .5, .75, 1.0):
        gx = L + frac * (W - L - R)
        parts.append(f'<line x1="{gx:.0f}" y1="{T-6}" x2="{gx:.0f}" y2="{H-14}" stroke="#eef2f7"/>')
        parts.append(f'<text x="{gx:.0f}" y="{T-10}" text-anchor="middle" font-size="9" fill="{BRAND["muted"]}">{frac*maxv:.0f}ms</text>')

    y = T
    for sid, sname in scen_order:
        parts.append(f'<text x="20" y="{y+12:.0f}" font-size="11" font-weight="600" fill="{BRAND["ink"]}">{esc(sid)}</text>')
        parts.append(f'<text x="20" y="{y+25:.0f}" font-size="9" fill="{BRAND["muted"]}">{esc(sname[:38])}</text>')
        for i, v in enumerate(views):
            l = lat(v, sid)
            cy = y + 8 + i * row_h
            col = SERIES[i % len(SERIES)]
            if not l:
                parts.append(f'<text x="{L}" y="{cy+4:.0f}" font-size="9" fill="{BRAND["muted"]}">no PASS</text>')
                continue
            mn, p50, p95, p99, mx = (l.get("min"), l.get("p50"), l.get("p95"), l.get("p99"), l.get("max"))
            if mn is None:
                continue
            parts.append(f'<line x1="{sx(mn):.1f}" y1="{cy:.1f}" x2="{sx(mx):.1f}" y2="{cy:.1f}" stroke="{col}" stroke-width="2" opacity="0.5"/>')
            if p50 is not None and p95 is not None:
                bx, bw = sx(p50), max(2, sx(p95) - sx(p50))
                parts.append(f'<rect x="{bx:.1f}" y="{cy-6:.1f}" width="{bw:.1f}" height="12" fill="{col}" opacity="0.28" stroke="{col}"/>')
            if p99 is not None:
                parts.append(f'<line x1="{sx(p99):.1f}" y1="{cy-7:.1f}" x2="{sx(p99):.1f}" y2="{cy+7:.1f}" stroke="{col}" stroke-width="2"/>')
            if p95 is not None:
                parts.append(f'<text x="{W-R+6}" y="{cy+4:.0f}" font-size="9" fill="{col}">p95 {p95:.0f}ms</text>')
        y += group_h
    parts.append("</svg>")
    return "".join(parts)


def build_heatmap(views: list[dict]) -> str:
    """Conformance fingerprint: checks are ROWS, engines are COLUMNS (fits letter width)."""
    scen, seen = [], set()
    for v in views:
        for r in v["conf"]:
            if r["scenario_id"] not in seen:
                seen.add(r["scenario_id"])
                scen.append((r["scenario_id"], r.get("scenario_name", "")))
    if not scen:
        return ""
    status_by = {v["name"]: {r["scenario_id"]: classify_conformance_result(r) for r in v["conf"]} for v in views}
    head = "".join(f'<th class="hm-eng">{esc(v["name"])}</th>' for v in views)
    rows = []
    for sid, name in scen:
        cells = []
        for v in views:
            st = status_by[v["name"]].get(sid, "NOT_RUN")
            cells.append(
                f'<td class="hm" style="background:{_status_color(st)}" title="{esc(st)}">{STATUS_DOT[st]} {st}</td>'
            )
        rows.append(f'<tr><th class="rowlab">{esc(sid)}<span>{esc(name)}</span></th>{"".join(cells)}</tr>')
    return (
        '<table class="heatmap"><thead><tr><th></th>' + head + "</tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
    )


def cap_matrix(views: list[dict]) -> str:
    scen, seen = [], set()
    for v in views:
        for r in v["caps"]:
            if r["scenario_id"] not in seen:
                seen.add(r["scenario_id"])
                scen.append((r["scenario_id"], r.get("scenario_name", "")))
    by = {v["name"]: {r["scenario_id"]: r for r in v["caps"]} for v in views}
    head = "".join(f'<th>{esc(v["name"])}</th>' for v in views)
    rows = []
    for sid, sname in scen:
        cells = []
        for v in views:
            r = by[v["name"]].get(sid)
            if not r:
                cells.append('<td class="muted">— NOT_RUN</td>')
                continue
            st = classify_result_label(r)
            t = ""
            if st == "PASS":
                t = " · " + fmt_ms(_headline_p95(r))
            col = _status_color(st)
            cells.append(f'<td><span class="pill" style="background:{col}22;color:{col}">{STATUS_DOT[st]} {st}</span>{t}</td>')
        rows.append(f'<tr><td><b>{esc(sid)}</b><br><span class="muted">{esc(sname)}</span></td>{"".join(cells)}</tr>')
    return f'<table><thead><tr><th>Scenario</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>'


def grade_for(v: dict) -> tuple[str, str]:
    if v["cap_total"] == 0:
        return ("—", BRAND["muted"])
    rate = v["cap_pass"] / v["cap_total"]
    if rate >= 0.9:
        return ("A", "#16a34a")
    if rate >= 0.7:
        return ("B", "#65a30d")
    if rate >= 0.5:
        return ("C", "#ca8a04")
    if rate >= 0.3:
        return ("D", "#ea580c")
    return ("F", "#dc2626")


def scorecard(v: dict, rank_fast: bool) -> str:
    g, gcol = grade_for(v)
    pass_pct = (v["cap_pass"] / v["cap_total"] * 100) if v["cap_total"] else 0
    pass_w = pass_pct
    fail_w = 100 - pass_pct
    speed_note = " · fastest" if rank_fast else ""
    return f"""
    <div class="card">
      <span class="grade" style="background:{gcol}22;color:{gcol}">GRADE {g}</span>
      <div class="ename">{esc(v['name'])}</div>
      <div class="adapter">{esc(v['adapter'])} · {esc(v['base_url'])}</div>

      <div class="metric speed">
        <span class="big">{fmt_ms(v['avg_p95'])}</span>
        <span class="unit">avg PASS p95{speed_note}</span>
      </div>
      <div class="subgrid">
        <div><b>{fmt_ms(v['min_p95'])}</b>fastest</div>
        <div><b>{fmt_ms(v['max_p95'])}</b>slowest</div>
      </div>

      <div class="metric">
        <span class="big">{v['cap_pass']}/{v['cap_total']}</span>
        <span class="unit">capabilities passed ({pass_pct:.0f}%)</span>
      </div>
      <div class="bar">
        <i style="width:{pass_w:.1f}%;background:var(--pass)"></i>
        <i style="width:{fail_w:.1f}%;background:var(--fail)"></i>
      </div>
      <div class="legend">
        <span>{STATUS_DOT['PASS']} {v['cap_counts'].get('PASS',0)} pass</span>
        <span>{STATUS_DOT['FAIL']} {v['cap_counts'].get('FAIL',0)} fail</span>
        <span>{STATUS_DOT['UNSUPPORTED']} {v['cap_counts'].get('UNSUPPORTED',0)} unsupported</span>
      </div>
    </div>"""


# ---------------------------------------------------------------------------
# HTML assembly
# ---------------------------------------------------------------------------
CSS = """
:root{--accent:%(accent)s;--soft:%(accent_soft)s;--ink:%(ink)s;--muted:%(muted)s;
--surface:%(surface)s;--border:%(border)s;--pass:#16a34a;--fail:#dc2626;}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
color:var(--ink);background:#fff;line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:900px;margin:0 auto;padding:0 24px 80px}
header.brand{background:linear-gradient(135deg,var(--accent),#0d3a73);color:#fff;padding:28px 0 26px;margin-bottom:8px}
header.brand .wrap{padding-top:0;padding-bottom:0;display:flex;align-items:center;gap:18px}
header.brand img{height:54px;width:auto;border-radius:8px;background:#fff;padding:5px}
header.brand h1{font-size:1.5rem;margin:0;letter-spacing:-.02em}
header.brand .tag{opacity:.85;font-size:.9rem;margin-top:2px}
header.brand .meta{margin-left:auto;text-align:right;font-size:.78rem;opacity:.92;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
h2{font-size:1.2rem;margin:42px 0 4px;letter-spacing:-.01em}
h2 .sub{display:block;font-size:.82rem;font-weight:400;color:var(--muted);letter-spacing:0}
.cards{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));margin-top:16px}
.card{border:1px solid var(--border);border-radius:14px;padding:18px 20px;background:#fff;
box-shadow:0 1px 2px rgba(15,23,42,.04)}
.card .ename{font-weight:700;font-size:1.05rem}
.card .adapter{color:var(--muted);font-size:.78rem;font-family:ui-monospace,monospace}
.metric{display:flex;align-items:baseline;gap:8px;margin-top:14px}
.metric .big{font-size:2.1rem;font-weight:800;letter-spacing:-.03em;line-height:1}
.metric .unit{color:var(--muted);font-size:.8rem}
.metric.speed .big{color:var(--accent)}
.subgrid{display:flex;gap:18px;margin-top:14px;flex-wrap:wrap}
.subgrid div{font-size:.78rem;color:var(--muted)}
.subgrid b{display:block;font-size:1.15rem;color:var(--ink);font-weight:700}
.bar{height:8px;border-radius:5px;background:#eef2f7;overflow:hidden;margin-top:12px;display:flex}
.bar i{display:block;height:100%%}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:.72rem;font-weight:600}
.grade{float:right;font-size:.72rem;font-weight:700;padding:3px 10px;border-radius:999px}
.chart{width:100%%;height:auto;border:1px solid var(--border);border-radius:12px;background:#fff;margin-top:12px}
.charts-2{display:grid;gap:16px;grid-template-columns:1fr 1fr}
@media(max-width:760px){.charts-2{grid-template-columns:1fr}}
table{border-collapse:collapse;width:100%%;margin-top:14px;font-size:.86rem}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--border)}
th{color:var(--muted);font-weight:600;font-size:.78rem;text-transform:uppercase;letter-spacing:.03em}
tr:hover td{background:var(--surface)}
.heatmap{font-size:.8rem;max-width:560px}
.heatmap td.hm{text-align:center;color:#fff;font-weight:600;font-size:.72rem;white-space:nowrap}
.heatmap th.hm-eng{text-align:center;font-family:ui-monospace,monospace;text-transform:none;color:var(--ink)}
.heatmap th.rowlab{font-family:ui-monospace,monospace;text-transform:none;color:var(--ink);font-weight:700;padding:5px 10px}
.heatmap th.rowlab span{display:block;font-family:inherit;font-weight:400;color:var(--muted);font-size:.72rem;max-width:300px;white-space:normal}
@media print{.wrap{max-width:none}.chart,.card,.heatmap{break-inside:avoid}}
.muted{color:var(--muted)}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:.78rem;color:var(--muted);margin-top:10px}
.lead{color:var(--muted);max-width:62ch;margin-top:6px}
footer.prov{margin-top:54px;border-top:1px solid var(--border);padding-top:20px;font-size:.78rem;color:var(--muted)}
footer.prov .repro{display:inline-block;background:#ecfdf5;color:#047857;border:1px solid #a7f3d0;
border-radius:999px;padding:3px 11px;font-weight:600;margin-bottom:10px}
footer.prov code{font-family:ui-monospace,monospace;background:var(--surface);padding:1px 5px;border-radius:4px}
footer.prov .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:6px 24px;margin-top:8px}
footer.prov a{color:var(--accent)}
""" % BRAND


def render_html_report(report: dict) -> str:
    """Render the full self-contained HTML document for a report/comparison dict."""
    views = _views(report)
    timed = [v for v in views if v["avg_p95"] is not None]
    fastest = min(timed, key=lambda v: v["avg_p95"]) if timed else None
    most_correct = max(views, key=lambda v: v["cap_pass"]) if views else None

    cards = "".join(scorecard(v, rank_fast=(fastest is not None and v is fastest)) for v in views)
    quad = svg_quadrant(views)
    cap_bars = svg_stacked("Capability outcomes by engine", views, "cap_counts", ["PASS", "FAIL", "UNSUPPORTED", "NOT_RUN"])
    conf_bars = svg_stacked("Conformance outcomes by engine", views, "conf_counts", ["PASS", "UNSUPPORTED", "WARNING", "FAIL"])
    heat = build_heatmap(views)
    line = svg_line_p95(views)
    dist = svg_distribution(views)
    matrix = cap_matrix(views)

    summ = []
    if fastest:
        summ.append(f"<b>{esc(fastest['name'])}</b> is fastest at {fmt_ms(fastest['avg_p95'])} avg PASS p95")
    if most_correct:
        summ.append(f"<b>{esc(most_correct['name'])}</b> passed the most capabilities ({most_correct['cap_pass']}/{most_correct['cap_total']})")
    summary_line = ("; ".join(summ) + ".") if summ else ""

    short_hash = (report.get("suite_hash") or "")[:12]
    git = report.get("git_commit") or "n/a"
    meta = (
        f'run <b>{esc(report.get("run_id",""))}</b><br>'
        f'{esc(report.get("ended_utc") or report.get("started_utc") or "")}<br>'
        f'suite {esc(report.get("suite_id",""))} · scale {esc(report.get("scale",""))} · {esc(report.get("repetitions",1))}× reps'
    )

    heat_section = (
        "<h2>Conformance fingerprint<span class='sub'>Conformance check × engine — green is good</span></h2>" + heat
        if heat else ""
    )

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(BRAND['name'])} Report — {esc(report.get('run_id',''))}</title>
<style>{CSS}</style></head><body>
<header class="brand"><div class="wrap">
  <img src="{_logo_data_uri()}" alt="{esc(BRAND['name'])}">
  <div><h1>{esc(BRAND['name'])} Report</h1><div class="tag">{esc(BRAND['tagline'])}</div></div>
  <div class="meta">{meta}</div>
</div></header>
<div class="wrap">

  <p class="lead">{summary_line} Read <b>correctness first, speed second</b> — a fast engine that returns the wrong answer is not outperforming a slower one that is correct. Timing is shown only for scenarios that passed.</p>

  <h2>Scorecards<span class="sub">Speed headline, then capability pass/fail — per engine</span></h2>
  <div class="cards">{cards}</div>

  <h2>Correct &amp; fast?<span class="sub">Top-right is the corner you want: more capabilities passed, lower latency</span></h2>
  {quad}

  <h2>Outcomes<span class="sub">How many scenarios passed end-to-end, and how endpoints conformed</span></h2>
  <div class="charts-2">{cap_bars}{conf_bars}</div>

  {heat_section}

  <h2>p95 by scenario<span class="sub">Each engine's latency profile across the suite — lower is faster; lines break where an engine had no PASS</span></h2>
  {line}

  <h2>Latency distribution<span class="sub">PASS-only: whisker = min→max, box = p50→p95, tick = p99</span></h2>
  {dist}

  <h2>Capability matrix<span class="sub">Every capability scenario, every engine</span></h2>
  {matrix}

  <footer class="prov">
    <span class="repro">✓ Reproducible run</span>
    <div>This report was generated from a CQF Bench run with full provenance recorded. Re-run with the same suite hash and scale to reproduce.</div>
    <div class="grid">
      <div>Suite: <code>{esc(report.get('suite_id',''))}</code> @ <code>{esc(short_hash)}</code></div>
      <div>Git commit: <code>{esc(git)}</code></div>
      <div>Scale: <code>{esc(report.get('scale',''))}</code> · Concurrency: <code>{esc(report.get('concurrency',''))}</code></div>
      <div>Score mode: <code>{esc(report.get('score_mode','compat'))}</code> · Reps: <code>{esc(report.get('repetitions',1))}</code></div>
      <div>Duration: <code>{esc(report.get('duration_seconds',''))}s</code></div>
      <div>Engines file: <code>{esc(report.get('engines_file',''))}</code></div>
    </div>
    <div style="margin-top:14px">{esc(BRAND['org'])} · <a href="{BRAND['repo_url']}">{BRAND['repo_url']}</a></div>
  </footer>
</div></body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Render a branded HTML report from a CQF Bench JSON report")
    ap.add_argument("report", type=Path, help="path to a CQF Bench full report / comparison JSON")
    ap.add_argument("-o", "--out", type=Path, help="output .html (default: <report>.report.html)")
    args = ap.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    out = args.out or args.report.with_suffix(".report.html")
    out.write_text(render_html_report(report), encoding="utf-8")
    print(f"Wrote {out}  ({out.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
