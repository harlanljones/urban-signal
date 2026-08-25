# DNS for AI Discovery (DNS-AID) — records to publish

The agent-discovery surface of `apps/dashboard` (`/.well-known/*`, `/mcp`,
`/sitemap.xml`, …) is published by the worker itself. DNS-AID is different: it
lives in the zone, so it must be added at the DNS provider. This file is the
exact change; nothing in this repository needs to be edited alongside it.

## Zone

`harlanljones.com` (Cloudflare). The dashboard origin is
`us-dash.harlanljones.com`.

## Records to add

| Type | Name | Content |
| ---- | ---- | ------- |
| `HTTPS` | `_index._agents.us-dash` | `1 . alpn="https" port=443 mandatory=alpn,port` |
| `HTTPS` | `_mcp._agents.us-dash` | `1 us-dash.harlanljones.com alpn="mcp" port=443 mandatory=alpn,port` |

Fully qualified:

```dns
_index._agents.us-dash.harlanljones.com. 3600 IN HTTPS 1 . alpn="https" port=443 mandatory=alpn,port
_mcp._agents.us-dash.harlanljones.com.   3600 IN HTTPS 1 us-dash.harlanljones.com. alpn="mcp" port=443 mandatory=alpn,port
```

- `_index` advertises the HTTPS entrypoint (the dashboard and its
  well-known discovery documents).
- `_mcp` advertises the MCP Streamable HTTP endpoint served by the worker
  (`POST https://us-dash.harlanljones.com/mcp`, server card at
  `/.well-known/mcp/server-card.json`). `alpn="mcp"` follows the draft's
  convention of carrying the discovery protocol tag in SvcParamKey `alpn`.
- If additional experimental parameters are needed before IANA registration,
  use numeric `keyNNNNN` names per the draft.

## DNSSEC

Sign the public discovery zone so validating resolvers get authenticated data:
Cloudflare dashboard → **DNS → Settings → Enable DNSSEC** on
`harlanljones.com` (add the DS record at the registrar if the zone is a
subordinate). If already enabled, no action is required.

## Verify

DoH (what the scanner uses):

```sh
curl -s 'https://cloudflare-dns.com/dns-query?name=_mcp._agents.us-dash.harlanljones.com&type=HTTPS&dnssec=true' \
  -H 'accept: application/dns-json' | jq .
```

or with dig:

```sh
dig +dnssec HTTPS _index._agents.us-dash.harlanljones.com +short
```

Then rescan: `POST https://isitagentready.com/api/scan {"url":"https://us-dash.harlanljones.com"}` →
`checks.discoverability.dnsAid.status == "pass"`.

## Optional companion records (ARD §6.1)

These are reported by the scanner but never queried; add them only if you also
want DNS-based ARD discovery:

```dns
_catalog._agents.us-dash.harlanljones.com. 3600 IN TXT "url=https://us-dash.harlanljones.com/.well-known/ai-catalog.json"
```
