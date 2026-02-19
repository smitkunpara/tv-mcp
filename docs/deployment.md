# Deployment Guide

## Vercel

Deploy the FastAPI server to Vercel for a publicly accessible API.

**Entrypoint:** `vercel/app.py`

### Required Environment Variables

Set these in your Vercel project settings:

| Variable | Description |
|---|---|
| `TRADINGVIEW_COOKIE` | TradingView session cookie |
| `TV_ADMIN_KEY` | Admin API key (keep secret) |
| `TV_CLIENT_KEY` | Client API key |
| `VERCEL_URL` | Your deployment URL (e.g. `https://your-app.vercel.app/`) |

### Deploying

```bash
vercel --prod
```

The `vercel.json` at the project root configures the build.

---

## ChatGPT / Custom GPT

Connect a custom GPT to the deployed HTTP API.

1. Deploy to Vercel and note your deployment URL.
2. In the GPT builder, choose **Actions → Create new action**.
3. Import the spec from `<your-vercel-url>/openapi.json`.
4. Set authentication:
   - Type: **Custom**
   - Custom header: `X-Client-Key`
   - Value: your `TV_CLIENT_KEY`
5. Re-import the spec after each new deployment if the URL changes.

---

## Cookie Updater Extension

The Chrome extension in `cookie_updater_extension/` can push updated cookies to a running server automatically.

See [cookie_updater_extension/README.md](../cookie_updater_extension/README.md) for installation and usage.
