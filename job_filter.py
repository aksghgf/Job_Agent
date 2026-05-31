"""
Job Filter - screens jobs before applying
Saves tokens by rejecting mismatched jobs early
"""

import json
import re
import logging
from groq_client import GroqClient

log = logging.getLogger("JobFilter")


class JobFilter:
    def __init__(self, profile: dict, groq_config: dict):
        self.profile = profile
        self.groq    = GroqClient(groq_config)

    async def is_relevant(self, message: str) -> dict:
        prompt = f"""You are screening a job posting for a candidate. Decide if this job is relevant.

CANDIDATE PROFILE:
- Graduation Year: {self.profile["batch"]}
- Experience: {self.profile["experience"]}
- Target Roles: {", ".join(self.profile["target_roles"])}
- Skills: {", ".join(self.profile["skills"])}
- Preferred Locations: {", ".join(self.profile["locations"])}

JOB POSTING:
{message[:1500]}

REJECTION RULES (reject if ANY of these match):
1. Required experience is MORE than candidate has
2. Batch/graduation year doesn't include candidate's year ({self.profile["batch"]})
3. Job role is completely unrelated to target roles (e.g. operations, finance, data analyst when candidate is developer)
4. Location is not in preferred locations AND not remote
5. Job is clearly for a different field (HR, marketing, sales, etc.)

Respond ONLY with JSON:
{{
  "relevant": true/false,
  "reason": "one line explanation"
}}"""

        try:
            raw   = await self.groq.generate(prompt, temperature=0.1)
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            log.error(f"Filter error: {e}")

        return {"relevant": True, "reason": "filter failed, defaulting to apply"}