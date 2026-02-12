"""
Daily Life Coach Email Generator
Runs every morning via GitHub Actions.
Reads goals.md, generates a science-backed coaching email via Anthropic API,
and delivers it via Gmail.
"""

import os
import base64
import sys
import logging
from datetime import datetime
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
load_dotenv(SCRIPT_DIR.parent / "newsletter" / ".env")

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
RECIPIENT_EMAIL   = os.environ["RECIPIENT_EMAIL"]

GMAIL_SCOPES   = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_PATH     = SCRIPT_DIR.parent / "newsletter" / "token.json"
CREDS_PATH     = SCRIPT_DIR.parent / "newsletter" / "client_secret.json"
LOG_PATH       = SCRIPT_DIR / "coaching.log"
GOALS_PATH     = SCRIPT_DIR / "goals.md"

ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS      = 2048

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

# ── Coaching prompt ───────────────────────────────────────────────────────────

COACHING_PROMPT = """\
You are an expert life coach with deep knowledge of evidence-based psychology, \
behavioural science, and performance research. Your role is to deliver a \
personalised daily coaching message to help Sophie stay accountable to her goals, \
grow across all areas of her life, and show up as her best self.

Today's date: {today}
Day of week: {day_of_week}

Sophie's current goals are listed below:

{goals}

---

Generate a daily coaching email with the following structure:

**1. Morning Intention (2–3 sentences)**
A grounding, motivating opening tailored to the day of the week and goals. \
Avoid generic platitudes — make it feel personal and real.

**2. Today's Focus (1 goal area)**
Pick ONE goal area most relevant for today (rotate across the week). \
Give a single, specific, actionable task she can do TODAY to make progress. \
Keep it realistic and achievable in under 30 minutes.

**3. Science Spotlight (3–5 sentences)**
Share one evidence-based insight, study, or technique directly relevant to \
today's focus. Cite the research domain or researcher if possible \
(e.g. "Research by Dr. Andrew Huberman...", "A 2023 meta-analysis in Nature..."). \
Make it practical, not academic.

**4. Accountability Check-in**
Ask 2–3 reflective questions for Sophie to answer mentally or journal about. \
These should connect yesterday's intentions with today's energy and focus.

**5. Daily Mantra**
One short, powerful sentence she can repeat to herself today. \
Evidence-informed where possible (e.g. rooted in self-compassion, growth mindset, \
or implementation intention research).

---

Tone: Warm, direct, encouraging — like a trusted coach who knows you well. \
Not preachy. Not generic. Grounded in science but human and conversational.
Length: 300–400 words.
Output: Only the email body. No meta-commentary.
"""


def load_goals() -> str:
    if not GOALS_PATH.exists():
        raise FileNotFoundError(f"Goals file not found: {GOALS_PATH}")
    return GOALS_PATH.read_text(encoding="utf-8")


def generate_coaching_email(goals: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    now = datetime.now()
    prompt = COACHING_PROMPT.format(
        today=now.strftime("%B %d, %Y"),
        day_of_week=now.strftime("%A"),
        goals=goals,
    )

    log.info("Calling Anthropic API (model=%s) …", ANTHROPIC_MODEL)
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    if not text.strip():
        raise ValueError("No content returned by the model.")

    log.info("Coaching email generated (%d chars).", len(text))
    return text


# ── HTML template ─────────────────────────────────────────────────────────────

def _build_html(subject: str, body_markdown: str) -> str:
    content_html = md.markdown(body_markdown, extensions=["extra", "nl2br"])

    # Style bold section headers distinctly
    for label in [
        "Morning Intention",
        "Today's Focus",
        "Science Spotlight",
        "Accountability Check-in",
        "Daily Mantra",
    ]:
        content_html = content_html.replace(
            f"<strong>{label}</strong>",
            f'<strong style="color:#0f766e;">{label}</strong>',
        )

    now = datetime.now()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#f0fdf4;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0fdf4;">
    <tr><td align="center" style="padding:32px 16px;">

      <table role="presentation" width="100%" style="max-width:600px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#064e3b 0%,#0f766e 100%);padding:32px 40px;">
            <p style="margin:0 0 4px 0;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#6ee7b7;font-weight:600;">Daily Coaching</p>
            <h1 style="margin:0;font-size:20px;font-weight:700;color:#ffffff;line-height:1.3;">Good morning, Sophie</h1>
            <p style="margin:8px 0 0 0;font-size:13px;color:#a7f3d0;">{now.strftime("%A, %B %d, %Y")}</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:32px 40px 24px 40px;color:#1e293b;font-size:15px;line-height:1.75;">
            <style>
              .cl strong {{ color:#0f766e; }}
              .cl p {{ margin:0 0 12px 0; color:#334155; }}
              .cl ul {{ margin:6px 0 14px 0; padding-left:20px; }}
              .cl li {{ margin-bottom:6px; color:#334155; }}
              .cl h2, .cl h3 {{ color:#064e3b; margin:20px 0 8px 0; font-size:15px; }}
              .cl blockquote {{
                border-left:3px solid #0f766e;
                margin:0 0 14px 0;
                padding:10px 16px;
                background:#f0fdf4;
                border-radius:0 6px 6px 0;
                font-style:italic;
                color:#334155;
              }}
              .cl hr {{ border:none; border-top:1px solid #d1fae5; margin:20px 0; }}
            </style>
            <div class="cl">
              {content_html}
            </div>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f0fdf4;padding:18px 40px;border-top:1px solid #d1fae5;">
            <p style="margin:0;font-size:12px;color:#6b7280;text-align:center;">
              Your daily coach &nbsp;·&nbsp; Delivered every morning &nbsp;·&nbsp; Edit your goals in <code>coaching/goals.md</code>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ── Gmail ─────────────────────────────────────────────────────────────────────

def get_gmail_service():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), GMAIL_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("Refreshing Gmail OAuth token …")
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds)


def send_email(service, to_address: str, subject: str, body: str) -> None:
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"]    = to_address
    message["To"]      = to_address
    message.attach(MIMEText(body, "plain", "utf-8"))
    message.attach(MIMEText(_build_html(subject, body), "html", "utf-8"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    try:
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        log.info("Coaching email sent to %s", to_address)
    except HttpError as e:
        log.error("Gmail API error: %s", e)
        raise


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    now = datetime.now()
    subject = f"Your Daily Coaching — {now.strftime('%A, %B %d')}"

    log.info("=== Coaching run started: %s ===", now.strftime("%Y-%m-%d"))

    goals        = load_goals()
    email_body   = generate_coaching_email(goals)
    gmail        = get_gmail_service()
    send_email(gmail, RECIPIENT_EMAIL, subject, email_body)

    log.info("=== Coaching run complete ===")


if __name__ == "__main__":
    main()
