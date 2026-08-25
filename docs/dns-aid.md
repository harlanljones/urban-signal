# DNS for AI Discovery (DNS-AID) records

The isitagentready audit checks DNS-based agent discovery (draft
[draft-mozleywilliams-dnsop-dnsaid](https://datatracker.ietf.org/doc/draft-mozleywilliams-dnsop-dnsaid/))
via DNS-over-HTTPS. These records live in the `harlanljones.com` zone — they
cannot be published from this repository. Apply them in Cloudflare DNS
(**DNS → Records**), then enable **DNS → Settings → Enable DNSSEC** on the zone
so validating resolvers return authenticated data (the draft requires signed
public discovery zones).

Both agent endpoints are already live:

- Product site MCP server: `https://urban-signal.harlanljones.com/mcp`
- Capability manifest: `https://urban-signal.harlanljones.com/.well-known/ai-catalog.json`

## Records

Experimental DNS-AID parameters must use numeric `keyNNNNN` SvcParamKey names
until IANA registration, per the draft.

```dns
; Discovery index — points at the ARD capability manifest
_index._agents.urban-signal.harlanljones.com. 3600 IN HTTPS 1 urban-signal.harlanljones.com. alpn="ard" port=443 mandatory=alpn,port key65280="url=/.well-known/ai-catalog.json"

; MCP transport — product site knowledge tools
_mcp._agents.urban-signal.harlanljones.com. 3600 IN HTTPS 1 urban-signal.harlanljones.com. alpn="mcp" port=443 mandatory=alpn,port key65281="endpoint=/mcp"

; Cross-reference: dashboard edge data API (its own surface lives at us-dash)
_a2a._agents.urban-signal.harlanljones.com. 3600 IN HTTPS 1 us-dash.harlanljones.com. alpn="https" port=443 mandatory=alpn,port key65282="url=https://us-dash.harlanljones.com/.well-known/api-catalog"
```

Notes:

- Use `HTTPS` (RFC 9460 SVCB-compatible) record type because every advertised
  endpoint is HTTPS; `SVCB 0 . alpn=...` alias-form records are not needed here.
- `alpn` carries the DNS-AID service tag (`mcp`, `ard`); the endpoint path rides
  in an experimental `keyNNNNN` parameter.
- If the scanner queries only apex-zone names, these can also be added under the
  registrant domain (`_index._agents.harlanljones.com`) pointing at the same
  targets — the `_agents` label convention is what matters.

## Verify after publishing

```bash
# Cloudflare DoH (the scanner's default resolver)
curl -s 'https://cloudflare-dns.com/dns-query?name=_mcp._agents.urban-signal.harlanljones.com&type=HTTPS' \
  -H 'accept: application/dns-json' | jq .

# DNSSEC: the AD flag should be set through a validating resolver
curl -s 'https://cloudflare-dns.com/dns-query?name=_index._agents.urban-signal.harlanljones.com&type=HTTPS&do=1' \
  -H 'accept: application/dns-json' | jq '{AD: .AD}'
```

Then re-run the scan:

```bash
curl -s https://isitagentready.com/api/scan -H 'content-type: application/json' \
  -d '{"url":"https://urban-signal.harlanljones.com"}' | jq '.checks.discoverability.dnsAid'
```
