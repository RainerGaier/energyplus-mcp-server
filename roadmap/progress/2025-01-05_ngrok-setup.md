# ngrok Tunnel Setup for n8n Integration

**Date:** 2025-01-05

**Purpose:** Expose local HTTP API to cloud-hosted n8n instance

---

## Prerequisites

1. HTTP server running on localhost:8000
2. ngrok installed and authenticated

---

## Quick Start

### 1. Start the HTTP Server

```bash
cd c:\Users\gaierr\Energy_Projects\projects\EnergyPlus-MCP\energyplus-mcp-server
python -m energyplus_mcp_server.http_server
```

### 2. Start ngrok Tunnel (in a new terminal)

```bash
ngrok http 8000
```

### 3. Get the Public URL

The URL will be displayed in the ngrok terminal, e.g.:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

Or query programmatically:
```bash
curl -s http://127.0.0.1:4040/api/tunnels | python -c "import sys,json; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'])"
```

---

## ngrok Commands Reference

| Command | Description |
|---------|-------------|
| `ngrok http 8000` | Start tunnel to port 8000 |
| `ngrok update` | Update ngrok to latest version |
| `ngrok version` | Check installed version |
| `ngrok config check` | Verify configuration |

---

## n8n Endpoint Mapping

Replace `localhost:8000` with your ngrok URL:

| Local | ngrok (example) |
|-------|-----------------|
| `http://localhost:8000/health` | `https://abc123.ngrok-free.app/health` |
| `http://localhost:8000/docs` | `https://abc123.ngrok-free.app/docs` |
| `http://localhost:8000/api/weather/fetch` | `https://abc123.ngrok-free.app/api/weather/fetch` |
| `http://localhost:8000/api/templates` | `https://abc123.ngrok-free.app/api/templates` |
| `http://localhost:8000/api/models/generate` | `https://abc123.ngrok-free.app/api/models/generate` |
| `http://localhost:8000/api/simulation/run` | `https://abc123.ngrok-free.app/api/simulation/run` |

---

## ngrok Dashboard

While ngrok is running, view request logs at:
- **Local Dashboard:** http://127.0.0.1:4040
- **Online Dashboard:** https://dashboard.ngrok.com

---

## Notes

- Free tier URLs change each time ngrok restarts
- Keep both terminals running (HTTP server + ngrok) during testing
- ngrok free tier has rate limits (~40 requests/minute)
- For production, consider paid ngrok plan or cloud deployment

---

## Troubleshooting

### ngrok version too old
```bash
ngrok update
```

### Check if server is running
```bash
curl http://localhost:8000/health
```

### Check tunnel status
```bash
curl http://127.0.0.1:4040/api/tunnels
```
