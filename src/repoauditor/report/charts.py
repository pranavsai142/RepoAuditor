"""Inline SVG charts. No JS chart library."""

from __future__ import annotations

from datetime import date, timedelta
from html import escape


def esc(value: object) -> str:
    return escape("" if value is None else str(value))


def bar_chart(rows: list[tuple[str, int]], *, width: int = 720, height: int = 140) -> str:
    if not rows:
        return '<p class="muted">No activity in range.</p>'
    peak = max(count for _, count in rows) or 1
    gap = 3
    bar_w = max(4, int((width - gap * (len(rows) + 1)) / max(len(rows), 1)))
    chart_h = height - 28
    bars = []
    x = gap
    for label, count in rows:
        h = int(chart_h * (count / peak)) if count else 0
        y = 8 + (chart_h - h)
        bars.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{h}" fill="#1b7f4e">'
            f'<title>{esc(label)}: {count}</title></rect>'
        )
        x += bar_w + gap
    first = esc(rows[0][0])
    last = esc(rows[-1][0])
    return (
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Activity bars">'
        f"{''.join(bars)}"
        f'<text x="4" y="{height - 6}" class="chart-label">{first}</text>'
        f'<text x="{width - 4}" y="{height - 6}" text-anchor="end" class="chart-label">{last}</text>'
        f"</svg>"
    )


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
