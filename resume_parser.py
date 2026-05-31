"""
Resume Parser - reads your PDF resume once at startup
Extracts raw text for AI to reason from dynamically
In CI mode, reads from RESUME_TEXT environment variable
"""

import os
from pypdf import PdfReader


def parse_resume(path: str = None) -> str:
    # CI mode — read from environment variable
    resume_env = os.getenv("RESUME_TEXT")
    if resume_env:
        print(f"✅ Resume loaded from environment ({len(resume_env)} characters)")
        return resume_env

    # Local mode — read from PDF file
    path = path or os.getenv("RESUME_PATH", "resume.pdf")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Resume not found at: {path}")

    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"

    print(f"✅ Resume loaded: {len(text)} characters from {len(reader.pages)} pages")
    return text.strip()


if __name__ == "__main__":
    print(parse_resume("resume.pdf"))