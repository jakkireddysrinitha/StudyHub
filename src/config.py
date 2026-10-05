from pathlib import Path
import os

from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# BASE PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# RESOURCE STORAGE
# ============================================================

RESOURCE_DIR = (
    BASE_DIR
    / "data"
    / "resources"
)

METADATA_FILE = (
    RESOURCE_DIR
    / "metadata.json"
)


# ============================================================
# CHROMADB STORAGE
# ============================================================

CHROMA_DIR = (
    BASE_DIR
    / "chroma_db"
)


# ============================================================
# SQLITE DATABASE
# ============================================================

DATABASE_FILE = (
    BASE_DIR
    / "data"
    / "studyhub.db"
)


# ============================================================
# APPLICATION SETTINGS
# ============================================================

COLLECTION_NAME = "study_resources"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

GEMINI_MODEL = "gemini-3.5-flash-lite"


# ============================================================
# FLASK SECRET KEY
# ============================================================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "studyhub-development-secret-key"
)


# ============================================================
# CREATE REQUIRED DIRECTORIES
# ============================================================

RESOURCE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

CHROMA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

DATABASE_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)