## Environment

```Bash
cd c:\Users/gaierr/Energy_Projects/projects/EnergyPlus-MCP/energyplus-mcp-server
.venv/bin/activate
```

## Quick Start

### 1. Start the HTTP Server

```bash
python -m energyplus_mcp_server.http_server
```

### 2. Start ngrok Tunnel (in a new terminal)

```bash
ngrok http 8000
```

### 3. Get the Public URL

The URL will be displayed in the ngrok terminal, e.g.:

---

Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000

### 4. Update the file

```bash
https://docs.google.com/spreadsheets/d/1XdLm6f9EY_AK6a6M4zH2Md4TzE3bSvTH-mXD6vL0KpE/edit?gid=0#gid=0
```

---

## Looking for Tasks

```Bash
netstat -ano | grep 8000 || echo "No process on port 8000"
```

## Killing a task

taskkill /PID 55864 /F

### Direcotry change (CMD)

```bash
cd c:\Users\gaierr\Energy_Projects\projects\EnergyPlus-MCP\energyplus-mcp-server
```