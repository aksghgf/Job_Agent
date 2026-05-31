"""
Email Sender - Uses Brevo free API + Groq to write emails from resume
300 emails/day free — https://app.brevo.com
"""

import os
import httpx
import logging
from groq_client import GroqClient

log = logging.getLogger("EmailSender")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class EmailSender:
    def __init__(self, brevo_config: dict, resume_text: str, groq_config: dict):
        self.api_key    = os.getenv("BREVO_API_KEY")
        self.from_email = brevo_config.get("from_email", "")
        self.from_name  = brevo_config.get("from_name", "")
        self.resume     = resume_text
        self.groq       = GroqClient(groq_config)

    async def send_application(self, to_email: str, job_context: str) -> bool:
        subject, body = await self._compose_from_resume(job_context)

        payload = {
            "sender": {
                "name":  self.from_name,
                "email": self.from_email
            },
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": self._to_html(body),
            "textContent": body
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    BREVO_API_URL,
                    headers={
                        "api-key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                if response.status_code in (200, 201):
                    log.info(f"Email sent to {to_email}")
                    return True
                else:
                    log.error(f"Brevo error {response.status_code}: {response.text}")
                    return False

        except Exception as e:
            log.error(f"Email send failed: {e}")
            return False

    async def _compose_from_resume(self, job_context: str) -> tuple:
        prompt = f"""Write a short professional job application email.

Resume:
{self.resume[:3000]}

Job context:
{job_context[:500]}

Format your response EXACTLY like this:
Subject: (one line subject)
---
(email body, 3 short paragraphs, under 150 words, no placeholders)

Do not add any explanation before or after."""

        try:
            text = await self.groq.generate(prompt, temperature=0.3)
            parts   = text.split("---", 1)
            subject = parts[0].replace("Subject:", "").strip() if parts else "Job Application"
            body    = parts[1].strip() if len(parts) > 1 else text
            return subject, body

        except Exception as e:
            log.error(f"AI email compose failed: {e}")
            return "Job Application", f"Please find my application.\n\n{self.resume[:300]}"

    def _to_html(self, text: str) -> str:
        lines = text.strip().split("\n")
        html_lines = []
        for line in lines:
            if line.strip() == "":
                html_lines.append("<br>")
            else:
                html_lines.append(f"<p style='margin:4px 0'>{line}</p>")
        return f"""<html><body style="font-family:Arial,sans-serif;font-size:15px;color:#222;max-width:600px;">
{"".join(html_lines)}
</body></html>"""