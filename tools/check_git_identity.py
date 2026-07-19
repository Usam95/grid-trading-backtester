"""Reject commits unless both Git identities use the workspace personal email."""

from __future__ import annotations

import re
import subprocess
import sys


REQUIRED_EMAIL = "usam.sersultanov@gmail.com"


def identity(variable: str) -> str:
    result = subprocess.run(
        ["git", "var", variable],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout.strip() or f"git var {variable} failed")
    match = re.search(r"<([^>]*)>", result.stdout)
    if match is None:
        raise RuntimeError(f"could not parse {variable}")
    return match.group(1)


def main() -> int:
    try:
        author = identity("GIT_AUTHOR_IDENT")
        committer = identity("GIT_COMMITTER_IDENT")
    except RuntimeError as error:
        print(f"Commit rejected: {error}", file=sys.stderr)
        return 1
    if author == REQUIRED_EMAIL and committer == REQUIRED_EMAIL:
        return 0
    print(
        "\n".join(
            (
                "Commit rejected: this workspace permits only the configured personal email.",
                f"Expected:  {REQUIRED_EMAIL}",
                f"Author:    {author}",
                f"Committer: {committer}",
            )
        ),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
