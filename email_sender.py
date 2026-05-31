"""
Email Sender - Uses Brevo free API + Groq to write tailored application emails
300 emails/day free — https://app.brevo.com
"""

import base64
import os
import httpx
import logging
from groq_client import GroqClient

log = logging.getLogger("EmailSender")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class EmailSender:
    def __init__(self, brevo_config: dict, resume_text: str, groq_config: dict, applicant: dict = None):
        self.api_key    = os.getenv("BREVO_API_KEY")
        self.from_email = brevo_config.get("from_email", "")
        self.from_name  = brevo_config.get("from_name", "")
        self.resume     = resume_text
        self.groq       = GroqClient(groq_config)
        self.applicant  = applicant or {}

    async def send_application(self, to_email: str, job_context: str) -> bool:
        subject, body = await self._compose_email(job_context, to_email)
        attachment = self._resume_attachment()

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
        if attachment:
            payload["attachment"] = attachment

        try:
            async with httpx.AsyncClient(timeout=30) as client:
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
                log.error(f"Brevo error {response.status_code}: {response.text}")
                return False

        except Exception as e:
            log.error(f"Email send failed: {e}")
            return False

    def _signature(self) -> str:
        name     = self.applicant.get("name", self.from_name)
        phone    = self.applicant.get("phone", "")
        email    = self.applicant.get("email", self.from_email)
        linkedin = self.applicant.get("linkedin", "")
        github   = self.applicant.get("github", "")

        lines = ["Best regards,", name]
        if phone:
            lines.append(phone)
        if email:
            lines.append(email)
        if linkedin:
            lines.append(f"LinkedIn: {linkedin}")
        if github:
            lines.append(f"GitHub: {github}")
        return "\n".join(lines)

    def _resume_attachment(self) -> list | None:
        pdf_b64 = os.getenv("RESUME_PDF_B64", "").strip()
        if pdf_b64:
            return [{"content": pdf_b64, "name": "Abhishek_Tiwari_Resume.pdf"}]

        path = os.getenv("RESUME_PATH", "resume.pdf")
        if os.path.exists(path):
            with open(path, "rb") as f:
                content = base64.b64encode(f.read()).decode()
            return [{"content": content, "name": "Abhishek_Tiwari_Resume.pdf"}]
        return None

    async def _compose_email(self, job_context: str, to_email: str) -> tuple[str, str]:
        name = self.applicant.get("name", self.from_name)
        has_resume = self._resume_attachment() is not None

        prompt = f"""Write a personalized job application email for this candidate applying to the role described below.

CANDIDATE RESUME (use facts from here only — do NOT paste the resume summary verbatim):
{self.resume[:4000]}

JOB POSTING / CONTEXT:
{job_context[:2000]}

RECIPIENT EMAIL: {to_email}

Write like a strong human cover email — similar in quality to these patterns:
- Open with "Dear [Recruiter Name] Sir," if a name appears in the posting, otherwise "Dear Hiring Team,"
- Paragraph 1: why THIS specific role/post stood out (reference concrete details from the job posting)
- Paragraph 2: 1-2 most relevant projects/internships from the resume that match the role's tech stack or domain
- Paragraph 3: what the candidate brings + genuine interest in the role/company
- Do NOT use generic openers like "Please find my application" or "I am writing to apply"
- Do NOT dump the resume summary or bullet list of skills
- Do NOT include phone, email, LinkedIn, or GitHub in the body (signature added separately)
- Tone: professional, warm, specific — not robotic
- Length: 180-280 words for the body only
{"- Mention that the resume is attached in one natural sentence near the end" if has_resume else ""}

Format your response EXACTLY like this:
Subject: Application for [specific role title from posting] — {name}
---
(email body only — no signature block)"""

        try:
            text = await self.groq.generate(prompt, temperature=0.45)
            subject, body = self._parse_compose_response(text)
        except Exception as e:
            log.error(f"AI email compose failed: {e}")
            subject, body = self._fallback_compose(job_context)

        if has_resume and "attach" not in body.lower():
            body = body.rstrip() + "\n\nI've attached my resume for your review."

        body = body.rstrip() + "\n\n" + self._signature()
        return subject, body

    def _parse_compose_response(self, text: str) -> tuple[str, str]:
        parts = text.split("---", 1)
        subject = parts[0].replace("Subject:", "").strip() if parts else "Job Application"
        body = parts[1].strip() if len(parts) > 1 else text.strip()
        return subject or "Job Application", body

    def _fallback_compose(self, job_context: str) -> tuple[str, str]:
        """Used only when Groq fails — still better than dumping raw resume."""
        name = self.applicant.get("name", self.from_name)
        role_hint = job_context.split("\n")[0][:80].strip() or "the role"
        body = (
            f"Dear Hiring Team,\n\n"
            f"Your post regarding {role_hint} caught my attention, and I'd like to express "
            f"my interest in the opportunity.\n\n"
            f"I'm an IIIT Surat student with SDE internship experience across full-stack "
            f"development, cloud infrastructure, and DevOps. I've built production-oriented "
            f"projects involving Python, FastAPI, MERN/Next.js, AWS, CI/CD, and agentic AI "
            f"workflows — and I'd welcome the chance to contribute similar skills to your team.\n\n"
            f"I'd be glad to discuss how my background aligns with what you're looking for."
        )
        return f"Application for {role_hint} — {name}", body

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
