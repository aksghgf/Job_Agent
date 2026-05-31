import os
from pypdf import PdfReader

def parse_resume(path: str = None) -> str:
    # CI mode — read directly from OS environment (not .env)
    resume_env = os.environ.get("RESUME_TEXT")
    if resume_env:
        print(f"✅ Resume loaded from environment ({len(resume_env)} characters)")
        return resume_env

    # Local mode — read from PDF
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