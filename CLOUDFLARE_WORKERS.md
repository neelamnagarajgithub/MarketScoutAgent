# Cloudflare Workers Setup Guide

## What is this?

This is an **API Gateway** that runs on Cloudflare's edge network. It:
- ✅ Routes requests to your Render backend
- ✅ Handles CORS and rate limiting
- ✅ Caches API responses for speed
- ✅ Provides health monitoring
- ✅ Low latency (runs on 250+ data centers globally)

---

## Prerequisites

1. **Cloudflare Account** at [dash.cloudflare.com](https://dash.cloudflare.com)
2. **Node.js 18+** installed
3. **Render backend running** (from previous setup)

---

## Step 1: Install Dependencies

```bash
npm install -g wrangler
cd /path/to/market-aggregator
npm install --save-dev @cloudflare/workers-types wrangler typescript
```

---

## Step 2: Create Cloudflare Worker

```bash
# Authenticate with Cloudflare
wrangler login

# List your accounts
wrangler whoami
```

---

## Step 3: Configure wrangler.toml

Edit `wrangler.toml` and update:

```toml
# Replace with your actual zone ID (from Cloudflare Dashboard)
[env.production]
zone_id = "your-cloudflare-zone-id"

[env.production.kv_namespaces]
binding = "CACHE"
id = "prod-kv-id"  # Create KV namespace in Cloudflare dashboard
```

---

## Step 4: Set Environment Variables

Add your Render backend URL to Cloudflare:

```bash
# For staging
wrangler secret put BACKEND_URL --env staging
# Enter: https://market-scout-api-staging.onrender.com

# For production
wrangler secret put BACKEND_URL --env production
# Enter: https://market-scout-api-prod.onrender.com
```

Or set in `wrangler.toml`:
```toml
[env.production]
vars = { BACKEND_URL = "https://market-scout-api-prod.onrender.com" }

[env.staging]
vars = { BACKEND_URL = "https://market-scout-api-staging.onrender.com" }
```

---

## Step 5: Deploy Worker

```bash
# Deploy to staging
wrangler deploy --env staging

# Deploy to production
wrangler deploy --env production

# Or just deploy (uses default env)
wrangler deploy
```

---

## Step 6: Test Deployment

```bash
# Get your worker URL (from deployment output)
WORKER_URL="https://market-scout-api-gateway.your-account.workers.dev"

# Test health endpoint
curl $WORKER_URL/health

# Make API call
curl -X POST $WORKER_URL/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "market trends"}'
```

---

## Step 7: Domain Setup (Optional)

To use your own domain:

1. Go to **Cloudflare Dashboard → Workers → Details**
2. Click **Add Custom Domain**
3. Enter: `api.yourdomai.com`
4. Save

Now your worker is accessible at `https://api.yourdomain.com`

---

## Features

### 🚀 Performance
- **Global edge network** - Ultra-low latency
- **Response caching** - Automatic 1-hour cache
- **Compression** - Gzip by default

### 🛡️ Security
- **Rate limiting** - 100 req/min per IP
- **CORS handling** - Safe cross-origin requests
- **DDoS protection** - Built-in (Cloudflare)

### 📊 Monitoring
- **Logs** - View in Cloudflare dashboard
- **Health checks** - Cron job every 6 hours
- **Analytics** - Request metrics

---

## Development

```bash
# Local development server
wrangler dev

# Visit: http://localhost:8787
# It proxies to your Render backend

# Watch for changes
wrangler dev --watch
```

---

## Deploy Command Reference

```bash
# Deploy to staging
npm run deploy:staging

# Deploy to production
npm run deploy:prod

# Development
npm run dev

# Format code
npm run format
```

---

## Monitoring & Logs

```bash
# View live logs
wrangler tail --env production

# View recent logs
wrangler logs --env production

# Or use Cloudflare Dashboard → Workers → Details → Logs
```

---

## Troubleshooting

### "BACKEND_URL not set"
```bash
wrangler secret put BACKEND_URL --env production
# Enter your Render URL
```

### "Worker timeout"
- Increase `timeout` in wrangler.toml
- Check Render backend is running: `curl https://your-render-service/health`

### "CORS error"
- Check `corsHeaders` in `src/index.ts`
- Update origin if needed

### "Cache not working"
- Ensure KV namespace is created in Cloudflare
- Check cache key in logs

---

## Pricing

| Item | Cost |
|------|------|
| Workers | $0.50/M requests (free tier: 100k/day) |
| KV Storage | Free tier: 100k operations/day |
| Custom domains | Included (with Cloudflare domain) |

---

## Architecture

```
User Request
    ↓
Cloudflare Workers (Edge) ← Rate limiting, caching, CORS
    ↓
Render Backend (FastAPI)
    ↓
Database (Supabase)
```

---

## Next Steps

1. ✅ Deploy worker: `npm run deploy:staging`
2. ✅ Get worker URL from output
3. ✅ Test: `curl $WORKER_URL/health`
4. ✅ Setup custom domain (optional)
5. ✅ Monitor in Cloudflare dashboard
6. ✅ Deploy to production when ready

---

## File Structure

```
market-aggregator/
├── wrangler.toml          # Worker config
├── src/
│   └── index.ts           # Worker code
├── package-workers.json   # Dependencies
└── CLOUDFLARE_WORKERS.md  # This file
```

---

## Quick Redeploy

```bash
# After making changes
git add src/
npm run deploy:prod
```
