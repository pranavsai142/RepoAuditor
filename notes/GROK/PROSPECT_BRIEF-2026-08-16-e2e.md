# Prospect Brief: RepoAuditor v1 — local-dir ingest → facts → flags → evidence

Produced by `/fieldgoal` + `/fabel-open-ended` on 2026-08-16. This is the implementation contract.

**Sharpened Objective**

Build the whole RepoAuditor pipeline as a **Python CLI** that, given one local directory of already-cloned repos, (1) discovers every nested git repo, (2) extracts a **reproducible commit/contributor fact table** using first-party `git` as the only oracle, (3) assimilates department-scale **repo + people** views without silently merging identities, (4) ranks by last commit / honest line volume / distinct humans, (5) flags **all eight** founding patterns from `SOUL_DRIVER.md`, each with a path back to exact commits, and (6) emits JSON + static HTML.

**Input lock:** a folder that already contains the department’s repos. No GitHub/GitLab discovery, no clone, no PAT.

Full locks (discovery, `--all`, author=person, identity pair, bots, tree+patch-id, UTC/`--as-of`, stack, thresholds, fixture catalog, argv) are in this file’s source session and restated in `notes/WIKI/system.md`.

**Harness:** `scripts/verify.sh` → fixture department + pytest.

**Just-Go:** stop only on real gate failure (`git` missing, fixture build fail, assertion fail, finding without hashes, silent identity merge, healthy-team false positive, parser ≠ `git log --numstat`, or someone adding remote discovery / SPA / GitPython).
