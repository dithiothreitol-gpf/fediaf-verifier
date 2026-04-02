"""Create GitHub issues via the REST API."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass

from loguru import logger


@dataclass
class IssueResult:
    success: bool
    number: int | None = None
    url: str | None = None
    error: str | None = None


def create_issue(
    token: str,
    repo: str,
    title: str,
    body: str,
    labels: list[str] | None = None,
) -> IssueResult:
    """Create a GitHub issue via REST API.

    Parameters
    ----------
    token:  Personal Access Token (needs ``repo`` scope for private repos).
    repo:   Owner/repo, e.g. ``"Global-Pets-Food/fediaf-verifier"``.
    title:  Issue title.
    body:   Issue body (markdown).
    labels: Optional list of label names (must already exist in the repo).
    """
    url = f"https://api.github.com/repos/{repo}/issues"
    payload: dict = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            logger.info("GitHub issue #{} created: {}", result["number"], result["html_url"])
            return IssueResult(
                success=True,
                number=result["number"],
                url=result["html_url"],
            )
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode(errors="replace")
        logger.error("GitHub API error {}: {}", exc.code, error_body)
        return IssueResult(success=False, error=f"GitHub API {exc.code}: {error_body}")
    except Exception as exc:
        logger.error("GitHub issue creation failed: {}", exc)
        return IssueResult(success=False, error=str(exc))
