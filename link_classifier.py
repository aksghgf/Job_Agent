"""
Link Classifier - Uses Groq AI to extract job links & recruiter emails
"""

import re
import json
import logging
from groq_client import GroqClient

log = logging.getLogger("LinkClassifier")


class LinkClassifier:
    def __init__(self, config: dict):
        self.groq = GroqClient(config)

    def health_check(self) -> bool:
        return self.groq.health_check()

    async def classify(self, text: str) -> dict:
        # Quick regex pre-filter to avoid wasting AI calls
        has_url   = bool(re.search(r'https?://\S+', text))
        has_email = bool(re.search(r'[\w.+-]+@[\w-]+\.\w+', text))

        if not has_url and not has_email:
            return {"type": "none", "links": [], "emails": []}

        prompt = f"""You are a job application assistant. Analyze this Telegram message and extract:
1. Job application links (Google Forms, Workday, Greenhouse, Lever, LinkedIn Easy Apply, company career pages, any apply URL)
2. Recruiter email addresses

Message:
\"\"\"{text[:2000]}\"\"\"

Respond ONLY with valid JSON, no explanation:
{{
  "job_links": ["url1", "url2"],
  "recruiter_emails": ["email1"],
  "is_job_post": true/false
}}

Rules:
- Only include links that lead to job applications (not just job descriptions)
- If a link looks like a job post (careers page, apply button), include it
- Only include emails that belong to recruiters or HR
- is_job_post should be true if this message is about a job opportunity"""

        try:
            raw    = await self.groq.generate(prompt, temperature=0.1)
            parsed = self._safe_parse(raw)

            links  = parsed.get("job_links", [])
            emails = parsed.get("recruiter_emails", [])
            is_job = parsed.get("is_job_post", False)

            if not is_job and not links and not emails:
                return {"type": "none", "links": [], "emails": []}

            if links and emails:
                return {"type": "both",           "links": links, "emails": emails}
            elif links:
                return {"type": "job_link",        "links": links, "emails": []}
            elif emails:
                return {"type": "recruiter_email", "links": [],    "emails": emails}
            return {"type": "none", "links": [], "emails": []}

        except Exception as e:
            log.error(f"Classifier error: {e}")
            return self._regex_fallback(text)

    def _safe_parse(self, text: str) -> dict:
        try:
            return json.loads(text)
        except Exception:
            pass
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return {}

    def _regex_fallback(self, text: str) -> dict:
        urls   = re.findall(r'https?://\S+', text)
        emails = re.findall(r'[\w.+-]+@[\w-]+\.\w+', text)

        job_keywords = ['apply', 'careers', 'jobs', 'workday', 'greenhouse',
                        'lever', 'google.com/forms', 'linkedin', 'job']
        job_links = [u for u in urls if any(k in u.lower() for k in job_keywords)]

        if job_links and emails:
            return {"type": "both",           "links": job_links, "emails": emails}
        elif job_links:
            return {"type": "job_link",        "links": job_links, "emails": []}
        elif emails:
            return {"type": "recruiter_email", "links": [],        "emails": emails}
        return {"type": "none", "links": [], "emails": []}