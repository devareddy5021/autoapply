import io
import re
import logging
from pypdf import PdfReader

logger = logging.getLogger(__name__)

COMMON_TECH_SKILLS = [
    "python", "django", "flask", "fastapi", "javascript", "typescript", "react", "vue",
    "angular", "node.js", "nodejs", "express", "sql", "postgresql", "postgres", "mysql",
    "sqlite", "mongodb", "redis", "celery", "docker", "kubernetes", "aws", "gcp", "azure",
    "git", "github", "ci/cd", "rest api", "graphql", "html", "css", "tailwind", "bootstrap",
    "linux", "bash", "selenium", "playwright", "pandas", "numpy", "pytorch", "tensorflow",
    "java", "c++", "c#", "golang", "go", "rust", "kafka", "rabbitmq"
]

def extract_text_from_pdf(pdf_file) -> str:
    """
    Extracts text content from a PDF file (file path or file-like object).
    """
    try:
        if hasattr(pdf_file, 'seek'):
            pdf_file.seek(0)
        reader = PdfReader(pdf_file)
        extracted_pages = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            extracted_pages.append(page_text.strip())
        full_text = "\n\n".join([p for p in extracted_pages if p])
        return full_text
    except Exception as exc:
        logger.error(f"Error extracting text from PDF: {exc}")
        return ""

def detect_skills_in_text(text: str) -> list:
    """
    Detects known technology keywords present in the text.
    """
    if not text:
        return []
    text_lower = text.lower()
    found_skills = []
    for skill in COMMON_TECH_SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.append(skill.title() if len(skill) > 3 else skill.upper())
    return sorted(list(set(found_skills)))
