"""
Configuration loader that supports both local YAML files and environment variables/secrets.
This enables seamless deployment on Cloudflare Workers, Render, and local development.
"""

import os
import json
import yaml
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Try to load from .env file (for local development)
try:
    from dotenv import load_dotenv
    # Load .env file if it exists
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass


class ConfigLoader:
    """
    Loads configuration from multiple sources with fallback:
    1. Individual environment variables (SERPAPI_KEY, etc.)
    2. JSON-encoded CONFIG environment variable
    3. Local config.yaml file (for development)
    
    Priority: Environment variables > JSON config > YAML file
    """

    @staticmethod
    def load(config_path: str = "config.yaml") -> Dict[str, Any]:
        """
        Load configuration from environment or file.
        
        Args:
            config_path: Path to config.yaml (used as fallback)
            
        Returns:
            Dictionary with full configuration
        """
        config = {}
        
        # Try to load from environment variables first
        env_config = ConfigLoader._load_from_env()
        if env_config:
            config.update(env_config)
            logger.info("✓ Loaded configuration from environment variables")
        
        # Try to load from JSON environment variable
        json_config = ConfigLoader._load_from_json_env()
        if json_config:
            config.update(json_config)
            logger.info("✓ Loaded configuration from JSON_CONFIG environment variable")
        
        # Fall back to YAML file if available
        if os.path.exists(config_path) and not env_config and not json_config:
            try:
                with open(config_path, "r") as fh:
                    file_config = yaml.safe_load(fh)
                    if file_config:
                        config.update(file_config)
                        logger.info(f"✓ Loaded configuration from {config_path}")
            except Exception as e:
                logger.warning(f"Could not load {config_path}: {e}")
        
        # Fill any missing sections with defaults
        config = ConfigLoader._apply_defaults(config)
        
        return config

    @staticmethod
    def _load_from_env() -> Optional[Dict[str, Any]]:
        """
        Load configuration from individual environment variables.
        Looks for: DATABASE_URL, SERPAPI_KEY, NEWSAPI_KEY, etc.
        """
        config = {}
        has_env_vars = False
        
        # Database configuration
        if os.getenv("DATABASE_URL") or os.getenv("SUPABASE_URL"):
            config["database"] = {
                "provider": os.getenv("DATABASE_PROVIDER", "supabase"),
                "supabase_url": os.getenv("SUPABASE_URL", ""),
                "supabase_key": os.getenv("SUPABASE_KEY", ""),
                "supabase_service_key": os.getenv("SUPABASE_SERVICE_KEY", ""),
                "url": os.getenv("DATABASE_URL", ""),
                "sqlite_path": os.getenv("SQLITE_PATH", "data/market_intelligence.db"),
            }
            has_env_vars = True
        
        # Fetch configuration
        fetch_config = {}
        if os.getenv("FETCH_CONCURRENCY"):
            fetch_config["concurrency"] = int(os.getenv("FETCH_CONCURRENCY", 8))
            has_env_vars = True
        if os.getenv("FETCH_RATE_LIMIT"):
            fetch_config["rate_limit_per_sec"] = int(os.getenv("FETCH_RATE_LIMIT", 5))
            has_env_vars = True
        if fetch_config:
            config["fetch"] = fetch_config
        
        # API Keys
        keys = {}
        api_key_names = [
            "serpapi", "serpapi_engine", "bing_search", "google_custom_search",
            "google_custom_search_id", "shodan", "newsapi", "gnews", "currents",
            "guardian", "nytimes_key", "nytimes_secret",
            "github_personal_access_token", "gitlab", "apollo", "product_hunt_secret",
            "stackoverflow", "alpha_vantage", "massive",
            "mastodon_instance_url", "mastodon_access_token",
            "companies_house", "GOOGLE_API_KEY",
        ]
        
        for key_name in api_key_names:
            env_var_name = key_name.upper()
            if os.getenv(env_var_name):
                keys[key_name] = os.getenv(env_var_name)
                has_env_vars = True
        
        if keys:
            config["keys"] = keys
        
        # Sources configuration
        sources = {}
        
        # RSS Feeds
        if os.getenv("RSS_FEEDS_JSON"):
            try:
                rss_feeds = json.loads(os.getenv("RSS_FEEDS_JSON", "[]"))
                sources["rss_feeds"] = rss_feeds
                has_env_vars = True
            except json.JSONDecodeError:
                logger.warning("Failed to parse RSS_FEEDS_JSON")
        
        # GitHub Organizations
        if os.getenv("GITHUB_ORGS_JSON"):
            try:
                github_orgs = json.loads(os.getenv("GITHUB_ORGS_JSON", "[]"))
                sources["github_orgs"] = github_orgs
                has_env_vars = True
            except json.JSONDecodeError:
                logger.warning("Failed to parse GITHUB_ORGS_JSON")
        
        # Subreddits
        if os.getenv("SUBREDDITS_JSON"):
            try:
                subreddits = json.loads(os.getenv("SUBREDDITS_JSON", "[]"))
                sources["subreddits"] = subreddits
                has_env_vars = True
            except json.JSONDecodeError:
                logger.warning("Failed to parse SUBREDDITS_JSON")
        
        # Mastodon Instances
        if os.getenv("MASTODON_INSTANCES_JSON"):
            try:
                mastodon_instances = json.loads(os.getenv("MASTODON_INSTANCES_JSON", "[]"))
                sources["mastodon_instances"] = mastodon_instances
                has_env_vars = True
            except json.JSONDecodeError:
                logger.warning("Failed to parse MASTODON_INSTANCES_JSON")
        
        # Product Hunt Categories
        if os.getenv("PRODUCT_HUNT_CATEGORIES_JSON"):
            try:
                categories = json.loads(os.getenv("PRODUCT_HUNT_CATEGORIES_JSON", "[]"))
                sources["product_hunt_categories"] = categories
                has_env_vars = True
            except json.JSONDecodeError:
                logger.warning("Failed to parse PRODUCT_HUNT_CATEGORIES_JSON")
        
        if sources:
            config["sources"] = sources
        
        return config if has_env_vars else None

    @staticmethod
    def _load_from_json_env() -> Optional[Dict[str, Any]]:
        """
        Load full configuration from JSON_CONFIG environment variable.
        This allows passing entire config as a single environment variable.
        """
        config_json = os.getenv("CONFIG")
        if not config_json:
            return None
        
        try:
            return json.loads(config_json)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse CONFIG JSON: {e}")
            return None

    @staticmethod
    def _apply_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values for missing configuration sections."""
        if "database" not in config:
            config["database"] = {
                "provider": "sqlite",
                "sqlite_path": "data/market_intelligence.db"
            }
        
        if "fetch" not in config:
            config["fetch"] = {
                "concurrency": 8,
                "rate_limit_per_sec": 5
            }
        
        if "keys" not in config:
            config["keys"] = {}
        
        if "sources" not in config:
            config["sources"] = {
                "rss_feeds": [],
                "free_apis": []
            }
        
        return config

    @staticmethod
    def get_key(config: Dict[str, Any], *names: str) -> Optional[str]:
        """
        Get an API key from config by checking multiple possible names.
        
        Args:
            config: Configuration dictionary
            *names: Possible key names to check (in order)
            
        Returns:
            The key value if found and non-empty, None otherwise
        """
        keys = config.get("keys", {})
        for name in names:
            value = keys.get(name, "") or os.getenv(name.upper(), "")
            if value and str(value).strip():
                return str(value).strip()
        return None
