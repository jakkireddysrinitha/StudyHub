from pathlib import Path
import os

from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# PROJECT DIRECTORY
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# STORAGE ROOT
# ============================================================

# Local development:
#     project folder is used.
#
# Render:
#     set STUDYHUB_STORAGE_DIR=/var/data
#
# This lets SQLite, uploaded PDFs and ChromaDB
# live on a persistent Render disk.
STORAGE_ROOT = Path(
    os.getenv(
        "STUDYHUB_STORAGE_DIR",
        str(BASE_DIR)
    )
)


# ============================================================
# RESOURCE STORAGE
# ============================================================

RESOURCE_DIR = (
    STORAGE_ROOT
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
    STORAGE_ROOT
    / "chroma_db"
)


# ============================================================
# SQLITE DATABASE
# ============================================================

DATABASE_FILE = (
    STORAGE_ROOT
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