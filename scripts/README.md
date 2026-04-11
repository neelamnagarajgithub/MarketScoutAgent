# Scripts Directory

Helper scripts for deployment and configuration management.

## Scripts

### `upload-secrets.sh`

Bulk upload all secrets to Cloudflare Workers from a `.secrets.json` file.

**Usage:**

```bash
chmod +x scripts/upload-secrets.sh
./scripts/upload-secrets.sh production
```

**Prerequisites:**
- `jq` installed (JSON processor)
- `wrangler` CLI installed
- `wrangler login` already authenticated
- `.secrets.json` file created with your secrets

**What it does:**
1. Reads all key-value pairs from `.secrets.json`
2. Uploads each one as a Cloudflare Worker secret
3. Shows success/failure for each upload
4. Displays verification commands

**Example `.secrets.json`:**

```json
{
  "SUPABASE_URL": "https://your-project.supabase.co",
  "SUPABASE_KEY": "your-key",
  "DATABASE_URL": "postgresql://...",
  "SERPAPI": "your-api-key"
}
```

See `.secrets.example.json` for a complete template.

---

## Environment-Specific Deployment

### Staging

```bash
# Set up staging secrets
./scripts/upload-secrets.sh staging

# Deploy to staging
wrangler deploy --env staging

# Test staging
curl https://market-scout-api-staging.workers.dev/health
```

### Production

```bash
# Set up production secrets
./scripts/upload-secrets.sh production

# Deploy to production
wrangler deploy --env production

# Verify deployment
curl https://market-scout-api.workers.dev/health
wrangler tail --env production
```

---

## Troubleshooting

### "command not found: jq"

Install JSON processor:
```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# Windows (WSL)
sudo apt-get install jq
```

### "wrangler command not found"

Install Cloudflare Workers CLI:
```bash
npm install -g wrangler
wrangler login
```

### "Authentication failed"

Re-authenticate with Cloudflare:
```bash
wrangler logout
wrangler login
```

### Script permissions

Make the script executable:
```bash
chmod +x scripts/upload-secrets.sh
```

---

## Best Practices

✅ **DO:**
- Keep `.secrets.json` private - add to `.gitignore`
- Use separate secrets for staging and production
- Rotate API keys regularly
- Use `wrangler secret list` to verify uploads
- Test with `wrangler dev` before deploying

❌ **DON'T:**
- Commit `.secrets.json` to git
- Share `.secrets.json` with others
- Store plaintext secrets in code
- Reuse staging secrets in production
- Share Cloudflare authentication tokens

---

## Additional Deployment Commands

```bash
# Local development with wrangler
wrangler dev

# View live logs
wrangler tail --env production

# List all uploaded secrets (names only, not values)
wrangler secret list --env production

# Delete a secret
wrangler secret delete SECRET_NAME --env production

# Check deployment history
wrangler deployments list
```

For more information, see [CLOUDFLARE_SECRETS_SETUP.md](../CLOUDFLARE_SECRETS_SETUP.md)
