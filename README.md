# Job Application Agent

Monitors Telegram job groups, filters posts with AI, and auto-applies to relevant openings.

**AI:** [Groq](https://groq.com) (free tier) · **Forms:** Playwright · **Email:** Brevo · **CI:** GitHub Actions (every 15 min)

---

## What It Does

```
Telegram groups (configured in config.json)
        ↓
  Unread messages scanned (CI) or live + unread catch-up (local)
        ↓
  AI classifies links / recruiter emails
        ↓
  Job filter checks role, batch, experience, skills, location
        ↓
  ┌─────────────────────┐
  │  Job link found?    │──→ Playwright opens page → fills form → submits
  └─────────────────────┘
        ↓
  ┌─────────────────────┐
  │ Recruiter email?    │──→ Personalized email via Brevo
  └─────────────────────┘
        ↓
  Logged in applications_log.json + Telegram notification
```

**CI mode** scans all **unread** messages in your configured groups, processes them, then marks them as read.

**Local mode** processes unread messages first, then listens for new posts live.

---

## Quick Start (Local)

### 1. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Create a `.env` file

```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+91xxxxxxxxxx
GROQ_API_KEY=your_groq_key
BREVO_API_KEY=your_brevo_key
RESUME_PATH=resume.pdf
```

Get Telegram credentials at [my.telegram.org/apps](https://my.telegram.org/apps).  
Get a free Groq key at [console.groq.com](https://console.groq.com).

### 3. Configure groups and filters

Edit `config.json`:

- **`telegram.group_usernames`** — numeric chat IDs (see below)
- **`filter_profile`** — batch, experience, target roles, skills, locations
- **`groq`** — model name (default: `llama-3.1-8b-instant`)
- **`brevo`** — sender name and verified `from_email`

**Find group IDs:**

```bash
python get_chat_ids.py
```

Copy the `ID` values into `config.json`.

### 4. Add your resume

Place `resume.pdf` in the project root (or set `RESUME_PATH` in `.env`).

### 5. Run

```bash
python main.py
```

First run prompts for a Telegram login code (one time). A `job_agent_session.session` file is created locally.

---

## GitHub Actions (Automated CI)

The workflow in `.github/workflows/job_agent.yml` runs every **15 minutes** and can be triggered manually from the Actions tab.

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `TELEGRAM_API_ID` | From [my.telegram.org/apps](https://my.telegram.org/apps) |
| `TELEGRAM_API_HASH` | From [my.telegram.org/apps](https://my.telegram.org/apps) |
| `TELEGRAM_PHONE` | Your phone number with country code |
| `TELEGRAM_SESSION` | Telethon string session (see below) |
| `GROQ_API_KEY` | Groq API key |
| `BREVO_API_KEY` | Brevo API key |
| `RESUME_TEXT` | Full plain-text resume (paste from PDF) |

### Generate `TELEGRAM_SESSION`

Run locally once (with `.env` configured):

```bash
python get_session.py
```

Copy the full one-line string it prints into the **`TELEGRAM_SESSION`** GitHub secret.

> Use the **string session** output — not base64 of the `.session` file.

If the session expires or you change your Telegram password, regenerate it and update the secret.

### CI artifacts

After each run, download **`applications-log`** from the Actions artifact to see what was applied, skipped, or failed.

---

## Helper Scripts

| Script | Purpose |
|--------|---------|
| `get_chat_ids.py` | List Telegram chats and their numeric IDs |
| `get_session.py` | Generate a string session for GitHub Actions |
| `main.py` | Run the agent (local or CI) |

---

## Supported Form Types

| Form Type | Support Level |
|-----------|---------------|
| Google Forms (multi-step) | Full |
| Oracle HCM / Workday-style | Good |
| Greenhouse | Good |
| Lever | Good |
| Generic HTML forms | AI-guided |
| Multi-step iCIMS / Amazon | Partial (may hit step limit) |
| LinkedIn Easy Apply | Partial (needs login) |
| Forms with CAPTCHA | Manual needed |

---

## Files Overview

```
job-agent/
├── main.py              # Orchestrator — start here
├── telegram_reader.py   # Telegram unread scan + live listener
├── link_classifier.py   # AI extracts links and emails
├── job_filter.py        # AI filters jobs by your profile
├── form_filler.py       # Playwright form automation
├── email_sender.py      # Brevo email sender
├── resume_parser.py     # Loads resume.pdf or RESUME_TEXT
├── logger.py            # Duplicate tracking + stats
├── groq_client.py       # Groq API wrapper
├── get_chat_ids.py      # List Telegram group IDs
├── get_session.py       # Generate CI session string
├── config.json          # Groups, filter profile, AI settings
├── requirements.txt     # Python dependencies
├── .env                 # Secrets (local only — not committed)
└── applications_log.json  # Auto-created application history
```

---

## Troubleshooting

**Groq API not reachable**

- Check `GROQ_API_KEY` in `.env` or GitHub Secrets
- Confirm your Groq account has quota remaining

**Telegram login issues (local)**

- Delete `job_agent_session.session` and re-run `python main.py`
- For CI, re-run `python get_session.py` and update `TELEGRAM_SESSION`

**CI: `base64: invalid input`**

- Your `TELEGRAM_SESSION` secret must be the **string session** from `get_session.py`, not a base64-encoded file

**No jobs applied in CI**

- Unread scan only processes messages still marked unread in Telegram
- Jobs can be skipped by the filter (wrong role, batch, or experience)
- Check the Actions log and `applications_log.json` artifact for details

**Form not filling**

- Some ATS sites use multi-step flows or block automation
- Check `applications_log.json` for `failed` entries and apply manually

**Brevo email failing**

- Verify the sender email in the Brevo dashboard
- Set `BREVO_API_KEY` in `.env` or GitHub Secrets

**Messages marked read unexpectedly**

- CI marks groups as read after scanning so the same posts are not reprocessed every run
