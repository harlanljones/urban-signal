# Urban Signal Webhook Receiver (`apps/webhook`)

Cloudflare Worker serving as the ingestion receiver for real-time catalyst alerts and feed staleness monitoring notifications.

---

## Route & Deployment

- **Production Domain:** `hooks.harlanljones.com`
- **Platform:** Cloudflare Workers

---

## Development

```bash
# Start local development server
bun run dev

# Deploy to Cloudflare Workers
bun run deploy
```
