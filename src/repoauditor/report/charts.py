"""Inline SVG charts. Zoom lives in the page script; no chart library."""

from __future__ import annotations

import json
from datetime import date, timedelta
from html import escape

from repoauditor.report.format import compact_number


def esc(value: object) -> str:
    return escape("" if value is None else str(value))


CHART_W = 720
CHART_H = 168
PAD_L = 42
PAD_R = 10
PAD_T = 12
PAD_B = 28


def bar_chart(rows: list[tuple[str, int]], *, width: int = CHART_W, height: int = CHART_H) -> str:
    if not rows:
        return '<p class="muted">No activity in range.</p>'
    svg = _bar_svg(rows, 0, len(rows) - 1, width=width, height=height)
    payload = json.dumps([[label, int(count)] for label, count in rows], separators=(",", ":"))
    payload = payload.replace("<", "\\u003c")
    return (
        '<div class="chart-zoom">'
        '<p class="muted chart-help">Drag across the bars to zoom a short window. '
        "Y-axis follows the visible peak. Reset to see the full range.</p>"
        '<div class="chart-tools">'
        '<button type="button" class="chart-reset" hidden>Reset zoom</button>'
        '<span class="chart-window muted"></span></div>'
        f'<div class="chart-stage">{svg}</div>'
        f'<script type="application/json" class="chart-data">{payload}</script>'
        "</div>"
    )


def _bar_svg(
    rows: list[tuple[str, int]],
    lo: int,
    hi: int,
    *,
    width: int = CHART_W,
    height: int = CHART_H,
) -> str:
    slice_rows = rows[lo : hi + 1]
    if not slice_rows:
        return ""
    peak = max(count for _, count in slice_rows) or 1
    inner_w = width - PAD_L - PAD_R
    inner_h = height - PAD_T - PAD_B
    n = len(slice_rows)
    gap = 2 if n > 80 else 3
    bar_w = max(2, int((inner_w - gap * (n + 1)) / n))
    bars = []
    for i, (label, count) in enumerate(slice_rows):
        h = int(inner_h * (count / peak)) if count else 0
        x = PAD_L + gap + i * (bar_w + gap)
        y = PAD_T + (inner_h - h)
        bars.append(
            f'<rect class="chart-bar" data-i="{lo + i}" x="{x}" y="{y}" '
            f'width="{bar_w}" height="{h}" fill="#1b7f4e">'
            f"<title>{esc(label)}: {count}</title></rect>"
        )
    y_ticks = _y_ticks(peak)
    axis = [
        f'<line x1="{PAD_L}" y1="{PAD_T}" x2="{PAD_L}" y2="{PAD_T + inner_h}" '
        f'stroke="#d5ddd7" stroke-width="1"/>',
        f'<line x1="{PAD_L}" y1="{PAD_T + inner_h}" x2="{width - PAD_R}" '
        f'y2="{PAD_T + inner_h}" stroke="#d5ddd7" stroke-width="1"/>',
    ]
    for value in y_ticks:
        frac = value / peak if peak else 0
        y = PAD_T + inner_h - int(inner_h * frac)
        axis.append(
            f'<line x1="{PAD_L - 3}" y1="{y}" x2="{PAD_L}" y2="{y}" stroke="#8a938c"/>'
        )
        axis.append(
            f'<text x="{PAD_L - 6}" y="{y + 3}" text-anchor="end" class="chart-label">'
            f"{esc(compact_number(value))}</text>"
        )
    x_labels = []
    ticks = _x_indices(n)
    for i in ticks:
        label, _count = slice_rows[i]
        x = PAD_L + gap + i * (bar_w + gap) + bar_w / 2
        x_labels.append(
            f'<text x="{x:.1f}" y="{height - 8}" text-anchor="middle" class="chart-label">'
            f"{esc(_short_x(label))}</text>"
        )
    return (
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Activity bars" data-lo="{lo}" data-hi="{hi}">'
        f"{''.join(axis)}{''.join(bars)}{''.join(x_labels)}</svg>"
    )


def _y_ticks(peak: int) -> list[int]:
    if peak <= 1:
        return [0, 1]
    mid = max(1, round(peak / 2))
    if mid == peak:
        return [0, peak]
    return [0, mid, peak]


def _x_indices(n: int) -> list[int]:
    if n <= 1:
        return [0]
    if n <= 6:
        return list(range(n))
    return sorted({0, n // 4, n // 2, (3 * n) // 4, n - 1})


def _short_x(label: str) -> str:
    text = str(label)
    if len(text) <= 10:
        return text
    if "T" in text and text[4:5] == "-":
        return text[:10]
    return text[:10]


def mini_bars(values: list[tuple[str, float, float]]) -> str:
    cells = []
    for label, value, peak in values:
        denom = peak or 1
        pct = min(100, int(100 * (value / denom))) if value else 0
        cells.append(
            f'<span class="mini" title="{esc(label)}: {value}">'
            f'<i style="width:{pct}%"></i><em>{esc(value)}</em></span>'
        )
    return f'<span class="minis">{"".join(cells)}</span>'


def day_heatmap(by_day: dict[str, int]) -> str:
    if not by_day:
        return '<p class="muted">No dated commits.</p>'
    days = sorted(date.fromisoformat(d) for d in by_day)
    start = days[0] - timedelta(days=days[0].weekday())
    end = days[-1]
    peak = max(by_day.values()) or 1
    weeks: list[list[date]] = []
    week: list[date] = []
    cursor = start
    while cursor <= end:
        week.append(cursor)
        if cursor.weekday() == 6:
            weeks.append(week)
            week = []
        cursor += timedelta(days=1)
    if week:
        while len(week) < 7:
            week.append(week[-1] + timedelta(days=1))
        weeks.append(week)
    last_month: tuple[int, int] | None = None
    columns = []
    for days_in_week in weeks:
        anchor = days_in_week[0]
        month_key = (anchor.year, anchor.month)
        label = anchor.strftime("%b %Y") if month_key != last_month else ""
        last_month = month_key
        cells = [f'<div class="heat-label">{esc(label)}</div>']
        for day in days_in_week:
            key = day.isoformat()
            count = by_day.get(key, 0)
            level = 0 if count == 0 else min(4, 1 + int(3 * count / peak))
            cells.append(
                f'<div class="heat l{level}" title="{key}: {count} commits"></div>'
            )
        columns.append("".join(cells))
    return (
        '<div class="heatmap-wrap">'
        '<div class="heatmap">'
        f"{''.join(columns)}"
        "</div></div>"
    )
