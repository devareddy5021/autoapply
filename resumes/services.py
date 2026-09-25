import io
import re
import logging
from pypdf import PdfReader

logger = logging.getLogger(__name__)

COMMON_TECH_SKILLS = [
    # Languages & Core
    "python", "sql", "scala", "java", "golang", "go", "rust", "c++", "c#", "r", "bash", "shell",
    "javascript", "typescript", "html", "css",
    # Data Engineering & Processing
    "spark", "pyspark", "apache spark", "hadoop", "hive", "apache flink", "flink", "apache beam", "beam",
    "airflow", "apache airflow", "dbt", "kafka", "apache kafka", "presto", "trino", "luigi", "prefect",
    "dagster", "nifi", "talend", "informatica", "aws glue", "emr", "kinesis",
    # Data Warehouses & Lakehouses
    "snowflake", "databricks", "bigquery", "redshift", "synapse", "delta lake", "iceberg", "hudi",
    # AI / Machine Learning / Deep Learning / LLMs
    "machine learning", "deep learning", "nlp", "computer vision", "pytorch", "tensorflow", "keras",
    "scikit-learn", "sklearn", "pandas", "numpy", "scipy", "xgboost", "lightgbm", "llm", "langchain",
    "llamaindex", "huggingface", "transformers", "mlflow", "kubeflow", "pinecone", "milvus", "chromadb",
    "weaviate", "generative ai", "genai", "prompt engineering",
    # Databases & Storage
    "postgresql", "postgres", "mysql", "sqlite", "oracle", "sql server", "mongodb", "cassandra",
    "dynamodb", "redis", "elasticsearch", "opensearch", "neo4j",
    # Cloud & DevOps
    "aws", "gcp", "google cloud", "azure", "docker", "kubernetes", "terraform", "ansible", "helm",
    "ci/cd", "jenkins", "github actions", "gitlab", "linux", "git", "github",
    # Web Frameworks & APIs
    "django", "flask", "fastapi", "react", "vue", "angular", "node.js", "nodejs", "express",
    "rest api", "graphql", "selenium", "playwright", "celery", "rabbitmq",
    # BI & Analytics & Concepts
    "tableau", "power bi", "looker", "metabase", "superset", "quicksight", "excel",
    "etl", "elt", "data modeling", "data pipeline", "data warehousing", "data lake", "data governance",
    "data quality", "data mesh", "stream processing", "batch processing"
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
