from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

RESOURCE_DIR = BASE_DIR / "data" / "resources"
METADATA_FILE = RESOURCE_DIR / "metadata.json"
CHROMA_DIR = BASE_DIR / "chroma_db"

COLLECTION_NAME = "study_resources"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

GEMINI_MODEL = "gemini-3.5-flash-lite"

RESOURCE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

CHROMA_DIR.mkdir(
    parents=True,
    exist_ok=True
)