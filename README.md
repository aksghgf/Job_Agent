# 🤖 Job Application Agent — Setup Guide
## 100% Free | Powered by Ollama (Local AI)

---

## Step 1 — Install Ollama (Local AI)

```bash
# Linux / Mac
curl -fsSL https://ollama.ai/install.sh | sh

# Windows: download from https://ollama.ai/download
```

Then pull the models (do this once):
```bash
ollama pull llama3.1       # Main AI brain (~4.7GB)
ollama pull llava          # Vision AI for screenshots (~4.7GB)
ollama serve               # Start Ollama (keep running)
```

> With your 32GB RAM, llama3.1:70b works too (better quality):
> `ollama pull llama3.1:70b`
> Then set `"model": "llama3.1:70b"` in config.json

---

## Step 2 — Get Telegram API Credentials

1. Go to **https://my.telegram.org/apps**
2. Log in with your phone number
3. Create a new app → copy **API ID** and **API Hash**
4. Paste into `config.json` under `telegram`

---

## Step 3 — Get Brevo API Key (Free Email)

1. Sign up at **https://app.brevo.com** (free)
2. Go to **Settings → API Keys → Generate**
3. Paste into `config.json` under `brevo.api_key`

---

## Step 4 — Fill Your Profile

Edit `config.json` → `profile` section:
- Add your name, email, phone, LinkedIn etc.
- Paste your resume text in `resume_text`
- Set your `target_role`
- Add your Telegram group usernames to monitor

**How to find group username:**
Right-click any Telegram group → Copy link → the part after `t.me/` is the username

---

## Step 5 — Install Python Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## Step 6 — Run the Agent

```bash
# Make sure Ollama is running first!
ollama serve

# In another terminal:
python main.py
```

First run will ask you to verify your phone number (one time only).

---

## What It Does

```
Telegram groups monitored
        ↓
  New job post detected
        ↓
  AI extracts links/emails
        ↓
  ┌─────────────────────┐
  │  Job Link found?    │──→ Opens browser → Detects form type
  │                     │    → Fills fields with your profile
  │                     │    → Submits automatically
  └─────────────────────┘
        ↓
  ┌─────────────────────┐
  │ Recruiter email?    │──→ Drafts personalized email
  │                     │    → Sends via Brevo
  └─────────────────────┘
        ↓
  Logged in applications_log.json
```

---

## Supported Form Types

| Form Type | Support Level |
|-----------|--------------|
| Google Forms (multi-step) | ✅ Full |
| Workday | ✅ Good |
| Greenhouse | ✅ Good |
| Lever | ✅ Good |
| Generic HTML forms | ✅ AI-guided |
| LinkedIn Easy Apply | ⚠️ Partial (needs login) |
| Forms with CAPTCHA | ❌ Manual needed |

---

## Files Overview

```
job-agent/
├── main.py              # Start here
├── telegram_reader.py   # Reads Telegram groups
├── link_classifier.py   # AI extracts links/emails
├── form_filler.py       # Playwright fills forms
├── email_sender.py      # Brevo sends emails
├── logger.py            # Tracks applications
├── config.json          # YOUR SETTINGS (edit this!)
├── requirements.txt     # Python packages
└── applications_log.json  # Auto-created, tracks what's done
```

---

## Troubleshooting

**Ollama not responding:**
```bash
ollama serve   # make sure this is running
```

**Telegram login issues:**
- Delete `job_agent_session.session` and re-run

**Form not filling:**
- Check `applications_log.json` for errors
- Some sites block automation — nothing we can do

**Brevo email failing:**
- Make sure sender email is verified in Brevo dashboard
