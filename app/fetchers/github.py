"""
GitHub fetcher – uses Personal Access Token (PAT) exclusively.
  Authorization: token <PAT>
"""

import httpx
from typing import List, Dict, Optional
from datetime import datetime, timedelta

GITHUB_API = "https://api.github.com"


def _headers(pat: str) -> Dict[str, str]:
    return {
        "Authorization": f"token {pat}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def fetch_org_repos(
    client: httpx.AsyncClient, pat: str, org: str, per_page: int = 50
) -> List[dict]:
    r = await client.get(
        f"{GITHUB_API}/orgs/{org}/repos",
        headers=_headers(pat),
        params={"per_page": per_page, "type": "all", "sort": "updated"},
        timeout=15,
    )
    r.raise_for_status()
    return [_normalise_repo(repo, org) for repo in r.json()]


async def fetch_trending_repos(
    client: httpx.AsyncClient,
    pat: str,
    language: str = "",
    days: int = 7,
) -> List[dict]:
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    q = f"created:>{since}" + (f" language:{language}" if language else "")
    r = await client.get(
        f"{GITHUB_API}/search/repositories",
        headers=_headers(pat),
        params={"q": q, "sort": "stars", "order": "desc", "per_page": 30},
        timeout=15,
    )
    r.raise_for_status()
    return [_normalise_repo(repo) for repo in r.json().get("items", [])]


async def fetch_repo_releases(
    client: httpx.AsyncClient, pat: str, owner: str, repo: str, per_page: int = 10
) -> List[dict]:
    r = await client.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/releases",
        headers=_headers(pat),
        params={"per_page": per_page},
        timeout=15,
    )
    r.raise_for_status()
    return [
        {
            "title": rel.get("name") or rel.get("tag_name"),
            "url": rel.get("html_url"),
            "content": (rel.get("body") or "")[:500],
            "publishedAt": rel.get("published_at"),
            "metadata": {
                "provider": "github_releases",
                "repo": f"{owner}/{repo}",
                "tag": rel.get("tag_name"),
                "prerelease": rel.get("prerelease"),
                "author": (rel.get("author") or {}).get("login"),
            },
        }
        for rel in r.json()
    ]


async def search_github_code(
    client: httpx.AsyncClient, pat: str, query: str, per_page: int = 20
) -> List[dict]:
    r = await client.get(
        f"{GITHUB_API}/search/repositories",
        headers=_headers(pat),
        params={"q": query, "sort": "stars", "order": "desc", "per_page": per_page},
        timeout=15,
    )
    r.raise_for_status()
    return [_normalise_repo(repo) for repo in r.json().get("items", [])]


# ── Private ────────────────────────────────────────────────────────────────────
def _normalise_repo(repo: dict, org: str = "") -> dict:
    return {
        "title": repo.get("name"),
        "url": repo.get("html_url"),
        "content": repo.get("description") or "",
        "publishedAt": repo.get("updated_at"),
        "metadata": {
            "provider": "github",
            "org": org or (repo.get("owner") or {}).get("login"),
            "language": repo.get("language"),
            "stars": repo.get("stargazers_count"),
            "forks": repo.get("forks_count"),
            "open_issues": repo.get("open_issues_count"),
            "topics": repo.get("topics", []),
            "created_at": repo.get("created_at"),
            "updated_at": repo.get("updated_at"),
        },
    }