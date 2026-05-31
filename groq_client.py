"""
Groq Client - Drop-in replacement for Ollama
Uses OpenAI-compatible API, completely free
"""

import os
import httpx
import logging
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("GroqClient")


class GroqClient:
    def __init__(self, config: dict):
        self.api_key  = os.getenv("GROQ_API_KEY")
        self.model    = config.get("model", "llama-3.1-8b-instant")
        self.base_url = config.get("base_url", "https://api.groq.com/openai/v1")

    def health_check(self) -> bool:
        try:
            import httpx
            r = httpx.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=5
            )
            return r.status_code == 200
        except Exception:
            return False

    async def generate(self, prompt: str, temperature: float = 0.1) -> str:
        """Generate text — same interface as Ollama"""
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature
                }
            )
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()