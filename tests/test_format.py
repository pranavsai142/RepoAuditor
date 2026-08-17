from repoauditor.report.charts import day_heatmap
from repoauditor.report.format import compact_number, display_date


def test_compact_number_keeps_small_values() -> None:
    assert compact_number(962) == "962"
    assert compact_number(0) == "0"
    assert compact_number(None) == "—"


def test_compact_number_scales() -> None:
    assert compact_number(6266493) == "6.27M"
    assert compact_number(626000) == "626K"
    assert compact_number(1_270_000) == "1.27M"


def test_display_date_iso() -> None:
    assert display_date("2024-03-11T12:00:00+00:00") == "2024-03-11"


def test_heatmap_has_month_labels_and_wrap() -> None:
    html = day_heatmap({"2024-03-04": 1, "2024-03-05": 2, "2024-04-01": 1})
    assert "heatmap-wrap" in html
    assert "Mar 2024" in html
    assert "Apr 2024" in html
    assert "title=\"2024-03-04: 1 commits\"" in html