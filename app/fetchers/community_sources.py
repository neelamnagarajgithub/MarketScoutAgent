# app/fetchers/community_sources.py
import httpx
from typing import List
import asyncio
import time

async def fetch_product_hunt_posts(client: httpx.AsyncClient, access_token: str, featured_date: str = None, per_page: int = 20) -> List[dict]:
    """Fetch from Product Hunt API"""
    url = "https://api.producthunt.com/v2/api/graphql"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # GraphQL query for posts
    query = """
    query($featured_date: DateTime, $first: Int) {
        posts(featured_date: $featured_date, first: $first) {
            edges {
                node {
                    id
                    name
                    tagline
                    url
                    website
                    featuredAt
                    description
                    votesCount
                    commentsCount
                    topics {
                        edges {
                            node {
                                name
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    variables = {"first": per_page}
    if featured_date:
        variables["featured_date"] = featured_date
    
    try:
        r = await client.post(url, headers=headers, json={"query": query, "variables": variables}, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for edge in data.get("data", {}).get("posts", {}).get("edges", []):
            node = edge["node"]
            results.append({
                "title": node.get("name"),
                "url": node.get("website") or node.get("url"),
                "content": node.get("description") or node.get("tagline"),
                "publishedAt": node.get("featuredAt"),
                "metadata": {
                    "provider": "product_hunt",
                    "votes_count": node.get("votesCount"),
                    "comments_count": node.get("commentsCount"),
                    "topics": [topic["node"]["name"] for topic in node.get("topics", {}).get("edges", [])]
                }
            })
        return results
    except Exception as e:
        print(f"Product Hunt API error: {e}")
        return []

async def fetch_hackernews_stories(client: httpx.AsyncClient, story_type: str = "topstories", limit: int = 30) -> List[dict]:
    """Fetch from Hacker News API"""
    # First get story IDs
    url = f"https://hacker-news.firebaseio.com/v0/{story_type}.json"
    
    try:
        r = await client.get(url, timeout=10)
        r.raise_for_status()
        story_ids = r.json()[:limit]
        
        # Fetch individual stories
        results = []
        for story_id in story_ids:
            story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
            story_r = await client.get(story_url, timeout=5)
            if story_r.status_code == 200:
                story = story_r.json()
                if story and story.get("type") == "story":
                    results.append({
                        "title": story.get("title"),
                        "url": story.get("url"),
                        "content": story.get("text", ""),
                        "publishedAt": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(story.get("time", 0))),
                        "metadata": {
                            "provider": "hackernews",
                            "score": story.get("score"),
                            "descendants": story.get("descendants"),
                            "by": story.get("by")
                        }
                    })
            # Rate limiting
            await asyncio.sleep(0.1)
        
        return results
    except Exception as e:
        print(f"Hacker News API error: {e}")
        return []

async def fetch_reddit_posts(client: httpx.AsyncClient, client_id: str, client_secret: str, user_agent: str, subreddit: str, limit: int = 25) -> List[dict]:
    """Fetch from Reddit API"""
    # Get access token
    auth_url = "https://www.reddit.com/api/v1/access_token"
    auth_data = {"grant_type": "client_credentials"}
    auth_headers = {"User-Agent": user_agent}
    
    try:
        # Basic auth
        import base64
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        auth_headers["Authorization"] = f"Basic {credentials}"
        
        auth_r = await client.post(auth_url, data=auth_data, headers=auth_headers, timeout=10)
        auth_r.raise_for_status()
        token = auth_r.json()["access_token"]
        
        # Fetch posts
        posts_url = f"https://oauth.reddit.com/r/{subreddit}/hot"
        headers = {
            "Authorization": f"bearer {token}",
            "User-Agent": user_agent
        }
        params = {"limit": limit}
        
        r = await client.get(posts_url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for post in data.get("data", {}).get("children", []):
            post_data = post["data"]
            results.append({
                "title": post_data.get("title"),
                "url": post_data.get("url"),
                "content": post_data.get("selftext", ""),
                "publishedAt": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(post_data.get("created_utc", 0))),
                "metadata": {
                    "provider": "reddit",
                    "subreddit": subreddit,
                    "score": post_data.get("score"),
                    "num_comments": post_data.get("num_comments"),
                    "author": post_data.get("author")
                }
            })
        return results
    except Exception as e:
        print(f"Reddit API error: {e}")
        return []