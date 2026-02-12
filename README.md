# AI & Data Engineering Newsletter

An automated weekly newsletter delivered every **Monday at 8:00 AM EST** via GitHub Actions. Uses the Anthropic API to search the web and generate a curated briefing on AI and data engineering news, delivered to your Gmail inbox.

---

## How It Works

```
GitHub Actions (cron)
      │
      ▼
generate_newsletter.py
      │
      ├── Anthropic API (claude-sonnet-4-5)
      │   └── web_search tool (up to 15 searches)
      │       └── Generates markdown newsletter
      │
      ├── HTML renderer (markdown → styled email)
      │
      └── Gmail API → your inbox
```

**Newsletter covers:**
- Top AI News (model releases, funding, research breakthroughs)
- Perplexity AI Updates
- X Platform AI Updates
- Data Engineering & Infrastructure (Databricks, Snowflake, dbt, Airflow, etc.)
- Quick Strategic Takeaways

---

## Project Structure

```
ai-goop/
├── .github/
│   └── workflows/
│       └── newsletter.yml       # GitHub Actions cron job
├── newsletter/
│   ├── generate_newsletter.py   # Main script: generate + send
│   ├── setup_gmail_auth.py      # One-time Gmail OAuth2 setup
│   ├── requirements.txt         # Pinned Python dependencies
│   └── .env.example             # Template for local secrets
└── README.md
```

---

## Setup

### Prerequisites
- Python 3.11+
- Anthropic API account with credits
- Google Cloud project with Gmail API enabled

### 1. Clone and configure
```bash
git clone https://github.com/sophiewangx/ai-goop.git
cd ai-goop
cp newsletter/.env.example newsletter/.env
# Edit newsletter/.env with your API key and email
```

### 2. Install dependencies
```bash
python -m venv .venv
.venv/Scripts/pip install -r newsletter/requirements.txt   # Windows
# or
.venv/bin/pip install -r newsletter/requirements.txt       # Mac/Linux
```

### 3. Set up Gmail API credentials
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → Enable **Gmail API**
3. **Credentials → Create OAuth client ID → Desktop app** → Download JSON
4. Save the file as `newsletter/client_secret.json`
5. Run the one-time auth flow:
   ```bash
   .venv/Scripts/python newsletter/setup_gmail_auth.py
   ```
   A browser window opens — sign in and click Allow. A `token.json` is saved.

### 4. Configure GitHub Secrets
In your repo → **Settings → Secrets → Actions**, add:

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `RECIPIENT_EMAIL` | Your Gmail address |
| `GMAIL_TOKEN_JSON_B64` | `base64 -w0 newsletter/token.json` |
| `GMAIL_CLIENT_SECRET_JSON_B64` | `base64 -w0 newsletter/client_secret.json` |

> On Windows, use: `.venv/Scripts/python -c "import base64,pathlib; print(base64.b64encode(pathlib.Path('newsletter/token.json').read_bytes()).decode())"`

### 5. Test manually
```bash
.venv/Scripts/python newsletter/generate_newsletter.py
```

---

## Automation

The workflow runs automatically every **Monday at 13:00 UTC (8:00 AM EST)** via GitHub Actions — no server or laptop required.

To trigger a manual run: [Actions tab](https://github.com/sophiewangx/ai-goop/actions) → **Weekly AI & Data Engineering Newsletter** → **Run workflow**.

---

## Cost

| Service | Cost |
|---|---|
| GitHub Actions | Free (well within 2,000 min/month free tier) |
| Anthropic API | ~$5/year (Sonnet, 52 weekly runs) |
| Gmail API | Free |

---

## Maintenance

**If the newsletter stops arriving:**
1. Check the [Actions tab](https://github.com/sophiewangx/ai-goop/actions) for failed runs
2. Check your Anthropic API credit balance at [console.anthropic.com](https://console.anthropic.com)

**If Gmail auth fails (token expired after 6+ months of inactivity):**
1. Run `python newsletter/setup_gmail_auth.py` locally to regenerate `token.json`
2. Re-encode and update the `GMAIL_TOKEN_JSON_B64` GitHub Secret

**To change the newsletter content or prompt:**
Edit `NEWSLETTER_PROMPT` in [newsletter/generate_newsletter.py](newsletter/generate_newsletter.py).

**To change the delivery schedule:**
Edit the cron expression in [.github/workflows/newsletter.yml](.github/workflows/newsletter.yml). Use [crontab.guru](https://crontab.guru) to build expressions.
