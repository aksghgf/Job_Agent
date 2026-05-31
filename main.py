"""
Job Application Agent - Main Orchestrator
Monitors Telegram job groups, extracts links/emails, auto-applies
Uses Groq (free cloud AI)
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from telegram_reader import TelegramReader
from link_classifier import LinkClassifier
from form_filler import FormFiller
from email_sender import EmailSender
from logger import AgentLogger
from resume_parser import parse_resume
from job_filter import JobFilter

# Load .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("JobAgent")

CONFIG_PATH = Path("config.json")
LOG_PATH    = Path("applications_log.json")
IS_CI       = os.getenv("CI", "false").lower() == "true"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


async def process_message(message, classifier, job_filter, filler, emailer, logger, reader):
    """Process a single message — shared between CI and live mode"""
    try:
        log.info(f"New message from {message['chat']}: {message['text'][:80]}...")

        result = await classifier.classify(message["text"])

        # ── Job link found ───────────────────────────────────────
        if result["type"] in ("job_link", "both"):

            filter_result = await job_filter.is_relevant(message["text"])
            if not filter_result["relevant"]:
                print(f"\n⏭️  Skipped job: {filter_result['reason']}")
            else:
                for link in result["links"]:
                    if logger.already_processed(link):
                        log.info(f"Already applied to {link}, skipping.")
                        continue

                    if "telegram.me" in link or "t.me/" in link:
                        reason = "Not a job application URL (Telegram channel link)"
                        print(f"\n⏭️  Skipped link: {reason}")
                        logger.log(link, message["chat"], "failed", reason)
                        await reader.notify(
                            f"❌ Failed to apply\n"
                            f"🔗 {link}\n"
                            f"⚠️ {reason}\n"
                            f"👆 Manual action needed"
                        )
                        continue

                    print(f"\n📋 Job link found: {link}")
                    print(f"   Source: {message['chat']}")
                    print(f"   Applying automatically...")

                    success, reason = await filler.apply(
                        url=link,
                        job_context=message["text"]
                    )
                    status = "applied" if success else "failed"
                    logger.log(link, message["chat"], status, reason if not success else "")
                    if success:
                        print(f"   ✅ Applied!")
                    else:
                        print(f"   ❌ Failed: {reason}")

                    # ── Telegram notification ────────────────────
                    if success:
                        await reader.notify(
                            f"✅ Applied!\n"
                            f"🔗 {link}\n"
                            f"📌 Source: {message['chat']}\n"
                            f"🕐 {datetime.now().strftime('%H:%M')}"
                        )
                    else:
                        await reader.notify(
                            f"❌ Failed to apply\n"
                            f"🔗 {link}\n"
                            f"⚠️ {reason}\n"
                            f"👆 Manual action needed"
                        )

        # ── Recruiter email found ────────────────────────────────
        if result["type"] in ("recruiter_email", "both"):

            filter_result = await job_filter.is_relevant(message["text"])
            if not filter_result["relevant"]:
                print(f"\n⏭️  Skipped email: {filter_result['reason']}")
            else:
                for email in result["emails"]:
                    if logger.already_processed(email):
                        continue

                    print(f"\n📧 Recruiter email found: {email}")
                    print(f"   Sending application email...")

                    success = await emailer.send_application(
                        to_email=email,
                        job_context=message["text"]
                    )
                    status = "emailed" if success else "email_failed"
                    logger.log(email, message["chat"], status)
                    print(f"   {'✅ Email sent!' if success else '❌ Email failed'}")

                    # ── Telegram notification ────────────────────
                    if success:
                        await reader.notify(
                            f"📧 Email sent!\n"
                            f"To: {email}\n"
                            f"🕐 {datetime.now().strftime('%H:%M')}"
                        )

    except Exception as e:
        log.error(f"Error processing message: {e}")


async def main():
    config = load_config()
    logger = AgentLogger(LOG_PATH)

    print("""
    ╔══════════════════════════════════════╗
    ║      JOB APPLICATION AGENT v1.0      ║
    ║     Powered by Groq (Free AI) ⚡     ║
    ╚══════════════════════════════════════╝
    """)

    if IS_CI:
        print("⚡ Mode: GitHub Actions (scanning unread messages)")
    else:
        print("🖥️  Mode: Local (unread catch-up, then live monitoring)")

    # ── Load resume ONCE at startup ──────────────────────────────
    print("📄 Loading resume...")
    resume_text = parse_resume(os.getenv("RESUME_PATH", "resume.pdf"))

    # ── Init all components ──────────────────────────────────────
    classifier = LinkClassifier(config["groq"])
    filler     = FormFiller(resume_text, config["groq"])
    emailer    = EmailSender(config["brevo"], resume_text, config["groq"], config.get("applicant", {}))
    reader     = TelegramReader(config["telegram"])
    job_filter = JobFilter(config["filter_profile"], config["groq"])

    print("✅ Connecting to Telegram...")
    await reader.connect()

    print("✅ Checking Groq API...")
    if not classifier.health_check():
        print("❌ Groq API not reachable! Check your GROQ_API_KEY in .env")
        return

    print(f"✅ Monitoring {len(config['telegram']['group_usernames'])} Telegram groups...")
    print("🔍 Agent is live. Scanning for job posts...\n")

    # ── Choose mode ──────────────────────────────────────────────
    if IS_CI:
        # GitHub Actions — scan all unread messages and exit
        async for message in reader.listen_groups_unread():
            await process_message(
                message, classifier, job_filter,
                filler, emailer, logger, reader
            )
        print("\n✅ CI scan complete.")
        await reader.disconnect()
    else:
        # Local — live mode, runs forever
        async for message in reader.listen_groups():
            await process_message(
                message, classifier, job_filter,
                filler, emailer, logger, reader
            )


if __name__ == "__main__":
    asyncio.run(main())