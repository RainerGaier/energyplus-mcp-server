# Google Sheets for ngrok URL Configuration

**Date:** 2025-01-06

**Purpose:** Use Google Sheets as a static endpoint for storing the ngrok URL, solving the chicken-and-egg problem where cloud n8n can't reach localhost to get the URL.

---

## Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Local Machine  │     │  Google Sheets  │     │   Cloud n8n     │
│                 │     │                 │     │                 │
│  ngrok starts   │────>│  ngrok_url      │<────│  Read URL       │
│  script updates │     │  (static URL)   │     │  at workflow    │
│                 │     │                 │     │  start          │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Step 1: Create Google Sheet

1. Go to https://sheets.google.com
2. Create a new spreadsheet named `EnergyPlus-MCP-Config`
3. In cell **A1**, enter: `ngrok_url`
4. In cell **B1**, enter your current ngrok URL (e.g., `https://abc123.ngrok-free.app`)
5. Optionally in **A2**: `last_updated`, **B2**: current timestamp

### Sheet Layout

| A            | B                             |
| ------------ | ----------------------------- |
| ngrok_url    | https://abc123.ngrok-free.app |
| last_updated | 2025-01-06T15:30:00           |

---

## Step 2: Share Sheet (for script access)

### Option A: Public Read Access (Simplest)

1. Click **Share** button
2. Under "General access", change to **Anyone with the link**
3. Set permission to **Viewer**
4. Copy the sharing link {https://docs.google.com/spreadsheets/d/1XdLm6f9EY_AK6a6M4zH2Md4TzE3bSvTH-mXD6vL0KpE/edit?usp=sharing}

### Option B: Service Account (More Secure)

1. Create a Google Cloud project
2. Enable Google Sheets API
3. Create a service account
4. Download JSON credentials
5. Share the sheet with the service account email

---

## Step 3: Get Sheet ID

From your sheet URL:

```
https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit
```

Copy the `SHEET_ID_HERE` portion.

---

## Step 4: n8n Workflow Configuration

### Node 1: Get ngrok URL from Google Sheets

**For Public Sheets (Option A):**

- **Node Type:** HTTP Request
- **Name:** Get ngrok URL
- **Method:** GET
- **URL:**

```
https://sheets.googleapis.com/v4/spreadsheets/YOUR_SHEET_ID/values/B1?key=YOUR_API_KEY
```

**Alternative - Direct CSV Export:**

```
https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/export?format=csv&range=B1
```

**For n8n Google Sheets Node:**

- **Node Type:** Google Sheets
- **Operation:** Read Rows
- **Document:** Select your spreadsheet
- **Sheet:** Sheet1
- **Range:** B1

### Node 2: Set Config

- **Node Type:** Set
- **Name:** Config

| Field        | Value                                           |
| ------------ | ----------------------------------------------- |
| API_BASE_URL | `{{ $json.values[0][0] }}` (HTTP Request)       |
|              | or `{{ $json.ngrok_url }}` (Google Sheets node) |

### Remaining Nodes

Continue with Health Check, etc., referencing:

```javascript
{{ $('Config').item.json.API_BASE_URL }}/health
```

---

## Step 5: Local Script to Update Sheet

See `scripts/update_ngrok_url.py` for automatic updates when ngrok starts.

### Manual Update via curl

```bash
# Get current ngrok URL
NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | python -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])")

echo "ngrok URL: $NGROK_URL"

# Update Google Sheet (requires API key with write access or service account)
# See script for full implementation
```

---

## Complete n8n Workflow Structure

```
Manual Trigger
    ↓
Google Sheets (Read ngrok_url)
    ↓
Set Config (API_BASE_URL = ngrok_url)
    ↓
Health Check → IF → [continue or error]
    ↓
Fetch Weather → IF → [continue or error]
    ↓
Generate Model → IF → [continue or error]
    ↓
Run Simulation → IF → [continue or error]
    ↓
Get Results Summary
```

---

## Troubleshooting

### "API key not valid"

- Ensure you've enabled the Google Sheets API in Cloud Console
- Check the API key restrictions

### "Sheet not found"

- Verify the Sheet ID is correct
- Check sharing permissions

### "Referenced node doesn't exist"

- Ensure the Google Sheets node is named exactly as referenced
- Use `$json` for immediate previous node

---

## Alternative: Direct CSV URL

If the sheet is public, you can use a simpler approach:

```
https://docs.google.com/spreadsheets/d/SHEET_ID/gviz/tq?tqx=out:csv&range=B1
```

This returns just the cell value as plain text.

In n8n:

1. HTTP Request to above URL
2. The response body is just the URL string
3. Use in Set node: `{{ $json }}`