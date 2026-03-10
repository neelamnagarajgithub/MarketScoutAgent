# app/fetchers/github.py
import httpx
from typing import List

GITHUB_API = "https://api.github.com"

async def fetch_org_repos(client: httpx.AsyncClient, token: str, org: str, per_page: int = 50) -> List[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GITHUB_API}/orgs/{org}/repos"
    params = {"per_page": per_page, "type": "all", "sort": "updated"}
    r = await client.get(url, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

async def fetch_repo_readme(client: httpx.AsyncClient, token: str, owner: str, repo: str) -> str:
    headers = {"Accept": "application/vnd.github.v3.html", "Authorization": f"Bearer {token}"}
    url = f"{GITHUB_API}/repos/{owner}/{repo}/readme"
    r = await client.get(url, headers=headers, timeout=15)
    if r.status_code == 200:
        return r.text
    return ""