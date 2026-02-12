"""
Weekly AI & Data Engineering Newsletter Generator
Runs every Monday at 8:00 AM via Windows Task Scheduler.
Generates newsletter content via Anthropic API (web search enabled),
then delivers it to the configured Gmail address.
"""

import os
import base64
import sys
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import anthropic
import markdown as md
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ── Config ────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent.resolve()
load_dotenv(SCRIPT_DIR / ".env")

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
RECIPIENT_EMAIL   = os.environ["RECIPIENT_EMAIL"]

GMAIL_SCOPES   = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_PATH     = SCRIPT_DIR / "token.json"
CREDS_PATH     = SCRIPT_DIR / "client_secret.json"
LOG_PATH       = SCRIPT_DIR / "newsletter.log"

ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS      = 4096
MAX_SEARCH_USES = 15

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── Date helpers ──────────────────────────────────────────────────────────────

def get_date_range() -> tuple[str, str]:
    """Return (start, end) strings for the previous Monday–Sunday."""
    today = datetime.now()
    # weekday(): Monday=0, Sunday=6
    # 'days_since_last_monday' when today IS Monday = 7 (we want the prior week)
    days_back = today.weekday() + 7
    last_monday = today - timedelta(days=days_back)
    last_sunday = last_monday + timedelta(days=6)
    fmt = "%B %d, %Y"
    return last_monday.strftime(fmt), last_sunday.strftime(fmt)

# ── Newsletter generation ─────────────────────────────────────────────────────

NEWSLETTER_PROMPT = """\
You are an AI research assistant and executive newsletter editor operating inside \
an automated weekly workflow.

Objective:
Generate a weekly AI & Data Engineering newsletter using ONLY information from \
{start_date} to {end_date}.

Content Requirements — gather and summarize the most important developments \
from this exact date range in:

1) Top AI News
   - Major model releases
   - Enterprise AI deployments
   - Significant research breakthroughs
   - Funding or strategic partnerships

2) Perplexity AI Updates
   - New features, product enhancements, enterprise moves
   - Integrations or monetization changes

3) X (formerly Twitter) AI-Related Updates
   - AI product launches, Grok updates
   - AI creator tools, platform changes affecting AI distribution

4) Data Engineering & Infrastructure
   - Data platforms (Databricks, Snowflake, BigQuery, etc.)
   - Streaming systems, lakehouse architecture
   - Open-source tools (Spark, dbt, Airflow, etc.)
   - MLOps or AI infrastructure developments
   - Cost, governance, performance improvements

For each item:
- Include the headline (hyperlinked if possible).
- Provide a 1–2 sentence summary of what happened.
- Add one bullet labeled "Application:" explaining the practical business, \
engineering, or product implication.

Newsletter Format:

Title: "Weekly AI & Data Engineering Brief – {start_date} to {end_date}"

Sections:
- Top AI News
- Perplexity Updates
- X Platform AI Updates
- Data Engineering & Infrastructure
- Quick Strategic Takeaways (3 concise, executive-level bullets)

Tone: Professional, executive-ready, concise, insightful. No speculation or rumors.
Length: 400–600 words. Focused and sharp.

Output: Fully formatted email-ready content, clean section headers, \
professional formatting, hyperlinks where available.
Do NOT include meta commentary or explanations — output only the newsletter body.

Critical constraint: If insufficient credible updates exist in a category within \
{start_date} to {end_date}, include fewer items rather than using outdated information.
"""


def generate_newsletter(start_date: str, end_date: str) -> str:
    """Call Anthropic with web search enabled; return the final newsletter text."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = NEWSLETTER_PROMPT.format(start_date=start_date, end_date=end_date)
    messages = [{"role": "user", "content": prompt}]
    tools = [
        {
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": MAX_SEARCH_USES,
        }
    ]

    log.info("Calling Anthropic API (model=%s) …", ANTHROPIC_MODEL)

    # Agentic loop: keep going until the model stops using tools
    while True:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=MAX_TOKENS,
            tools=tools,
            messages=messages,
        )

        # Append assistant turn
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            # Build tool_result blocks for every tool_use block
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    # Web search results are injected automatically by the API;
                    # we just need to acknowledge each tool_use with a placeholder
                    # so the conversation stays valid.
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "",   # server fills in search results
                        }
                    )
            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            continue

        # Any other stop reason — break to avoid infinite loop
        log.warning("Unexpected stop_reason: %s", response.stop_reason)
        break

    # Extract all text blocks from the final assistant message
    newsletter_text = "\n\n".join(
        block.text
        for block in response.content
        if hasattr(block, "text") and block.text
    )

    if not newsletter_text.strip():
        raise ValueError("No text content returned by the model.")

    log.info("Newsletter generated (%d chars).", len(newsletter_text))
    return newsletter_text


# ── Gmail helpers ─────────────────────────────────────────────────────────────

def get_gmail_service():
    """Return an authenticated Gmail API service, refreshing/creating creds as needed."""
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("Refreshing Gmail OAuth token …")
            creds.refresh(Request())
        else:
            if not CREDS_PATH.exists():
                raise FileNotFoundError(
                    f"Gmail credentials not found at {CREDS_PATH}. "
                    "Run setup_gmail_auth.py first."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDS_PATH), GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        log.info("Gmail token saved to %s", TOKEN_PATH)

    return build("gmail", "v1", credentials=creds)


def _build_html(subject: str, body_markdown: str) -> str:
    """Wrap converted markdown in a styled HTML email template."""
    content_html = md.markdown(
        body_markdown,
        extensions=["extra", "nl2br"],
    )

    # Post-process: style "Application:" label distinctly
    content_html = content_html.replace(
        "<strong>Application:</strong>",
        '<strong style="color:#2563eb;">Application:</strong>',
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">

  <!-- Outer wrapper -->
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f1f5f9;">
    <tr><td align="center" style="padding:32px 16px;">

      <!-- Card -->
      <table role="presentation" width="100%" style="max-width:640px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);padding:36px 40px;">
            <p style="margin:0 0 6px 0;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#93c5fd;font-weight:600;">Weekly Intelligence Brief</p>
            <h1 style="margin:0;font-size:22px;font-weight:700;color:#ffffff;line-height:1.3;">AI &amp; Data Engineering</h1>
            <p style="margin:10px 0 0 0;font-size:13px;color:#94a3b8;">{subject.split('–')[-1].strip() if '–' in subject else ''}</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:36px 40px 24px 40px;color:#1e293b;font-size:15px;line-height:1.7;">
            <style>
              .nl h2 {{
                font-size:13px;
                font-weight:700;
                letter-spacing:1.5px;
                text-transform:uppercase;
                color:#2563eb;
                margin:32px 0 14px 0;
                padding-bottom:8px;
                border-bottom:2px solid #e2e8f0;
              }}
              .nl h2:first-child {{ margin-top:0; }}
              .nl h3 {{
                font-size:15px;
                font-weight:600;
                color:#0f172a;
                margin:20px 0 6px 0;
              }}
              .nl p {{
                margin:0 0 10px 0;
                color:#334155;
              }}
              .nl ul {{
                margin:6px 0 14px 0;
                padding-left:20px;
              }}
              .nl li {{
                margin-bottom:6px;
                color:#334155;
              }}
              .nl a {{
                color:#2563eb;
                text-decoration:none;
                font-weight:500;
              }}
              .nl a:hover {{ text-decoration:underline; }}
              .nl hr {{
                border:none;
                border-top:1px solid #e2e8f0;
                margin:28px 0;
              }}
              .nl blockquote {{
                border-left:3px solid #2563eb;
                margin:0 0 14px 0;
                padding:8px 0 8px 16px;
                background:#f8fafc;
                border-radius:0 6px 6px 0;
              }}
            </style>
            <div class="nl">
              {content_html}
            </div>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;padding:20px 40px;border-top:1px solid #e2e8f0;">
            <p style="margin:0;font-size:12px;color:#94a3b8;text-align:center;">
              Generated automatically every Monday at 8:00 AM &nbsp;·&nbsp; AI &amp; Data Engineering Brief
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_email(service, to_address: str, subject: str, body: str) -> None:
    """Send a multipart plain-text + HTML email via Gmail API."""
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"]    = to_address
    message["To"]      = to_address

    # Plain-text fallback
    message.attach(MIMEText(body, "plain", "utf-8"))

    # Styled HTML version
    html = _build_html(subject, body)
    message.attach(MIMEText(html, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    try:
        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        log.info("Email sent to %s", to_address)
    except HttpError as e:
        log.error("Gmail API error: %s", e)
        raise


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    start_date, end_date = get_date_range()
    subject = f"Weekly AI & Data Engineering Brief – {start_date} to {end_date}"

    log.info("=== Newsletter run started: %s to %s ===", start_date, end_date)

    newsletter_body = generate_newsletter(start_date, end_date)
    gmail_service   = get_gmail_service()
    send_email(gmail_service, RECIPIENT_EMAIL, subject, newsletter_body)

    log.info("=== Newsletter run complete ===")


if __name__ == "__main__":
    main()
