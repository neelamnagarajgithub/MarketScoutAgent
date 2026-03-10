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

async def scrape_reddit_posts(client: httpx.AsyncClient, subreddit: str, sort: str = "hot", limit: int = 25) -> List[dict]:
    """Scrape Reddit posts without API (no authentication needed)"""
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; MarketAggregator/1.0)"
    }
    params = {"limit": limit}
    
    try:
        r = await client.get(url, headers=headers, params=params, timeout=15)
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
                    "provider": "reddit_scraper",
                    "subreddit": subreddit,
                    "score": post_data.get("score"),
                    "num_comments": post_data.get("num_comments"),
                    "author": post_data.get("author"),
                    "flair": post_data.get("link_flair_text"),
                    "permalink": f"https://reddit.com{post_data.get('permalink', '')}"
                }
            })
        return results
    except Exception as e:
        print(f"Reddit scraping error: {e}")
        return []

async def scrape_hackernews_search(client: httpx.AsyncClient, query: str, num_results: int = 20) -> List[dict]:
    """Search Hacker News using Algolia API"""
    url = "https://hn.algolia.com/api/v1/search"
    params = {
        "query": query,
        "tags": "story",
        "hitsPerPage": num_results
    }
    
    try:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        results = []
        for hit in data.get("hits", []):
            results.append({
                "title": hit.get("title", ""),
                "url": hit.get("url", f"https://news.ycombinator.com/item?id={hit.get('objectID')}"),
                "content": hit.get("story_text", ""),
                "publishedAt": hit.get("created_at"),
                "metadata": {
                    "provider": "hackernews_search",
                    "points": hit.get("points", 0),
                    "num_comments": hit.get("num_comments", 0),
                    "author": hit.get("author"),
                    "story_id": hit.get("objectID"),
                    "created_at_i": hit.get("created_at_i")
                }
            })
        return results
    except Exception as e:
        print(f"Hacker News search error: {e}")
        return []

async def fetch_indie_hackers_posts(client: httpx.AsyncClient, query: str = None, limit: int = 20) -> List[dict]:
    """Scrape Indie Hackers posts (no official API)"""
    url = "https://www.indiehackers.com/posts"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; MarketAggregator/1.0)"
    }
    
    try:
        r = await client.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        
        # Basic HTML parsing for Indie Hackers posts
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        
        results = []
        post_elements = soup.find_all('div', class_='post-card', limit=limit)
        
        for post in post_elements:
            title_elem = post.find('h3') or post.find('h2')
            link_elem = post.find('a')
            
            if title_elem and link_elem:
                title = title_elem.get_text(strip=True)
                url = f"https://www.indiehackers.com{link_elem.get('href', '')}"
                
                # Filter by query if provided
                if query and query.lower() not in title.lower():
                    continue
                
                results.append({
                    "title": title,
                    "url": url,
                    "content": "Indie Hackers community post",
                    "publishedAt": None,
                    "metadata": {
                        "provider": "indie_hackers",
                        "platform": "community"
                    }
                })
        
        return results[:limit]
    except Exception as e:
        print(f"Indie Hackers scraping error: {e}")
        return []

async def fetch_betalist_startups(client: httpx.AsyncClient, category: str = None, limit: int = 20) -> List[dict]:
    """Scrape BetaList for startup information"""
    url = "https://betalist.com/startups"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; MarketAggregator/1.0)"
    }
    
    try:
        r = await client.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        
        results = []
        startup_elements = soup.find_all('div', class_='startup-item', limit=limit)
        
        for startup in startup_elements:
            title_elem = startup.find('h3') or startup.find('h2')
            desc_elem = startup.find('p')
            link_elem = startup.find('a')
            
            if title_elem:
                title = title_elem.get_text(strip=True)
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                url = f"https://betalist.com{link_elem.get('href', '')}" if link_elem else ""
                
                results.append({
                    "title": title,
                    "url": url,
                    "content": description,
                    "publishedAt": None,
                    "metadata": {
                        "provider": "betalist",
                        "platform": "startup_directory",
                        "category": category
                    }
                })
        
        return results[:limit]
    except Exception as e:
        print(f"BetaList scraping error: {e}")
        return []