"""
Comprehensive API Key Validator
Covers every key present in config.yaml
GitHub uses PAT (token), Reddit uses public JSON (no key), Supabase checked separately.
"""

import asyncio
import httpx
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class APIKeyValidator:
    def __init__(self, config: Dict):
        self.config = config
        self.validation_results: Dict[str, bool] = {}

    # ── Entry point ────────────────────────────────────────────────────────────
    async def validate_all_keys(self) -> Dict[str, bool]:
        keys = self.config.get("keys", {})
        db_cfg = self.config.get("database", {})

        tasks: List[Tuple[str, any]] = []

        # ── Paid / keyed APIs ─────────────────────────────────────────────────
        _keyed = {
            # Search
            "serpapi":          (self._v_serpapi,       keys.get("serpapi")),
            "shodan":           (self._v_shodan,         keys.get("shodan")),
            # News
            "newsapi":          (self._v_newsapi,        keys.get("newsapi")),
            "gnews":            (self._v_gnews,          keys.get("gnews")),
            "currents":         (self._v_currents,       keys.get("currents")),
            "guardian":         (self._v_guardian,       keys.get("guardian")),
            "nytimes":          (self._v_nytimes,        keys.get("nytimes_key")),
            # Tech / product
            "github_pat":       (self._v_github_pat,     keys.get("github_personal_access_token")),
            "gitlab":           (self._v_gitlab,         keys.get("gitlab")),
            "apollo":           (self._v_apollo,         keys.get("apollo")),
            # Financial
            "alpha_vantage":    (self._v_alpha_vantage,  keys.get("alpha_vantage")),
            "massive":          (self._v_massive,        keys.get("massive")),
            # Social
            "mastodon":         (self._v_mastodon,       keys.get("mastodon_access_token")),
        }

        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            coros = []
            names = []
            for name, (fn, key) in _keyed.items():
                if key and str(key).strip():
                    coros.append(fn(client, key))
                    names.append(name)

            # Free APIs – always validate
            free = {
                "hackernews": self._v_hackernews,
                "yahoo_finance": self._v_yahoo_finance,
                "reddit": self._v_reddit,
                "npm_registry": self._v_npm,
                "pypi": self._v_pypi,
                "stackoverflow": self._v_stackoverflow,
                "coingecko": self._v_coingecko,
            }
            for name, fn in free.items():
                coros.append(fn(client, None))
                names.append(name)

            results = await asyncio.gather(*coros, return_exceptions=True)

        for name, result in zip(names, results):
            ok = result if isinstance(result, bool) else False
            self.validation_results[name] = ok
            icon = "✅" if ok else "❌"
            logger.info("%s %s", icon, name)

        # Supabase / DB check (sync-friendly)
        await self._v_supabase(db_cfg)

        return self.validation_results

    # ── SEARCH ─────────────────────────────────────────────────────────────────
    async def _v_serpapi(self, c, k):
        try:
            r = await c.get("https://serpapi.com/account", params={"api_key": k})
            return r.status_code == 200
        except Exception:
            return False

    async def _v_shodan(self, c, k):
        try:
            r = await c.get(f"https://api.shodan.io/api-info?key={k}")
            return r.status_code == 200
        except Exception:
            return False

    # ── NEWS ───────────────────────────────────────────────────────────────────
    async def _v_newsapi(self, c, k):
        try:
            r = await c.get(
                "https://newsapi.org/v2/top-headlines",
                headers={"X-API-Key": k},
                params={"country": "us", "pageSize": 1},
            )
            return r.status_code == 200
        except Exception:
            return False

    async def _v_gnews(self, c, k):
        try:
            r = await c.get(
                "https://gnews.io/api/v4/search",
                params={"q": "test", "token": k, "max": 1},
            )
            return r.status_code == 200
        except Exception:
            return False

    async def _v_currents(self, c, k):
        try:
            r = await c.get(
                "https://api.currentsapi.services/v1/latest-news",
                headers={"Authorization": k},
                params={"page_size": 1},
            )
            return r.status_code == 200
        except Exception:
            return False

    async def _v_guardian(self, c, k):
        try:
            r = await c.get(
                "https://content.guardianapis.com/search",
                params={"api-key": k, "page-size": 1},
            )
            return r.status_code == 200
        except Exception:
            return False

    async def _v_nytimes(self, c, k):
        try:
            r = await c.get(
                "https://api.nytimes.com/svc/topstories/v2/technology.json",
                params={"api-key": k},
            )
            return r.status_code == 200
        except Exception:
            return False

    # ── TECH / PRODUCT ─────────────────────────────────────────────────────────
    async def _v_github_pat(self, c, k):
        """GitHub Personal Access Token validation."""
        try:
            r = await c.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"token {k}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            return r.status_code == 200
        except Exception:
            return False

    async def _v_gitlab(self, c, k):
        try:
            r = await c.get(
                "https://gitlab.com/api/v4/user",
                headers={"Authorization": f"Bearer {k}"},
            )
            return r.status_code == 200
        except Exception:
            return False

    async def _v_apollo(self, c, k):
        try:
            r = await c.post(
                "https://api.apollo.io/api/v1/organizations/search",
                headers={"Content-Type": "application/json", "Cache-Control": "no-cache", "X-Api-Key": k},
                json={"q_organization_name": "openai", "page": 1, "per_page": 1},
            )
            return r.status_code in (200, 201)
        except Exception:
            return False

    # ── FINANCIAL ──────────────────────────────────────────────────────────────
    async def _v_alpha_vantage(self, c, k):
        try:
            r = await c.get(
                "https://www.alphavantage.co/query",
                params={"function": "GLOBAL_QUOTE", "symbol": "AAPL", "apikey": k},
            )
            data = r.json()
            return "Error Message" not in data and "Note" not in data
        except Exception:
            return False

    async def _v_massive(self, c, k):
        """Massive.com financial API – https://massive.com/docs/rest/quickstart"""
        try:
            r = await c.get(
                "https://data.financial.com/api/v2/dividends",   # adjust per actual docs
                headers={"Authorization": f"Bearer {k}"},
                params={"symbols": "AAPL", "limit": 1},
            )
            return r.status_code in (200, 201)
        except Exception:
            return False

    # ── SOCIAL ─────────────────────────────────────────────────────────────────
    async def _v_mastodon(self, c, k):
        instance = self.config.get("keys", {}).get("mastodon_instance_url", "mastodon.social")
        if "urn:ietf" in instance:          # placeholder value
            instance = "mastodon.social"
        try:
            r = await c.get(
                f"https://{instance}/api/v1/accounts/verify_credentials",
                headers={"Authorization": f"Bearer {k}"},
            )
            return r.status_code == 200
        except Exception:
            return False

    # ── FREE (no key) ─────────────────────────────────────────────────────────
    async def _v_hackernews(self, c, _):
        try:
            r = await c.get("https://hacker-news.firebaseio.com/v0/topstories.json")
            return r.status_code == 200
        except Exception:
            return False

    async def _v_yahoo_finance(self, c, _):
        try:
            r = await c.get("https://query1.finance.yahoo.com/v8/finance/chart/AAPL")
            return r.status_code == 200
        except Exception:
            return False

    async def _v_reddit(self, c, _):
        """Reddit public JSON – no API key needed."""
        try:
            r = await c.get(
                "https://www.reddit.com/r/technology/hot.json",
                headers={"User-Agent": "MarketScoutBot/1.0"},
                params={"limit": 1},
            )
            return r.status_code == 200
        except Exception:
            return False

    async def _v_npm(self, c, _):
        try:
            r = await c.get("https://registry.npmjs.org/react")
            return r.status_code == 200
        except Exception:
            return False

    async def _v_pypi(self, c, _):
        try:
            r = await c.get("https://pypi.org/pypi/requests/json")
            return r.status_code == 200
        except Exception:
            return False

    async def _v_stackoverflow(self, c, _):
        try:
            r = await c.get(
                "https://api.stackexchange.com/2.3/questions",
                params={"site": "stackoverflow", "pagesize": 1},
            )
            return r.status_code == 200
        except Exception:
            return False

    async def _v_coingecko(self, c, _):
        try:
            r = await c.get("https://api.coingecko.com/api/v3/ping")
            return r.status_code == 200
        except Exception:
            return False

    # ── Supabase ───────────────────────────────────────────────────────────────
    async def _v_supabase(self, db_cfg: Dict):
        url = db_cfg.get("supabase_url", "")
        key = db_cfg.get("supabase_service_key") or db_cfg.get("supabase_key", "")
        if not (url and key):
            return
        try:
            async with httpx.AsyncClient(timeout=8) as c:
                r = await c.get(
                    f"{url}/rest/v1/documents",
                    headers={
                        "apikey": key,
                        "Authorization": f"Bearer {key}",
                    },
                    params={"limit": 1},
                )
                ok = r.status_code in (200, 206)
                self.validation_results["supabase"] = ok
                logger.info("%s supabase_rest", "✅" if ok else "❌")
        except Exception as e:
            self.validation_results["supabase"] = False
            logger.warning("❌ supabase_rest: %s", e)

    # ── Helpers ────────────────────────────────────────────────────────────────
    def get_valid_keys(self)   -> List[str]:
        return [k for k, v in self.validation_results.items() if v]

    def get_invalid_keys(self) -> List[str]:
        return [k for k, v in self.validation_results.items() if not v]

    def get_free_services(self) -> List[str]:
        free = {"hackernews", "yahoo_finance", "reddit", "npm_registry", "pypi", "stackoverflow", "coingecko"}
        return [s for s in free if self.validation_results.get(s)]