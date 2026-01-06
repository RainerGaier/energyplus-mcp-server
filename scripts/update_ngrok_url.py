#!/usr/bin/env python3
"""
Update ngrok URL in Google Sheets

This script detects the current ngrok URL and updates a Google Sheet,
allowing cloud-based n8n workflows to dynamically fetch the URL.

Usage:
    # One-time update
    python scripts/update_ngrok_url.py

    # Watch mode - updates whenever ngrok URL changes
    python scripts/update_ngrok_url.py --watch

    # With custom sheet ID
    python scripts/update_ngrok_url.py --sheet-id YOUR_SHEET_ID

Setup:
    1. Create a Google Sheet with ngrok_url in A1, URL in B1
    2. Create a service account and download credentials JSON
    3. Share the sheet with the service account email
    4. Set environment variable: GOOGLE_SHEETS_CREDENTIALS=/path/to/credentials.json
    5. Set environment variable: NGROK_CONFIG_SHEET_ID=your_sheet_id

Alternative (simpler but less secure):
    Use a public sheet and update via Apps Script web app
"""

import os
import sys
import json
import time
import argparse
import urllib.request
from datetime import datetime
from pathlib import Path

# Configuration
NGROK_API_URL = "http://127.0.0.1:4040/api/tunnels"
DEFAULT_SHEET_ID = os.environ.get("NGROK_CONFIG_SHEET_ID", "")
CREDENTIALS_PATH = os.environ.get("GOOGLE_SHEETS_CREDENTIALS", "")
CONFIG_FILE = Path(__file__).parent.parent / "config" / "ngrok_url.txt"


def get_ngrok_url() -> str | None:
    """Get the current ngrok public URL from the local API."""
    try:
        with urllib.request.urlopen(NGROK_API_URL, timeout=2) as response:
            data = json.loads(response.read().decode())
            tunnels = data.get("tunnels", [])

            # Prefer HTTPS tunnel
            for tunnel in tunnels:
                if tunnel.get("proto") == "https":
                    return tunnel["public_url"]

            # Fall back to first tunnel
            if tunnels:
                return tunnels[0]["public_url"]

            return None
    except Exception as e:
        print(f"Error getting ngrok URL: {e}")
        return None


def update_local_config(url: str) -> bool:
    """Update the local config file with the ngrok URL."""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(url)
        print(f"Updated local config: {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"Error updating local config: {e}")
        return False


def update_google_sheet_gspread(url: str, sheet_id: str) -> bool:
    """
    Update Google Sheet using gspread library.

    Requires:
        pip install gspread google-auth
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        print("gspread not installed. Run: pip install gspread google-auth")
        return False

    if not CREDENTIALS_PATH or not os.path.exists(CREDENTIALS_PATH):
        print(f"Credentials file not found: {CREDENTIALS_PATH}")
        print("Set GOOGLE_SHEETS_CREDENTIALS environment variable")
        return False

    try:
        # Authenticate
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=scopes)
        client = gspread.authorize(creds)

        # Open sheet and update
        sheet = client.open_by_key(sheet_id).sheet1
        sheet.update_acell("B1", url)
        sheet.update_acell("B2", datetime.now().isoformat())

        print(f"Updated Google Sheet: {url}")
        return True

    except Exception as e:
        print(f"Error updating Google Sheet: {e}")
        return False


def update_google_sheet_apps_script(url: str, webhook_url: str) -> bool:
    """
    Update Google Sheet via Apps Script Web App.

    This is a simpler approach that doesn't require service account credentials.

    Setup:
        1. In your Google Sheet, go to Extensions → Apps Script
        2. Add this code:

        function doPost(e) {
          var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
          var data = JSON.parse(e.postData.contents);
          sheet.getRange("B1").setValue(data.ngrok_url);
          sheet.getRange("B2").setValue(new Date().toISOString());
          return ContentService.createTextOutput(JSON.stringify({success: true}));
        }

        3. Deploy as Web App (Execute as: Me, Access: Anyone)
        4. Copy the web app URL
    """
    try:
        data = json.dumps({"ngrok_url": url}).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            if result.get("success"):
                print(f"Updated Google Sheet via Apps Script: {url}")
                return True
            else:
                print(f"Apps Script error: {result}")
                return False

    except Exception as e:
        print(f"Error calling Apps Script: {e}")
        return False


def watch_and_update(sheet_id: str, interval: int = 30):
    """Watch for ngrok URL changes and update sheet."""
    print(f"Watching for ngrok URL changes (interval: {interval}s)...")
    print("Press Ctrl+C to stop")

    last_url = None

    while True:
        try:
            current_url = get_ngrok_url()

            if current_url and current_url != last_url:
                print(f"\nngrok URL changed: {current_url}")
                update_local_config(current_url)

                if sheet_id:
                    update_google_sheet_gspread(current_url, sheet_id)

                last_url = current_url

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\nStopping watch...")
            break


def main():
    parser = argparse.ArgumentParser(
        description="Update ngrok URL in Google Sheets for n8n workflows"
    )
    parser.add_argument(
        "--sheet-id",
        default=DEFAULT_SHEET_ID,
        help="Google Sheet ID (or set NGROK_CONFIG_SHEET_ID env var)"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch for URL changes and auto-update"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Check interval in seconds (default: 30)"
    )
    parser.add_argument(
        "--apps-script-url",
        help="Apps Script web app URL (alternative to service account)"
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Only update local config file, skip Google Sheets"
    )

    args = parser.parse_args()

    # Get current ngrok URL
    url = get_ngrok_url()

    if not url:
        print("Error: Could not get ngrok URL. Is ngrok running?")
        print("Start ngrok with: ngrok http 8000")
        sys.exit(1)

    print(f"Current ngrok URL: {url}")

    # Update local config
    update_local_config(url)

    if args.local_only:
        print("Local-only mode, skipping Google Sheets update")
        return

    # Watch mode
    if args.watch:
        watch_and_update(args.sheet_id, args.interval)
        return

    # One-time update
    if args.apps_script_url:
        update_google_sheet_apps_script(url, args.apps_script_url)
    elif args.sheet_id:
        update_google_sheet_gspread(url, args.sheet_id)
    else:
        print("\nNo Google Sheet configured. Options:")
        print("  1. Set NGROK_CONFIG_SHEET_ID environment variable")
        print("  2. Use --sheet-id argument")
        print("  3. Use --apps-script-url for Apps Script webhook")
        print("  4. Use --local-only to skip Google Sheets")


if __name__ == "__main__":
    main()
