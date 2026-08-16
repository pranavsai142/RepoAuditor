from __future__ import annotations

import html
from datetime import date

from repoauditor import CAVEAT, PRIVACY


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
    repo_rows = "".join(_repo_row(r) for r in repos)
    people_rows = "".join(_person_row(p) for p in people if not p.get("is_bot"))
    finding_cards = "".join(_finding_card(f) for f in findings)
    rank_repos = _rank_list(rankings.get("repos", {}).get("by_last_commit", []))
    analysis_cards = "".join(_analysis_card(a) for a in analysis or [])
    assist_rows = "".join(_assist_row(a) for a in (assistance or {}).get("assistants") or [])
    exec_html = _executive_html(executive)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>RepoAuditor scan</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem; color: #111; }}
    .caveat {{ background: #fff3cd; border: 1px solid #e6c200; padding: 1rem; }}
    .privacy {{ color: #555; font-size: 0.9rem; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left; vertical-align: top; }}
    th {{ background: #f4f4f4; }}
    .finding {{ border: 1px solid #bbb; padding: 0.8rem; margin: 0.8rem 0; }}
    code {{ font-size: 0.85em; }}
  </style>
</head>
<body>
  <h1>RepoAuditor</h1>
  <p>Input: <code>{esc(input_path)}</code> · as-of {as_of.isoformat()} · commit authors only</p>
  <p class="caveat">{esc(CAVEAT)}</p>
  <p class="privacy">{esc(PRIVACY)}</p>
  {exec_html}

  <h2>Repos ranked by last commit (oldest first)</h2>
  {rank_repos}

  <h2>Repos</h2>
  <table>
    <thead>
      <tr>
        <th>repo</th><th>last commit</th><th>commits</th>
        <th>humans</th><th>additions</th><th>deletions</th>
        <th>net</th><th>churn</th><th>files</th>
      </tr>
    </thead>
    <tbody>{repo_rows}</tbody>
  </table>

  <h2>People</h2>
  <table>
    <thead>
      <tr>
        <th>name</th><th>email</th><th>last commit</th>
        <th>commits</th><th>repos</th><th>durable</th><th>thin</th><th>days</th>
        <th>additions</th><th>deletions</th><th>churn</th>
      </tr>
    </thead>
    <tbody>{people_rows}</tbody>
  </table>

  <h2>Coding assistance inventory</h2>
  <p>Fingerprints from commit authors, trailers, and subjects. Not proof a human did no work.</p>
  {f"<table><thead><tr><th>assistant</th><th>commits</th><th>repos</th></tr></thead><tbody>{assist_rows}</tbody></table>" if assist_rows else "<p>No assistant fingerprints in this scan.</p>"}

  <h2>Findings</h2>
  <p>Flags rank what to inspect. They are not verdicts.</p>
  {finding_cards or "<p>No founding-pattern flags.</p>"}

  <h2>Per-repo interpretation</h2>
  <p>Grok read the pack plus source and workflows. Scripts cannot substitute for this.</p>
  {analysis_cards or "<p>No per-repo interpretation yet. Product scan runs Grok; <code>--no-analyze</code> is harness-only.</p>"}
</body>
</html>
"""


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _repo_row(repo: dict) -> str:
    return (
        "<tr>"
        f"<td><code>{esc(repo['repo_id'])}</code></td>"
        f"<td>{esc(repo.get('last_commit'))}</td>"
        f"<td>{esc(repo.get('commit_count'))}</td>"
        f"<td>{esc(repo.get('human_contributor_count'))}</td>"
        f"<td>{esc(repo.get('additions'))}</td>"
        f"<td>{esc(repo.get('deletions'))}</td>"
        f"<td>{esc(repo.get('net'))}</td>"
        f"<td>{esc(repo.get('churn'))}</td>"
        f"<td>{esc(repo.get('files_changed'))}</td>"
        "</tr>"
    )


def _person_row(person: dict) -> str:
    return (
        "<tr>"
        f"<td>{esc(person.get('author_name'))}</td>"
        f"<td><code>{esc(person.get('author_email'))}</code></td>"
        f"<td>{esc(person.get('last_commit'))}</td>"
        f"<td>{esc(person.get('commit_count'))}</td>"
        f"<td>{esc(person.get('repo_count'))}</td>"
        f"<td>{esc(person.get('durable_repo_count'))}</td>"
        f"<td>{esc(person.get('thin_repo_count'))}</td>"
        f"<td>{esc(person.get('distinct_days'))}</td>"
        f"<td>{esc(person.get('additions'))}</td>"
        f"<td>{esc(person.get('deletions'))}</td>"
        f"<td>{esc(person.get('churn'))}</td>"
        "</tr>"
    )


def _finding_card(finding: dict) -> str:
    hashes = finding.get("evidence", {}).get("commit_hashes") or []
    hash_list = "".join(f"<li><code>{esc(h)}</code></li>" for h in hashes)
    return (
        f'<article class="finding" data-pattern="{esc(finding["pattern"])}">'
        f"<h3>{esc(finding['pattern'])} · {esc(finding['lens'])} · "
        f"<code>{esc(finding['subject_id'])}</code></h3>"
        f"<p>{esc(finding['summary'])}</p>"
        f"<p>Evidence commits:</p><ul>{hash_list}</ul>"
        "</article>"
    )


def _rank_list(ids: list[str]) -> str:
    items = "".join(f"<li><code>{esc(i)}</code></li>" for i in ids)
    return f"<ol>{items}</ol>"


def _named_list(items: list | None, key: str) -> str:
    if not items:
        return "<p>None listed.</p>"
    rows = "".join(
        f"<li><code>{esc(item.get(key))}</code> — {esc(item.get('why'))}</li>"
        for item in items
    )
    return f"<ul>{rows}</ul>"


def _executive_html(executive: dict | None) -> str:
    if not executive:
        return (
            "<h2>Executive summary</h2>"
            "<p>Waiting on headless Grok. Product <code>scan</code> always runs it; "
            "<code>--no-analyze</code> is only for the test harness.</p>"
        )
    unscripted = "".join(
        f"<li>{esc(item.get('observation'))} "
        f"(<code>{esc(item.get('evidence'))}</code>)</li>"
        for item in executive.get("unscriptable") or []
    )
    nxt = "".join(f"<li>{esc(item)}</li>" for item in executive.get("open_next") or [])
    return (
        "<h2>Executive summary</h2>"
        f"<p><strong>{esc(executive.get('headline'))}</strong></p>"
        f"<p>{esc(executive.get('executive_summary'))}</p>"
        "<h3>Run the business</h3>"
        f"{_named_list(executive.get('run_the_business'), 'repo_id')}"
        "<h3>Theater</h3>"
        f"{_named_list(executive.get('theater'), 'repo_id')}"
        "<h3>Who appears to carry durable work</h3>"
        f"{_named_list(executive.get('who_matters'), 'name')}"
        "<h3>Who to inspect</h3>"
        f"{_named_list(executive.get('who_to_inspect'), 'name')}"
        f"<h3>Assistance</h3><p>{esc(executive.get('assistance'))}</p>"
        f"<h3>What scripts cannot see</h3><ul>{unscripted}</ul>"
        f"<h3>Open next</h3><ol>{nxt}</ol>"
    )


def _assist_row(row: dict) -> str:
    return (
        "<tr>"
        f"<td><code>{esc(row.get('id'))}</code></td>"
        f"<td>{esc(row.get('commit_count'))}</td>"
        f"<td>{esc(row.get('repo_count'))}</td>"
        "</tr>"
    )


def _analysis_card(report: dict) -> str:
    checks = "".join(
        "<li>"
        f"<strong>{esc(item.get('id'))}</strong> "
        f"{'· concern ' if item.get('concern') else ''}"
        f"— {esc(item.get('answer'))}"
        "</li>"
        for item in report.get("checklist") or []
    )
    inspect = "".join(
        f"<li><code>{esc(item.get('hash'))}</code> — {esc(item.get('why'))}</li>"
        for item in report.get("next_inspect") or []
    )
    return (
        f'<article class="finding" data-repo="{esc(report.get("repo_id"))}">'
        f"<h3><code>{esc(report.get('repo_id'))}</code> · {esc(report.get('category'))}</h3>"
        f"<p>{esc(report.get('purpose'))}</p>"
        f"<ol>{checks}</ol>"
        f"<p>Open first:</p><ul>{inspect}</ul>"
        "</article>"
    )
