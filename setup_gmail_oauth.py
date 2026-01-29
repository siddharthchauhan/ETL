#!/usr/bin/env python3
"""
Gmail OAuth2 Setup — one-time script to obtain a refresh token.

Usage:
    python setup_gmail_oauth.py

Prerequisites:
    1. Create a project in Google Cloud Console
    2. Enable the Gmail API
    3. Configure OAuth consent screen (External, add your email as test user)
    4. Create OAuth Client ID (Desktop app type)
    5. Add http://localhost:9004 as an Authorized redirect URI
    6. Set environment variables:
         GMAIL_CLIENT_ID=<your-client-id>
         GMAIL_CLIENT_SECRET=<your-client-secret>
       Or pass them as arguments:
         python setup_gmail_oauth.py --client-id=... --client-secret=...

This script will:
    1. Open your browser to the Google consent page
    2. Start a tiny local server on port 9004 to capture the callback
    3. Exchange the authorization code for tokens
    4. Print the GMAIL_REFRESH_TOKEN for you to add to .env
"""

import os
import sys
import json
import webbrowser
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

REDIRECT_PORT = 9004
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
SCOPE = "https://mail.google.com/"

# Global to capture the auth code from the callback
_auth_code = None


class _CallbackHandler(BaseHTTPRequestHandler):
    """Handles the OAuth2 redirect callback."""

    def do_GET(self):
        global _auth_code
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if "code" in params:
            _auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body style='font-family:sans-serif;text-align:center;padding:60px;'>"
                b"<h2>Authorization successful!</h2>"
                b"<p>You can close this tab and return to the terminal.</p>"
                b"</body></html>"
            )
        elif "error" in params:
            error = params.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                f"<html><body><h2>Error: {error}</h2></body></html>".encode()
            )
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress request logs


def exchange_code_for_tokens(client_id: str, client_secret: str, code: str) -> dict:
    """Exchange authorization code for access + refresh tokens."""
    data = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main():
    # Parse arguments
    client_id = os.getenv("GMAIL_CLIENT_ID", "")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET", "")

    for arg in sys.argv[1:]:
        if arg.startswith("--client-id="):
            client_id = arg.split("=", 1)[1]
        elif arg.startswith("--client-secret="):
            client_secret = arg.split("=", 1)[1]

    if not client_id or not client_secret:
        print("ERROR: GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET are required.")
        print()
        print("Set them as environment variables or pass as arguments:")
        print("  python setup_gmail_oauth.py --client-id=... --client-secret=...")
        sys.exit(1)

    # Build authorization URL
    auth_params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    })
    auth_url = f"{AUTH_URL}?{auth_params}"

    print("=" * 60)
    print("  Gmail OAuth2 Setup")
    print("=" * 60)
    print()
    print("1. Opening your browser to authorize access...")
    print()
    print("   If the browser doesn't open, visit this URL manually:")
    print(f"   {auth_url}")
    print()
    print(f"2. Waiting for callback on http://localhost:{REDIRECT_PORT} ...")
    print()

    # Start local callback server
    server = HTTPServer(("127.0.0.1", REDIRECT_PORT), _CallbackHandler)
    server_thread = Thread(target=server.handle_request, daemon=True)
    server_thread.start()

    # Open browser
    webbrowser.open(auth_url)

    # Wait for callback
    server_thread.join(timeout=120)
    server.server_close()

    if not _auth_code:
        print("ERROR: Did not receive authorization code within 2 minutes.")
        sys.exit(1)

    print("3. Received authorization code. Exchanging for tokens...")
    print()

    # Exchange code for tokens
    try:
        tokens = exchange_code_for_tokens(client_id, client_secret, _auth_code)
    except Exception as e:
        print(f"ERROR: Token exchange failed: {e}")
        sys.exit(1)

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("ERROR: No refresh_token in response. Try again with prompt=consent.")
        print(f"Response: {json.dumps(tokens, indent=2)}")
        sys.exit(1)

    print("=" * 60)
    print("  SUCCESS! Add these to your .env file:")
    print("=" * 60)
    print()
    print(f"GMAIL_CLIENT_ID={client_id}")
    print(f"GMAIL_CLIENT_SECRET={client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={refresh_token}")
    print(f"SMTP_FROM=<your-gmail-address>")
    print()
    print("Then restart `langgraph dev` to pick up the new variables.")
    print()


if __name__ == "__main__":
    main()
