"""
Resume Parser - reads your PDF resume once at startup
Extracts raw text for AI to reason from dynamically
"""

import os
from pypdf import PdfReader


def parse_resume(path: str = None) -> str:
    path = path or os.getenv("RESUME_PATH", "resume.pdf")
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"Resume not found at: {path}")
    
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    
    print(f"✅ Resume loaded: {len(text)} characters from {len(reader.pages)} pages")
    return text.strip()