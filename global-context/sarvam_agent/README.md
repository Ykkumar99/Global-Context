# Connecting a Sarvam Voice Agent to Global Context

The demo UI calls Sarvam's APIs directly (Bulbul v3 TTS, Saaras v4 STT, Sarvam-105B). To run the same memory on a
**Sarvam Voice Agent** (telephony / web widget, dashboard.sarvam.ai → Voice Agents):

## 1. Expose the context API
The agent platform must reach your server over HTTPS:
```bash
python -m gcx serve --port 8000
cloudflared tunnel --url http://localhost:8000      # or: ngrok http 8000
```
(If your endpoint is behind a firewall, Sarvam's docs say to allowlist `4.213.167.70`.)

**Security:** requests that arrive through the tunnel can only reach `/sarvam/*`, and only with the secret
`GCX_TUNNEL_TOKEN` from `.env` (add `&token=` / `?token=` to both tool URLs). Every other route answers 403 from
outside, so nobody can browse the data or spend Sarvam credits through the demo endpoints. Run the tunnel with
the demo data only (`python -m gcx setup`, the default).

## 2. Create the agent
- **Instructions:** paste [`agent_prompt.md`](agent_prompt.md).
- **Voice:** Bulbul, female speaker (e.g. *priya*), language Hindi (hi-IN), code-mixed.
- **Variables:** `glid` (set per campaign contact / test call).

## 3. Add two HTTPS tools
| Tool | When it runs | Request | Save reply into variables |
|---|---|---|---|
| `load_context` | `on_start` | `GET https://<your-host>/sarvam/context?glid={{glid}}&token=<GCX_TUNNEL_TOKEN>` | `context_md` → `context`, `opening_line` → `opening`, `language` → `language` |
| `save_call` | `on_end` | `POST https://<your-host>/sarvam/call-ended?token=<GCX_TUNNEL_TOKEN>` body `{"glid": "{{glid}}", "transcript": "<Call Transcript>"}` | — |

Use the `@` variable picker for *Call Transcript* in the body. After the call, the seller's file is updated within
milliseconds and the next channel (WhatsApp, a second call) resumes from it.

## 4. Test
Start a test call with `glid = 146010610` (KPR Tempo Services). The agent should open by referring to the seller's
WhatsApp question instead of the generic pitch.

## Our deployed agent (hackathon build)

| | |
|---|---|
| Platform | Sarvam Samvaad (indus.sarvam.ai → Voice Agents) |
| Agent | **Payal - Global Context** · ID `Payal---Glo-ed092fb2-9b6f` · v1 · organisation **Vishwas's Organisation** (team credits). An earlier copy `Payal---Glo-b7f05376-3920` exists in Yatharth's Organisation and is no longer used |
| Voice | Ritu - Sales Agent (Bulbul, female, Hindi), speed 1.15, starts in Hindi, switches language with the caller |
| Input variables | `glid` (default 146010610), `context`, `opening`, `language` (fallbacks if the tool fails) |
| Greeting | `{opening}` — the personalised line from the memory file |
| Tools | `load_context` (on start, GET `/sarvam/context`, param `glid`) → saves `context_md`→`context`, `opening_line`→`opening`, `language`→`language` · `save_call` (on end, POST `/sarvam/call-ended`, body `glid`, `summary`=call_summary, `transcript`=Call transcript) |
| Auth | API key header `x-gcx-token` = workspace secret holding `GCX_TUNNEL_TOKEN` |

The free Cloudflare quick-tunnel URL changes every time `cloudflared` restarts — update the URL in both tools after
a restart (or use a named tunnel for a fixed hostname). Laptop, `python -m gcx serve` and the tunnel must stay running
while the agent is used.
