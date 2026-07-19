from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PERSONAL_EMAIL = "usam.sersultanov@gmail.com"


def _git(
    repo: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def test_repository_identity_resolves_to_personal_email() -> None:
    for identity in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"):
        result = _git(ROOT, "var", identity)
        assert result.returncode == 0
        assert f"<{PERSONAL_EMAIL}>" in result.stdout


def test_identity_hook_accepts_only_the_personal_email() -> None:
    accepted_environment = os.environ.copy()
    accepted_environment.update(
        {
            "GIT_AUTHOR_NAME": "Accepted Identity",
            "GIT_AUTHOR_EMAIL": PERSONAL_EMAIL,
            "GIT_COMMITTER_NAME": "Accepted Identity",
            "GIT_COMMITTER_EMAIL": PERSONAL_EMAIL,
        }
    )
    accepted = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "check_git_identity.py")],
        cwd=ROOT,
        env=accepted_environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert accepted.returncode == 0, accepted.stdout

    rejected_environment = accepted_environment.copy()
    rejected_environment.update(
        {
            "GIT_AUTHOR_EMAIL": "not-allowed@example.invalid",
            "GIT_COMMITTER_EMAIL": "not-allowed@example.invalid",
        }
    )
    rejected = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "check_git_identity.py")],
        cwd=ROOT,
        env=rejected_environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert rejected.returncode != 0
    assert "Commit rejected" in rejected.stdout
