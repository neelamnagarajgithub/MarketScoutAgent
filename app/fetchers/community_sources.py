"""
Community sources
  • Reddit   – public JSON (no API key, no OAuth)
  • HackerNews – Firebase + Algolia (both free, no key)
  • Mastodon  – access token
  • Stack Overflow – free, no key
"""

import httpx
from typing import List, Optional
from datetime import datetime


# ─────────────────────────── Reddit (no key) ─────────────────────────────────
async def scrape_reddit_posts(
    client: httpx.AsyncClient,
    subreddit: str,
    sort: str = "hot",
    limit: int = 25,
) -> List[dict]:
    """Read Reddit without any API key – public .json endpoint."""
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    r = await client.get(
        url,
        headers={"User-Agent": "MarketScoutBot/1.0 (educational)"},
        params={"limit": limit},
        timeout=15,
    )
    r.raise_for_status()
    posts = []
    for child in r.json().get("data", {}).get("children", []):
        d = child["data"]
        if d.get("is_promoted") or not d.get("title"):
            continue
        pub = datetime.utcfromtimestamp(d["created_utc"]).isoformat() if d.get("created_utc") else None
        posts.append(
            {
                "title": d.get("title"),
                "url": f"https://reddit.com{d.get('permalink')}" if d.get("permalink") else d.get("url"),
                "content": (d.get("selftext") or "")[:500],
                "publishedAt": pub,
                "metadata": {
                    "provider": "reddit",
                    "subreddit": subreddit,
                    "score": d.get("score"),
                    "num_comments": d.get("num_comments"),
                    "author": d.get("author"),
                    "upvote_ratio": d.get("upvote_ratio"),
                    "flair": d.get("link_flair_text"),
                    "domain": d.get("domain"),
                },
            }
        )
    return posts


# ─────────────────────────── Hacker News ─────────────────────────────────────
async def fetch_hackernews_stories(
    client: httpx.AsyncClient,
    story_type: str = "topstories",
    limit: int = 30,
) -> List[dict]:
    """Firebase HN API – completely free, no key."""
    base = "https://hacker-news.firebaseio.com/v0"
    r = await client.get(f"{base}/{story_type}.json", timeout=10)
    r.raise_for_status()
    ids = r.json()[:limit]

    stories = []
    for sid in ids[:20]:
        try:
            sr = await client.get(f"{base}/item/{sid}.json", timeout=5)
            s = sr.json()
            if s and s.get("type") == "story":
                pub = datetime.utcfromtimestamp(s["time"]).isoformat() if s.get("time") else None
                stories.append(
                    {
                        "title": s.get("title"),
                        "url": s.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                        "content": (s.get("text") or "")[:400],
                        "publishedAt": pub,
                        "metadata": {
                            "provider": "hackernews",
                            "story_type": story_type,
                            "score": s.get("score"),
                            "comments": s.get("descendants", 0),
                            "author": s.get("by"),
                            "hn_id": sid,
                        },
                    }
                )
        except Exception:
            continue
    return stories


async def scrape_hackernews_search(
    client: httpx.AsyncClient, query: str, num_results: int = 20
) -> List[dict]:
    """Algolia HN search – free, no key. Docs: https://hn.algolia.com/api"""
    r = await client.get(
        "https://hn.algolia.com/api/v1/search",
        params={"query": query, "tags": "story", "hitsPerPage": num_results},
        timeout=15,
    )
    r.raise_for_status()
    results = []
    for h in r.json().get("hits", []):
        results.append(
            {
                "title": h.get("title", ""),
                "url": h.get("url", f"https://news.ycombinator.com/item?id={h.get('objectID')}"),
                "content": (h.get("story_text") or "")[:400],
                "publishedAt": h.get("created_at"),
                "metadata": {
                    "provider": "hackernews_search",
                    "points": h.get("points", 0),
                    "num_comments": h.get("num_comments", 0),
                    "author": h.get("author"),
                    "hn_id": h.get("objectID"),
                },
            }
        )
    return results


# ─────────────────────────── Mastodon ────────────────────────────────────────
async def fetch_mastodon_timeline(
    client: httpx.AsyncClient,
    access_token: str,
    instance: str = "mastodon.social",
    hashtag: Optional[str] = None,
    limit: int = 20,
) -> List[dict]:
    if "urn:ietf" in instance or not instance:
        instance = "mastodon.social"
    if not instance.startswith("http"):
        instance = f"https://{instance}"

    url = (
        f"{instance}/api/v1/timelines/tag/{hashtag}"
        if hashtag
        else f"{instance}/api/v1/timelines/public"
    )
    r = await client.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        params={"limit": limit},
        timeout=15,
    )
    r.raise_for_status()
    results = []
    for post in r.json():
        acc = post.get("account", {})
        results.append(
            {
                "title": f"Mastodon @{acc.get('username', 'unknown')}",
                "url": post.get("url"),
                "content": (post.get("content") or "")[:500],
                "publishedAt": post.get("created_at"),
                "metadata": {
                    "provider": "mastodon",
                    "instance": instance,
                    "author": acc.get("username"),
                    "display_name": acc.get("display_name"),
                    "favourites": post.get("favourites_count"),
                    "reblogs": post.get("reblogs_count"),
                    "tags": [t.get("name") for t in post.get("tags", [])],
                    "language": post.get("language"),
                },
            }
        )
    return results


# ─────────────────────────── Stack Overflow ──────────────────────────────────
async def fetch_stackoverflow_questions(
    client: httpx.AsyncClient,
    tagged: str,
    sort: str = "votes",
    pagesize: int = 20,
) -> List[dict]:
    """Stack Exchange API v2.3 – free, no key for basic usage.
    Docs: https://api.stackexchange.com/docs
    """
    r = await client.get(
        "https://api.stackexchange.com/2.3/questions",
        params={
            "order": "desc",
            "sort": sort,
            "tagged": tagged,
            "site": "stackoverflow",
            "pagesize": pagesize,
        },
        timeout=15,
    )
    r.raise_for_status()
    results = []
    for q in r.json().get("items", []):
        pub = datetime.utcfromtimestamp(q["creation_date"]).isoformat() if q.get("creation_date") else None
        results.append(
            {
                "title": q.get("title"),
                "url": q.get("link"),
                "content": "",
                "publishedAt": pub,
                "metadata": {
                    "provider": "stackoverflow",
                    "score": q.get("score"),
                    "answer_count": q.get("answer_count"),
                    "view_count": q.get("view_count"),
                    "tags": q.get("tags", []),
                    "owner": (q.get("owner") or {}).get("display_name"),
                    "is_answered": q.get("is_answered"),
                },
            }
        )
    return results