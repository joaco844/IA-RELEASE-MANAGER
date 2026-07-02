#!/usr/bin/env python3
"""Seed a demo GitLab project to test AI Release Manager.

Creates a new project in your namespace with everything the workflow consumes:

  - labels (feature, bug, performance, security, ...)
  - base commits + tag v1.0.0 + a published release for v1.0.0 (RAG history)
  - issues: some closed by merge requests, some closed manually, some open
  - merged MRs with "Closes #N" descriptions (traceability for the QA agent)
  - direct commits to main (fixes, docs, chores)
  - tag v1.1.0 (no release attached — that's what the app will generate)

Usage:
    export GITLAB_TOKEN=glpat-xxxxxxxxxxxx        # scope: api
    python scripts/seed_gitlab_demo.py
    python scripts/seed_gitlab_demo.py --url https://gitlab.mycompany.com --name my-demo

Requires: pip install python-gitlab   (already a backend dependency:
    backend/.venv/bin/python scripts/seed_gitlab_demo.py)
"""

from __future__ import annotations

import argparse
import os
import sys
import time

try:
    import gitlab
except ImportError:
    sys.exit("python-gitlab not installed. Run: pip install python-gitlab "
             "(or use backend/.venv/bin/python)")

LABELS = [
    ("feature", "#2da160"),
    ("bug", "#dc3545"),
    ("performance", "#f0ad4e"),
    ("security", "#6f42c1"),
    ("refactoring", "#0d6efd"),
    ("documentation", "#6c757d"),
    ("infrastructure", "#fd7e14"),
]

V1_RELEASE_NOTES = """## v1.0.0 — Initial release

### Features
- User authentication with JWT (login, register, refresh).
- Transactions API with filtering and pagination.
- Basic reporting dashboard.

### Infrastructure
- Dockerized deployment with health checks.
"""


def log(msg: str) -> None:
    print(f"  ✓ {msg}")


def commit(project, branch: str, message: str, files: dict[str, str],
           update: bool = False) -> None:
    """Create a commit on `branch` creating (or updating) the given files."""
    action = "update" if update else "create"
    project.commits.create({
        "branch": branch,
        "commit_message": message,
        "actions": [{"action": action, "file_path": p, "content": c}
                    for p, c in files.items()],
    })
    log(f"commit on {branch}: {message.splitlines()[0]}")


def merge_mr(project, mr) -> None:
    """Wait until GitLab computes mergeability, then merge."""
    for _ in range(20):
        fresh = project.mergerequests.get(mr.iid)
        status = getattr(fresh, "detailed_merge_status", None) or fresh.merge_status
        if status in ("mergeable", "can_be_merged"):
            fresh.merge(should_remove_source_branch=True)
            log(f"merged MR !{mr.iid}: {mr.title}")
            return
        time.sleep(2)
    raise RuntimeError(f"MR !{mr.iid} never became mergeable (status={status})")


def feature_mr(project, *, branch: str, title: str, description: str,
               labels: list[str], commits: list[tuple[str, dict[str, str]]]) -> None:
    """Create branch from main, commit, open MR, merge it."""
    project.branches.create({"branch": branch, "ref": "main"})
    for message, files in commits:
        commit(project, branch, message, files)
    mr = project.mergerequests.create({
        "source_branch": branch,
        "target_branch": "main",
        "title": title,
        "description": description,
        "labels": labels,
    })
    merge_mr(project, mr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("GITLAB_URL", "https://gitlab.com"))
    parser.add_argument("--name", default="ai-release-manager-demo",
                        help="name of the project to create")
    args = parser.parse_args()

    token = os.environ.get("GITLAB_TOKEN")
    if not token:
        sys.exit("Set GITLAB_TOKEN (personal access token with 'api' scope).")

    gl = gitlab.Gitlab(args.url, private_token=token)
    gl.auth()
    print(f"\nAuthenticated as {gl.user.username} on {args.url}")

    # ── Project ──────────────────────────────────────────────────────────
    project = gl.projects.create({
        "name": args.name,
        "description": "Demo payments service — seeded to test AI Release Manager",
        "visibility": "private",
    })
    log(f"project created: {project.path_with_namespace}")
    time.sleep(2)  # let GitLab finish initializing the repo

    for name, color in LABELS:
        project.labels.create({"name": name, "color": color})
    log(f"{len(LABELS)} labels created")

    # ── Base history + v1.0.0 ────────────────────────────────────────────
    commit(project, "main", "chore: initial project scaffold", {
        "README.md": "# Payments Service\n\nDemo service for AI Release Manager.\n",
        "app/main.py": "def create_app():\n    return App()\n",
        "app/config.py": "DEBUG = False\nDB_URL = 'postgresql://localhost/payments'\n",
    })
    commit(project, "main", "feat: JWT authentication (login, register, refresh)", {
        "app/auth.py": "def login(email, password):\n    ...\n\ndef register(email, password):\n    ...\n",
    })
    commit(project, "main", "feat: transactions API with filtering and pagination", {
        "app/transactions.py": "def list_transactions(filters, page, size):\n    ...\n",
    })

    project.tags.create({"tag_name": "v1.0.0", "ref": "main"})
    project.releases.create({
        "name": "v1.0.0",
        "tag_name": "v1.0.0",
        "description": V1_RELEASE_NOTES,
    })
    log("tag v1.0.0 + release published (RAG history)")

    # ── Issues ───────────────────────────────────────────────────────────
    def issue(title, description, labels):
        i = project.issues.create({"title": title, "description": description,
                                   "labels": labels})
        log(f"issue #{i.iid}: {title}")
        return i

    i_login = issue(
        "Login fails with 500 when email contains uppercase letters",
        "Users registering with `John@Example.com` cannot log in later. "
        "The lookup is case-sensitive while registration lowercases the email.",
        ["bug"])
    i_csv = issue(
        "Add CSV export for transaction reports",
        "Finance team needs to export filtered transactions as CSV "
        "from the reports view for monthly reconciliation.",
        ["feature"])
    i_perf = issue(
        "Dashboard is slow with more than 10k transactions",
        "Loading the dashboard takes 8+ seconds for large accounts. "
        "The transactions query has no index and loads everything in memory.",
        ["performance"])
    i_jwt = issue(
        "Upgrade JWT library to patch known vulnerability",
        "Our pinned version of pyjwt is affected by a signature-bypass advisory. "
        "Upgrade and rotate signing keys.",
        ["security"])
    i_rate = issue(
        "Add rate limiting to public API endpoints",
        "Public endpoints are unprotected against abuse. Add per-IP rate limiting.",
        ["feature", "security"])
    i_docs = issue(
        "Improve onboarding documentation",
        "The README lacks setup instructions for local development.",
        ["documentation"])
    # Left open on purpose (should NOT appear in the release):
    issue("Refactor payment gateway adapter",
          "The Stripe adapter mixes transport and business logic. Split it.",
          ["refactoring"])
    issue("Add dark mode support",
          "Several customers requested a dark theme for the dashboard.",
          ["feature"])

    # ── Merge requests (each closes an issue) ────────────────────────────
    feature_mr(project,
        branch="fix/login-email-case",
        title="Fix case-sensitive email lookup on login",
        description=f"Normalizes email to lowercase before lookup.\n\nCloses #{i_login.iid}",
        labels=["bug"],
        commits=[(
            f"fix: lowercase email before user lookup on login\n\nCloses #{i_login.iid}",
            {"app/auth_fix.py": "def normalize_email(email):\n    return email.strip().lower()\n"},
        )])

    feature_mr(project,
        branch="feature/csv-export",
        title="Add CSV export for transaction reports",
        description=f"Adds `/reports/export.csv` honoring active filters.\n\nCloses #{i_csv.iid}",
        labels=["feature"],
        commits=[
            ("feat: CSV export endpoint for transaction reports",
             {"app/export.py": "def export_csv(filters):\n    ...\n"}),
            ("test: coverage for CSV export edge cases",
             {"tests/test_export.py": "def test_export_empty():\n    ...\n"}),
        ])

    feature_mr(project,
        branch="perf/dashboard-query",
        title="Paginate and index dashboard transactions query",
        description=f"Adds DB index + keyset pagination. p95 load 8.2s → 340ms.\n\nCloses #{i_perf.iid}",
        labels=["performance"],
        commits=[(
            "perf: add index and keyset pagination to dashboard query",
            {"migrations/002_add_tx_index.sql": "CREATE INDEX idx_tx_account_date ON transactions(account_id, created_at);\n"},
        )])

    feature_mr(project,
        branch="security/jwt-upgrade",
        title="Upgrade pyjwt and rotate signing keys",
        description=f"Patches the signature-bypass advisory.\n\nCloses #{i_jwt.iid}",
        labels=["security"],
        commits=[(
            "fix(security): upgrade pyjwt to patched version, rotate keys",
            {"requirements.txt": "pyjwt==2.10.1\nfastapi\nsqlalchemy\n"},
        )])

    # ── Direct commits to main + manual issue closes ─────────────────────
    commit(project, "main",
           f"feat: per-IP rate limiting on public endpoints\n\nRefs #{i_rate.iid}",
           {"app/ratelimit.py": "LIMITS = {'default': '120/minute'}\n"})
    commit(project, "main",
           f"docs: local development setup guide\n\nRefs #{i_docs.iid}",
           {"docs/setup.md": "# Local setup\n\n1. Install deps\n2. Run migrations\n3. Start the server\n"})
    commit(project, "main", "chore: bump dependencies and CI image",
           {".gitlab-ci.yml": "image: python:3.12\nstages: [test]\n"})

    for i in (i_rate, i_docs):
        i.state_event = "close"
        i.save()
    log(f"issues #{i_rate.iid} and #{i_docs.iid} closed manually")

    # ── v1.1.0 tag (no release — the app generates it) ───────────────────
    project.tags.create({"tag_name": "v1.1.0", "ref": "main"})
    log("tag v1.1.0 created (no release attached)")

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"""
{'=' * 62}
Done! Project ready: {project.web_url}

To test AI Release Manager, connect the repo in the UI with:
  GitLab URL:    {args.url}
  Project path:  {project.path_with_namespace}
  Access token:  (the same GITLAB_TOKEN you used here)

Then generate a release with range:  v1.0.0 → v1.1.0
Expected result: ~4 merged MRs, 6 closed issues, ~10 commits,
categories: Features, Bug Fixes, Performance, Security, Docs, Infra.
The 2 open issues should NOT appear in the notes.
{'=' * 62}""")


if __name__ == "__main__":
    main()
