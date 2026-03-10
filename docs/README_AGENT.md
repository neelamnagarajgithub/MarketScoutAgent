# Market Intelligence Agent

A comprehensive LangChain-powered agent that uses Gemini 2.5 Flash to gather market intelligence from 20+ data sources.

## 🚀 Features

- **AI-Powered Analysis**: Uses Google's Gemini 2.5 Flash for intelligent data analysis
- **20+ Data Sources**: Aggregates from News APIs, GitHub, financial markets, community sources, and more
- **Real-time Intelligence**: Fetches latest market trends, company news, and product launches
- **Structured Output**: Returns comprehensive JSON reports with insights and recommendations

## 📡 Data Sources

### Search & Discovery
- SerpAPI (Google Search)
- Bing Search API  
- Google Custom Search

### News & Market Intelligence
- NewsAPI
- GNews
- Currents API
- RSS Feeds (OpenAI, GitHub, Stripe, etc.)

### Tech/Product Intelligence  
- GitHub API (organizations, repositories)
- npm registry
- PyPI registry

### Business Intelligence
- Crunchbase API (company data)
- BuiltWith API (tech stacks)

### Community Intelligence
- Hacker News API
- Reddit API
- Product Hunt API

### Financial Intelligence
- Alpha Vantage (company overviews, news)
- Polygon.io (financial data)

## 🛠️ Setup

### 1. Install Dependencies

```bash
cd /home/naagaraj/marketscoutagent/market-aggregator
pip install -r requirements.txt
```

### 2. Configure API Keys

**Step 1: Set Gemini API Key**
```bash
export GOOGLE_API_KEY="your_gemini_api_key_here"
```

**Step 2: Update config.yaml**
Edit `config.yaml` and fill in your API keys:

```yaml
keys:
  # Search & Discovery APIs
  serpapi: "your_serpapi_key"
  newsapi: "your_newsapi_key" 
  gnews: "your_gnews_key"
  currents: "your_currents_key"
  
  # Tech/Product APIs  
  github: "your_github_token"
  
  # Financial APIs
  alpha_vantage: "your_alpha_vantage_key"
  polygon: "your_polygon_key"
  
  # Social/Community APIs
  reddit_client_id: "your_reddit_client_id"
  reddit_client_secret: "your_reddit_secret"
```

### 3. Setup Database (PostgreSQL)

```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb marketdb
sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE marketdb TO postgres;"
```

## 🎯 Usage

### Quick Test
```bash
# Test data sources
python test_agent.py

# Test full agent
python test_agent.py agent
```

### Run Agent

**1. Simple Market Scan**
```bash
python run_agent.py scan
```

**2. Company Analysis**  
```bash
python run_agent.py company "OpenAI"
```

**3. Market Trend Analysis**
```bash
python run_agent.py trend "AI automation"
```

### Python API

```python
import asyncio
from app.agent import MarketIntelligenceAgent

async def main():
    # Initialize agent
    agent = MarketIntelligenceAgent()
    
    # Comprehensive intelligence gathering
    result = await agent.comprehensive_intelligence_gathering(
        "AI startups and product launches in 2024"
    )
    
    print(json.dumps(result, indent=2))

# Run
asyncio.run(main())
```

## 📊 Output Format

The agent returns a comprehensive JSON response:

```json
{
  "summary": "Brief summary of findings",
  "timestamp": "2024-01-01T12:00:00Z",
  "query": "Original search query", 
  "sources": {
    "search_discovery": {
      "serpapi": [...],
      "bing": [...],
      "google_custom": [...]
    },
    "news_intelligence": {
      "newsapi": [...],
      "gnews": [...],
      "currents": [...]  
    },
    "tech_product": {
      "github": {...},
      "npm": {...},
      "pypi": {...}
    },
    "community": {
      "hackernews": {...},
      "reddit": {...}
    },
    "financial": {
      "alpha_vantage": {...}
    },
    "rss_feeds": {...}
  },
  "key_insights": [
    "insight 1",
    "insight 2"
  ],
  "recommendations": [
    "recommendation 1", 
    "recommendation 2"
  ]
}
```

## 🔧 Configuration

### Rate Limiting
```yaml
fetch:
  concurrency: 8           # Concurrent requests
  rate_limit_per_sec: 5    # Requests per second
```

### Database
```yaml
database:
  url: "postgresql+asyncpg://user:pass@localhost:5432/marketdb"
```

### Custom Sources
```yaml
sources:
  rss_feeds:
    - "https://blog.example.com/feed"
  
  github_orgs:
    - "your-org"
    
  subreddits:
    - "your-subreddit"
```

## 📋 API Keys Required

### Essential (for basic functionality)
- **GOOGLE_API_KEY**: Gemini 2.5 Flash (required)
- **serpapi**: SerpAPI for search (recommended)
- **newsapi**: NewsAPI for news (recommended)

### Optional (for enhanced features)
- **gnews**: GNews API
- **currents**: Currents API  
- **github**: GitHub personal access token
- **alpha_vantage**: Alpha Vantage financial data
- **polygon**: Polygon.io financial data
- **reddit_client_id/secret**: Reddit API

## 🚨 Troubleshooting  

### Common Issues

**1. "GOOGLE_API_KEY not found"**
```bash
export GOOGLE_API_KEY="your_actual_key"
```

**2. "Database connection failed"** 
- Check PostgreSQL is running
- Verify database URL in config.yaml
- Ensure database exists

**3. "API rate limit exceeded"**
- Reduce rate_limit_per_sec in config.yaml
- Add delays between requests
- Check API usage limits

**4. "Module not found"**
```bash
pip install -r requirements.txt
```

### Debugging
```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Test individual data sources  
python test_agent.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add new data source fetchers in `app/fetchers/`
4. Update configuration in `config.yaml`
5. Add tests and documentation
6. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

---

**Built with ❤️ using LangChain, Gemini 2.5 Flash, and 20+ market intelligence APIs**