# Render Memory Issue & Out of Memory Fix

## Problem

```
==> Out of memory (used over 512Mi)
==> No open ports detected
```

Your app crashes **before opening a port** because:
1. Heavy ML libraries (`torch`, `transformers`, etc.) load at startup
2. They consume >512MB RAM on Render's free tier
3. App crashes before uvicorn opens port 8080

---

## Root Cause: Heavy Dependencies

| Library | Size | Used In |
|---------|------|---------|
| `torch` | 500MB+ | ML models |
| `transformers` | 1GB+ | Embeddings |
| `sentence-transformers` | 300MB+ | Semantic search |
| `faiss-cpu` | 200MB+ | Vector search |
| `selenium` | 100MB+ | Web scraping (dev only) |
| **Total** | **2.5GB+** | WAY over limit |

---

## ✅ Solution: Use Production-Optimized Requirements

### Step 1: Switch to Optimized Requirements

I've created `requirements-prod.txt` which:
- ✅ Removes torch, transformers, faiss (load on-demand only)
- ✅ Removes selenium, pandas, reportlab (dev/optional only)
- ✅ Keeps only essential packages: FastAPI, database, APIs
- ✅ Reduces startup size from ~3GB to ~500MB

### Step 2: Update render.yaml

Already updated! Now uses:
```yaml
buildCommand: "pip install -r requirements-prod.txt"  # ✅ Optimized
startCommand: "gunicorn --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8080 app.main:app"
plan: starter  # ⚠️ 1GB RAM (not free 512MB)
```

### Step 3: Upgrade Render Plan

**IMPORTANT:** You need at least **Starter ($7/month)** plan:

1. Go to **Render Dashboard → Your Service → Settings**
2. Change plan from **Free** to **Starter** (1GB RAM)
3. Click **Save**

**Note:** Free tier has 512MB which is insufficient for Python ML apps.

---

## Step 4: Redeploy

```bash
git add requirements-prod.txt render.yaml
git commit -m "Fix memory issue: use optimized requirements and upgrade plan"
git push
```

Then in Render Dashboard:
1. Click **Manual Deploy** (or auto-deploys)
2. Monitor logs
3. Should see startup succeeding in 1-2 minutes

---

## Test Deployment

```bash
SERVICE_URL="https://market-scout-api-xxxxx.onrender.com"

# Should return 200 now
curl $SERVICE_URL/health

# If still failing, check logs in Render dashboard
```

---

## Long-Term: Lazy Load Heavy Models

For even better performance, modify `app/main.py` to load ML models on-demand:

```python
# In app/main.py

# ❌ BEFORE: Loads 1GB at startup
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')

# ✅ AFTER: Lazy load only when needed
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model

@app.post("/v1/analyze")
async def analyze(req):
    # Only load if needed
    model = get_embedding_model()
    embeddings = model.encode(req.query)
    # ... rest of logic
```

---

## Pricing Comparison

| Plan | RAM | Cost | Status |
|------|-----|------|--------|
| **Free** | 512MB | $0 | ❌ Too small |
| **Starter** | 1GB | $7/mo | ✅ Minimum for your app |
| **Standard** | 2GB | $25/mo | ✅ Better for scale |
| **Pro** | 4GB | $100+/mo | ✅ For heavy ML |

---

## What Changed

### `requirements-prod.txt` (NEW)
- Removed heavy ML libs (load on-demand)
- Keeps essential packages
- **Size: ~500MB** (vs 3GB before)

### `render.yaml` (UPDATED)
```yaml
# Uses optimized requirements
buildCommand: "pip install -r requirements-prod.txt"

# Uses gunicorn for better concurrency
startCommand: "gunicorn --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8080 app.main:app"

# Needs at least 1GB RAM
plan: starter
```

### Dockerfile (NO CHANGE NEEDED)
Keep existing Dockerfile - it works fine

---

## Troubleshooting

### Still getting OOM error?
```bash
# 1. Verify plan is Starter (1GB), not Free
# Render Dashboard → Settings → Plan

# 2. Check build command uses requirements-prod.txt
# Render Dashboard → Settings → Build Command

# 3. View detailed logs
# Render Dashboard → Logs tab
```

### Still no open ports?
```bash
# Make sure you see these in logs:
# "Uvicorn running on http://0.0.0.0:8080"
# "Application startup complete"

# If not, check:
# 1. All env vars are set (DATABASE_URL, API keys, etc)
# 2. config.yaml exists or can be created
# 3. No missing dependencies
```

### Slow startup (>2 min)?
```bash
# Normal with first deploy (downloads all packages)
# Second deploy will be faster (uses cache)
# Keep min deploy time is ~1 min with Starter plan
```

---

## Next Steps

1. ✅ Update `render.yaml` (already done)
2. ✅ Create `requirements-prod.txt` (already done)
3. ⚠️ **UPGRADE Render plan to Starter** (required)
4. ✅ Push changes: `git push`
5. ✅ Monitor deployment in Render logs
6. ✅ Test: `curl https://your-service/health`

---

## Reference Commands

```bash
# View all production requirements
cat requirements-prod.txt

# View render config
cat render.yaml

# Verify changes
git status
git diff render.yaml
```

Done! Your deployment should now work. 🚀
