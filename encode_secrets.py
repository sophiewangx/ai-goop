"""
Run this once to get the base64-encoded values to paste into GitHub Secrets.

    python encode_secrets.py

Copy each value printed below into the corresponding GitHub Secret.
"""

import base64
from pathlib import Path

ROOT = Path(__file__).parent

files = {
    "GMAIL_TOKEN_JSON_B64":          ROOT / "newsletter" / "token.json",
    "GMAIL_CLIENT_SECRET_JSON_B64":  ROOT / "newsletter" / "client_secret.json",
}

print("\n── GitHub Secret values ─────────────────────────────────────────────\n")
for secret_name, path in files.items():
    if not path.exists():
        print(f"[MISSING] {path} not found — skipping {secret_name}\n")
        continue
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    print(f"Secret name : {secret_name}")
    print(f"Secret value: {encoded}")
    print()

print("─────────────────────────────────────────────────────────────────────")
print("Also add these two secrets manually:")
print("  ANTHROPIC_API_KEY   → your Anthropic API key")
print("  RECIPIENT_EMAIL     → sophie.wang1995@gmail.com")
print()
