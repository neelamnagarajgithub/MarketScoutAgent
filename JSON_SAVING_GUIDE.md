# 🚀 Semantic Search with Automatic JSON Saving

Your semantic search system now **automatically saves JSON results** to local files! Here's how to use it:

## 📁 Automatic JSON File Saving

**By default, all queries now save JSON results to the `search_results/` directory with intelligent filenames.**

### File Naming Format:
```
search_results/YYYYMMDD_HHMMSS_querytype_cleanquery.json
```

Examples:
- `search_results/20260309_143022_company_analysis_NVIDIA_AI_business_strategy.json`
- `search_results/20260309_143045_market_trend_SaaS_market_trends.json`

## 🎯 Ways to Run Queries & Save JSON:

### 1. **Simple Query Runner (RECOMMENDED)**
```bash
python run_query.py "NVIDIA AI business strategy and new product announcements"
```
- ✅ Runs query
- ✅ Auto-saves JSON file  
- ✅ Shows summary
- ✅ Displays key insights

### 2. **Interactive Mode**
```bash
./run_semantic.sh interactive
# or
python semantic_cli.py
```

**Commands in interactive mode:**
- `jsonfile on/off` - Toggle JSON file saving (default: ON)
- `json on/off` - Toggle JSON output display
- `last` - Show previous result as JSON
- Just type your query and JSON is auto-saved!

### 3. **Quick Launcher**
```bash
./run_semantic.sh run "your query here"
```

### 4. **Direct JSON Query**
```bash
python json_query.py "your query here"  # Prints JSON to console
```

### 5. **Test Your NVIDIA Query**
```bash
python test_nvidia_json.py
```

## 📊 JSON Structure

Each saved JSON file contains:

```json
{
  "query": "your search query",
  "query_type": "company_analysis",
  "status": "success", 
  "timestamp": "2026-03-09T14:30:22",
  "plan": {
    "entities": [...],
    "keywords": [...],
    "sources": [...]
  },
  "summary": {
    "successful_sources": 4,
    "total_documents": 25,
    "confidence_score": 0.90
  },
  "insights": [...],
  "recommendations": [...],
  "raw_data": {
    "search_discovery": {...},
    "news_intelligence": {...},
    "github_intelligence": {...},
    "financial_intelligence": {...}
  },
  "json_file_saved": "search_results/20260309_143022_company_analysis_NVIDIA.json"
}
```

## 🎯 Quick Start:

```bash
# Run your NVIDIA query and auto-save JSON:
python run_query.py "NVIDIA AI business strategy and new product announcements"

# Check the search_results/ directory for your JSON file
ls search_results/
```

**Your JSON files are automatically organized and ready for further analysis!** 🚀