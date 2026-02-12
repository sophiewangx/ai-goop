"""
One-time Gmail OAuth2 authorization.

Run this script once before first use:
    python newsletter/setup_gmail_auth.py

It will open your browser, ask you to sign in to Google and grant
"Send email" permission, then save a token.json file in this folder.
The main script (generate_newsletter.py) reuses that token automatically
and silently refreshes it when it expires.
"""

from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES     = ["https://www.googleapis.com/auth/gmail.send"]
SCRIPT_DIR = Path(__file__).parent.resolve()
CREDS_PATH = SCRIPT_DIR / "client_secret.json"
TOKEN_PATH = SCRIPT_DIR / "token.json"


def main() -> None:
    if not CREDS_PATH.exists():
        print(
            f"\n[ERROR] {CREDS_PATH} not found.\n"
            "Please download your OAuth 2.0 credentials from Google Cloud Console\n"
            "and save the file as newsletter/client_secret.json\n\n"
            "Steps:\n"
            "  1. https://console.cloud.google.com → APIs & Services → Credentials\n"
            "  2. Create Credentials → OAuth client ID → Desktop app\n"
            "  3. Download JSON → rename to client_secret.json → place in newsletter/\n"
        )
        raise SystemExit(1)

    print("Opening browser for Gmail authorization …")
    flow  = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
    creds: Credentials = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    print(f"\n[OK] Authorization complete. Token saved to:\n  {TOKEN_PATH}\n")
    print("You can now run generate_newsletter.py.")


if __name__ == "__main__":
    main()
