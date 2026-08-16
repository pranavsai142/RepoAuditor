from __future__ import annotations

from repoauditor.auditor.substance import classify_line, parse_patch, path_kind, score_counts


def test_path_and_line_kinds() -> None:
    assert path_kind("engine.py") == "code"
    assert path_kind("README.md") == "docs"
    assert path_kind("NOTES.md") == "docs"
    assert classify_line("# todo", "code") == "comment"
    assert classify_line("def main():", "code") == "code"
    assert classify_line("hello", "docs") == "docs"


def test_comment_only_patch_is_no_code() -> None:
    patch = """diff --git a/engine.py b/engine.py
--- a/engine.py
+++ b/engine.py
@@ -1,3 +1,6 @@
 # matching engine entry
 # TODO implement
 # still planning
+# status ping 0
+# status ping 1
+# status ping 2
"""
    scored = score_counts(parse_patch(patch))
    assert scored["code_lines"] == 0
    assert scored["comment_lines"] == 3
    assert scored["no_code"] is True
    assert scored["comment_or_docs_only"] is True
