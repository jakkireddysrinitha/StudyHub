import base64
import hashlib
import html
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from textwrap import dedent

import chromadb
import streamlit as st
from dotenv import load_dotenv
from google import genai
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from streamlit_auth import (
    current_user,
    initialize_auth_state,
    is_authenticated,
    login_user,
    logout_user,
    register_user,
)


# ============================================================
# APP CONFIGURATION
# ============================================================

load_dotenv()

st.set_page_config(
    page_title="StudyHub",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


CATEGORIES = [
    "AI & Machine Learning",
    "Programming",
    "Data Structures",
    "Database / DBMS",
    "Web Development",
    "Mathematics",
    "Computer Networks",
    "Operating Systems",
    "Cybersecurity",
    "Cloud Computing",
    "Software Engineering",
    "Electronics",
    "General Study",
    "Other",
]

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
BASE_DIR = Path(__file__).resolve().parent
RESOURCE_ROOT = BASE_DIR / "data" / "resources"
RESOURCE_ROOT.mkdir(parents=True, exist_ok=True)


# ============================================================
# SESSION STATE
# ============================================================

def initialize_app_state():
    initialize_auth_state()

    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"

    if "user_resources" not in st.session_state:
        st.session_state.user_resources = {}

    if "user_collections" not in st.session_state:
        st.session_state.user_collections = {}

    if "ignored_upload_hashes" not in st.session_state:
        st.session_state.ignored_upload_hashes = set()

    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"


initialize_app_state()


# ============================================================
# HTML HELPERS
# ============================================================

def render_html(content: str):
    """Render custom HTML without allowing indentation to turn it into code."""
    cleaned = dedent(content).strip()

    # st.html is preferred on modern Streamlit versions because it treats the
    # input explicitly as HTML. The fallback keeps the app compatible with
    # older versions that do not expose st.html.
    if hasattr(st, "html"):
        st.html(cleaned)
    else:
        st.markdown(cleaned, unsafe_allow_html=True)


def safe_text(value) -> str:
    return html.escape(str(value))


def format_date(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d %b %Y")
    return str(value)


# ============================================================
# GLOBAL CSS
# ============================================================

def inject_global_css():
    st.markdown(
        """
        <style>
        /* ---------- Streamlit shell ---------- */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {background: transparent !important;}

        [data-testid="stAppViewContainer"] {
            background: #f7f9fc;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        [data-testid="stMainBlockContainer"] {
            max-width: 1400px;
            padding-top: 28px;
            padding-bottom: 60px;
        }

        /* ---------- Sidebar ---------- */
        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid #edf1f5;
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 20px;
        }

        .sidebar-logo {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 6px 8px 24px 8px;
        }

        .sidebar-brand-icon {
            position: relative;
            width: 34px;
            height: 34px;
            flex: 0 0 34px;
        }

        .sidebar-brand-icon span {
            position: absolute;
            width: 14px;
            height: 14px;
            border-radius: 2px;
        }

        .sidebar-brand-icon .green {
            left: 0;
            top: 2px;
            background: #45c86a;
        }

        .sidebar-brand-icon .pink {
            left: 9px;
            top: 10px;
            background: #f16d9a;
        }

        .sidebar-brand-icon .blue {
            left: 18px;
            top: 18px;
            background: #5da9e9;
        }

        .sidebar-brand-text {
            font-size: 23px;
            font-weight: 800;
            color: #1b314c;
            line-height: 1;
        }

        .sidebar-user {
            padding: 13px 14px;
            margin: 0 2px 18px 2px;
            border-radius: 14px;
            background: #f7f9fc;
            border: 1px solid #edf1f5;
        }

        .sidebar-user-name {
            font-weight: 700;
            color: #1f3550;
            font-size: 14px;
        }

        .sidebar-user-email {
            margin-top: 4px;
            color: #8d97a5;
            font-size: 12px;
            word-break: break-word;
        }

        /* Native radio -> pill-like nav */
        [data-testid="stSidebar"] [data-testid="stRadio"] > div {
            gap: 6px;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            border-radius: 12px;
            padding: 10px 12px;
            margin-bottom: 4px;
            color: #637083;
            font-weight: 600;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
            background: #f2f7fb;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
            background: #eaf5fb;
            color: #3f9fd1;
        }

        /* ---------- Headings ---------- */
        .page-kicker {
            color: #8993a0;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.02em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .page-title {
            color: #1c344f;
            font-size: 34px;
            font-weight: 800;
            line-height: 1.12;
            margin: 0;
        }

        .page-subtitle {
            color: #8a94a3;
            font-size: 15px;
            margin-top: 8px;
        }

        .section-title {
            color: #1e3650;
            font-size: 20px;
            font-weight: 800;
            margin: 0;
        }

        .section-subtitle {
            color: #8b95a3;
            font-size: 13px;
            margin-top: 4px;
        }

        /* ---------- Hero ---------- */
        .hero {
            background: #eaf6ff;
            border: 1px solid #dceffb;
            border-radius: 22px;
            padding: 36px 38px;
            position: relative;
            overflow: hidden;
            margin-bottom: 24px;
        }

        .hero-badge {
            display: inline-flex;
            align-items: center;
            padding: 7px 11px;
            border-radius: 999px;
            background: #ffffff;
            color: #5a6878;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.08em;
        }

        .hero-title {
            margin-top: 16px;
            color: #1c344f;
            font-size: 44px;
            font-weight: 850;
            line-height: 1.03;
            max-width: 590px;
        }

        .hero-title span {
            color: #4aa6d9;
        }

        .hero-text {
            color: #768596;
            font-size: 15px;
            line-height: 1.7;
            max-width: 580px;
            margin-top: 15px;
        }

        .hero-art {
            position: absolute;
            right: 36px;
            bottom: 4px;
            width: 245px;
            height: 205px;
        }

        .book-shadow {
            position: absolute;
            left: 23px;
            bottom: 25px;
            width: 190px;
            height: 30px;
            border-radius: 50%;
            background: rgba(90, 138, 170, 0.15);
            filter: blur(2px);
        }

        .book-1,
        .book-2,
        .book-3 {
            position: absolute;
            border-radius: 8px;
            box-shadow: 0 10px 20px rgba(45, 80, 110, 0.12);
        }

        .book-1 {
            left: 52px;
            bottom: 40px;
            width: 142px;
            height: 68px;
            background: #5aa9e6;
            transform: rotate(-7deg);
        }

        .book-2 {
            left: 70px;
            bottom: 66px;
            width: 132px;
            height: 62px;
            background: #f3b2c7;
            transform: rotate(8deg);
        }

        .book-3 {
            left: 62px;
            bottom: 92px;
            width: 136px;
            height: 65px;
            background: #ffffff;
            border: 1px solid #dfe9f2;
            transform: rotate(-1deg);
        }

        .book-page-line {
            position: absolute;
            left: 18px;
            right: 18px;
            height: 5px;
            border-radius: 4px;
            background: #dce8f2;
        }

        .book-page-line.one {top: 17px; width: 72%;}
        .book-page-line.two {top: 30px; width: 82%;}
        .book-page-line.three {top: 43px; width: 58%;}

        /* ---------- Metrics ---------- */
        .metric-card {
            background: #ffffff;
            border: 1px solid #e8edf3;
            border-radius: 17px;
            padding: 20px 22px;
            min-height: 110px;
        }

        .metric-label {
            color: #8b96a5;
            font-size: 13px;
            font-weight: 700;
        }

        .metric-value {
            color: #1e3650;
            font-size: 31px;
            line-height: 1;
            font-weight: 850;
            margin-top: 12px;
        }

        /* ---------- Resource cards ---------- */
        .resource-card {
            background: #ffffff;
            border: 1px solid #e9edf3;
            border-radius: 17px;
            padding: 18px 18px 15px 18px;
            min-height: 160px;
            margin-bottom: 14px;
        }

        .resource-icon {
            width: 42px;
            height: 42px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #f1f7fb;
            font-size: 20px;
            margin-bottom: 13px;
        }

        .resource-name {
            color: #1e3650;
            font-weight: 800;
            font-size: 15px;
            line-height: 1.35;
            word-break: break-word;
        }

        .resource-meta {
            color: #8b95a3;
            font-size: 12px;
            margin-top: 7px;
        }

        .tag {
            display: inline-flex;
            border-radius: 999px;
            padding: 5px 8px;
            background: #eef8f0;
            color: #48a666;
            font-size: 10px;
            font-weight: 800;
            margin-top: 9px;
        }

        /* ---------- Empty states ---------- */
        .empty-state {
            text-align: center;
            border: 1px dashed #d8e1ea;
            background: #ffffff;
            border-radius: 18px;
            padding: 45px 24px;
        }

        .empty-icon {
            font-size: 40px;
            margin-bottom: 10px;
        }

        .empty-title {
            color: #1e3650;
            font-size: 19px;
            font-weight: 800;
        }

        .empty-text {
            color: #8a95a3;
            font-size: 13px;
            margin-top: 6px;
        }

        /* ---------- Buttons ---------- */
        .stButton > button {
            border-radius: 11px;
            min-height: 42px;
            font-weight: 700;
            border: 1px solid #dbe4ec;
        }

        .stButton > button[kind="primary"] {
            background: #49a8db;
            color: #ffffff;
            border-color: #49a8db;
        }

        .stButton > button[kind="primary"]:hover {
            background: #3e9dce;
            border-color: #3e9dce;
        }

        /* ---------- Form inputs ---------- */
        div[data-baseweb="input"] {
            border-radius: 10px;
            background: #f3f6fa;
            border-color: #e5ebf1;
        }

        div[data-baseweb="input"] input {
            color: #1d3450;
        }

        div[data-baseweb="select"] > div {
            border-radius: 10px;
        }

        /* ---------- Auth ---------- */
        .auth-shell {
            min-height: 82vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 30px 16px 60px 16px;
        }

        .auth-wrap {
            width: 100%;
            max-width: 550px;
        }

        .auth-card {
            background: #ffffff;
            border: 1px solid #e6ecf2;
            border-radius: 22px;
            box-shadow: 0 18px 55px rgba(31, 61, 88, 0.08);
            padding: 30px 34px 34px 34px;
        }

        .auth-brand {
            text-align: center;
            padding-bottom: 24px;
        }

        .auth-logo {
            position: relative;
            width: 42px;
            height: 42px;
            margin: 0 auto 7px auto;
        }

        .auth-logo span {
            position: absolute;
            width: 16px;
            height: 16px;
            border-radius: 2px;
        }

        .auth-logo .green {
            left: 3px;
            top: 3px;
            background: #45c86a;
        }

        .auth-logo .pink {
            left: 13px;
            top: 13px;
            background: #f16d9a;
        }

        .auth-logo .blue {
            left: 23px;
            top: 23px;
            background: #5da9e9;
        }

        .auth-title {
            color: #1c344f;
            font-size: 29px;
            font-weight: 850;
        }

        .auth-subtitle {
            color: #8c96a4;
            font-size: 13px;
            margin-top: 5px;
        }

        .auth-heading {
            color: #1c344f;
            font-size: 29px;
            font-weight: 850;
            margin-top: 12px;
        }

        .auth-copy {
            color: #8a94a2;
            font-size: 14px;
            margin-top: 4px;
            margin-bottom: 18px;
        }

        .auth-divider {
            height: 1px;
            background: #edf1f5;
            margin: 18px 0 10px 0;
        }

        .auth-switch {
            text-align: center;
            color: #8b95a3;
            font-size: 13px;
            margin-top: 11px;
            margin-bottom: 4px;
        }

        /* ---------- AI ---------- */
        .ai-banner {
            background: #eaf6ff;
            border: 1px solid #dceffb;
            border-radius: 18px;
            padding: 22px 24px;
            margin-bottom: 22px;
        }

        .ai-banner-title {
            color: #1e3650;
            font-size: 21px;
            font-weight: 850;
        }

        .ai-banner-text {
            color: #7b8998;
            font-size: 13px;
            line-height: 1.55;
            margin-top: 4px;
        }

        .answer-box {
            background: #ffffff;
            border: 1px solid #e6edf3;
            border-radius: 16px;
            padding: 22px;
            margin-top: 17px;
        }

        .answer-title {
            font-weight: 850;
            color: #1e3650;
            font-size: 15px;
            margin-bottom: 10px;
        }

        .source-chip {
            display: inline-flex;
            padding: 6px 8px;
            margin: 5px 5px 0 0;
            border-radius: 999px;
            background: #f1f7fb;
            color: #5c7082;
            font-size: 11px;
        }

        /* ---------- Mobile ---------- */
        @media (max-width: 900px) {
            .hero-title {font-size: 34px;}
            .hero-art {opacity: 0.18; right: -30px;}
            .hero {padding: 28px 24px;}
            .auth-card {padding: 26px 22px 28px 22px;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_global_css()


# ============================================================
# MODELS / CLIENTS
# ============================================================

@st.cache_resource(show_spinner="Loading the study AI model...")
def load_embedding_model():
    return SentenceTransformer("all-MiniLM-L6-v2")


@st.cache_resource
def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


@st.cache_resource
def get_chroma_client():
    # In-memory Chroma keeps this deployment self-contained for a free demo.
    # Each authenticated user gets a separate collection.
    return chromadb.Client()


embedding_model = load_embedding_model()
gemini_client = get_gemini_client()
chroma_client = get_chroma_client()


# ============================================================
# USER STORAGE
# ============================================================

def get_logged_in_user():
    user = current_user()
    if not user:
        return None
    return user


def ensure_user_storage(user_id):
    user_dir = RESOURCE_ROOT / safe_filesystem_name(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def safe_filesystem_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", str(value))
    return cleaned[:80] or "user"


def get_user_resource_dir(user_id):
    return ensure_user_storage(user_id)


def get_user_collection(user_id):
    if user_id not in st.session_state.user_collections:
        collection_name = f"studyhub_{safe_filesystem_name(user_id)}"

        # Chroma collection names have a limited character set/length.
        collection_name = collection_name[:60]

        st.session_state.user_collections[user_id] = (
            chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        )

    return st.session_state.user_collections[user_id]


def get_user_resources(user_id):
    if user_id not in st.session_state.user_resources:
        st.session_state.user_resources[user_id] = {}
    return st.session_state.user_resources[user_id]


# ============================================================
# TEXT / PDF PROCESSING
# ============================================================

def get_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def clean_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^a-zA-Z0-9._ -]", "_", name)
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name[:180]


def get_storage_path(user_id, file_hash, original_name):
    safe_name = clean_filename(original_name)
    user_dir = get_user_resource_dir(user_id)
    return user_dir / f"{file_hash[:12]}__{safe_name}"


def clean_text(text: str) -> str:
    text = (text or "").replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200):
    words = text.split()
    if not words:
        return []

    chunks = []
    current = []
    current_len = 0

    for word in words:
        add_len = len(word) + 1

        if current and current_len + add_len > chunk_size:
            chunks.append(" ".join(current))

            overlap_words = []
            overlap_len = 0

            for old_word in reversed(current):
                candidate_len = len(old_word) + 1
                if overlap_len + candidate_len > overlap:
                    break
                overlap_words.insert(0, old_word)
                overlap_len += candidate_len

            current = overlap_words + [word]
            current_len = sum(len(item) + 1 for item in current)
        else:
            current.append(word)
            current_len += add_len

    if current:
        chunks.append(" ".join(current))

    return chunks


def extract_pdf_text(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    pages = []

    for page in reader.pages:
        try:
            page_text = page.extract_text(extraction_mode="layout")
        except TypeError:
            page_text = page.extract_text()
        if page_text:
            pages.append(page_text)

    return clean_text("\n\n".join(pages))


# ============================================================
# AI HELPERS
# ============================================================

def handle_gemini_error(error) -> str:
    error_text = str(error)

    if (
        "RESOURCE_EXHAUSTED" in error_text
        or "429" in error_text
        or "quota" in error_text.lower()
    ):
        return "⏳ Gemini API quota has been reached. Please wait and try again later."

    if "API key" in error_text or "401" in error_text or "403" in error_text:
        return "⚠️ Gemini authentication failed. Check your GEMINI_API_KEY."

    return "⚠️ Gemini could not process this request."


def categorize_resource(text: str) -> str:
    if not gemini_client:
        return "Other"

    sample = text[:4000]
    prompt = f"""
You are organizing a student's study resources.

Choose exactly ONE category from this list:
{chr(10).join(CATEGORIES)}

Return ONLY the category name.

Study material:
{sample}
"""

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        category = (response.text or "").strip()

        for valid_category in CATEGORIES:
            if category.lower() == valid_category.lower():
                return valid_category

        return "Other"
    except Exception:
        return "Other"


def index_pdf(user_id, file_path, original_name, file_hash):
    collection = get_user_collection(user_id)

    try:
        existing = collection.get(
            where={"file_hash": file_hash},
            include=[],
        )
        if existing.get("ids"):
            return True, 0, None, "already_indexed"

        text = extract_pdf_text(file_path)
        if not text:
            return False, 0, None, "The PDF did not contain extractable text."

        chunks = chunk_text(text, chunk_size=1000, overlap=200)
        if not chunks:
            return False, 0, None, "No readable text was found in the PDF."

        category = categorize_resource(text)
        embeddings = embedding_model.encode(chunks).tolist()

        ids = [f"{file_hash}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "source": original_name,
                "category": category,
                "file_hash": file_hash,
                "stored_filename": file_path.name,
            }
            for _ in chunks
        ]

        collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        return True, len(chunks), category, None

    except Exception as error:
        return False, 0, None, str(error)


def search_resources(user_id, question, category_filter, number_of_results=5):
    collection = get_user_collection(user_id)
    query_embedding = embedding_model.encode([question]).tolist()

    kwargs = {
        "query_embeddings": query_embedding,
        "n_results": number_of_results,
        "include": ["documents", "metadatas", "distances"],
    }

    if category_filter != "All Resources":
        kwargs["where"] = {"category": category_filter}

    try:
        results = collection.query(**kwargs)
        documents = results.get("documents", [[]])[0] or []
        metadatas = results.get("metadatas", [[]])[0] or []
        distances = results.get("distances", [[]])[0] or []
        return documents, metadatas, distances
    except Exception:
        return [], [], []


def generate_answer(question, documents, metadatas):
    if not gemini_client:
        return (
            "⚠️ Gemini is not configured. Add GEMINI_API_KEY to your environment "
            "or Streamlit Secrets to enable AI answers."
        )

    if not documents:
        return "I couldn't find the answer in the uploaded study resources."

    context_parts = []
    for index, document in enumerate(documents):
        source = "Unknown resource"
        if index < len(metadatas):
            source = metadatas[index].get("source", source)
        context_parts.append(f"Source {index + 1} ({source}):\n{document}")

    context = "\n\n".join(context_parts)

    prompt = f"""
You are an AI study assistant.

Answer the student's question using ONLY the study material below.
Do not use outside knowledge.
If the answer cannot be found in the uploaded material, say exactly:
"I couldn't find the answer in the uploaded study resources."

Give a clear, concise, student-friendly answer.
Use short paragraphs or bullets where useful.

Study material:
{context}

Student question:
{question}
"""

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        return response.text or "I couldn't generate an answer."
    except Exception as error:
        return handle_gemini_error(error)


def generate_resource_summary(user_id, file_hash, source):
    if not gemini_client:
        return (
            "⚠️ Gemini is not configured. Add GEMINI_API_KEY to enable summaries."
        )

    collection = get_user_collection(user_id)

    try:
        results = collection.get(
            where={"file_hash": file_hash},
            include=["documents"],
        )

        documents = results.get("documents", []) or []
        if not documents:
            return "No indexed content was found for this resource."

        study_text = "\n\n".join(documents)[:16000]

        prompt = f"""
You are a study assistant.

Create a useful study summary of this resource using ONLY the supplied content.

Return this structure:

SUMMARY:
Write a clear summary in simple language.

KEY TOPICS:
- Topic 1
- Topic 2
- Topic 3
- Topic 4
- Topic 5

IMPORTANT POINTS:
- Point 1
- Point 2
- Point 3
- Point 4
- Point 5

Resource name:
{source}

Resource content:
{study_text}
"""

        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        return response.text or "No summary was generated."
    except Exception as error:
        return handle_gemini_error(error)


# ============================================================
# RESOURCE CRUD
# ============================================================

def resource_record(user_id, original_name, file_hash, stored_filename, category):
    return {
        "source": original_name,
        "file_hash": file_hash,
        "stored_filename": stored_filename,
        "category": category or "Other",
        "uploaded_at": datetime.now(),
    }


def delete_resource(user_id, file_hash):
    resources = get_user_resources(user_id)
    record = resources.get(file_hash)
    collection = get_user_collection(user_id)

    if record:
        try:
            results = collection.get(
                where={"file_hash": file_hash},
                include=[],
            )
            ids = results.get("ids", []) or []
            if ids:
                collection.delete(ids=ids)
        except Exception:
            pass

        stored_path = get_user_resource_dir(user_id) / record["stored_filename"]
        if stored_path.exists():
            try:
                stored_path.unlink()
            except OSError:
                pass

        resources.pop(file_hash, None)


def clear_all_resources(user_id):
    resources = get_user_resources(user_id)
    collection = get_user_collection(user_id)

    try:
        existing = collection.get(include=[])
        ids = existing.get("ids", []) or []
        if ids:
            collection.delete(ids=ids)
    except Exception:
        pass

    user_dir = get_user_resource_dir(user_id)
    for path in user_dir.iterdir():
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
        except OSError:
            pass

    resources.clear()


def preview_text(user_id, record):
    path = get_user_resource_dir(user_id) / record["stored_filename"]
    if not path.exists():
        return "The stored PDF file is not available in this session."

    try:
        text = extract_pdf_text(path)
        return text[:8000] or "No extractable text is available for preview."
    except Exception as error:
        return f"Could not preview this resource: {error}"


def pdf_data_uri(path: Path):
    try:
        encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
        return f"data:application/pdf;base64,{encoded}"
    except Exception:
        return None


# ============================================================
# AUTH SCREEN
# ============================================================

def show_auth_screen():
    render_html(
        """
        <div class="auth-shell">
            <div class="auth-wrap">
                <div class="auth-card">
                    <div class="auth-brand">
                        <div class="auth-logo">
                            <span class="green"></span>
                            <span class="pink"></span>
                            <span class="blue"></span>
                        </div>
                        <div class="auth-title">StudyHub</div>
                        <div class="auth-subtitle">AI-Powered Study Resource Organizer</div>
                    </div>
                </div>
            </div>
        </div>
        """
    )

    # The form is outside the HTML card so Streamlit's secure/native input
    # widgets remain fully functional. The visual treatment below matches the
    # same design system.
    _, form_col, _ = st.columns([1, 2, 1])

    with form_col:
        mode = st.session_state.auth_mode

        if mode == "login":
            st.markdown(
                '<div class="auth-heading">Welcome back</div>'
                '<div class="auth-copy">Log in to continue to your StudyHub.</div>',
                unsafe_allow_html=True,
            )

            email = st.text_input("Email", key="login_email")
            password = st.text_input(
                "Password",
                type="password",
                key="login_password",
            )

            if st.button("Login", use_container_width=True, type="primary"):
                success, message = login_user(email, password)
                if success:
                    st.session_state.page = "Dashboard"
                    st.toast("Welcome back to StudyHub!", icon="📚")
                    st.rerun()
                else:
                    st.error(message)

            st.markdown(
                '<div class="auth-divider"></div>'
                '<div class="auth-switch">Don\'t have an account?</div>',
                unsafe_allow_html=True,
            )

            if st.button("Create an account", use_container_width=True):
                st.session_state.auth_mode = "register"
                st.rerun()

        else:
            st.markdown(
                '<div class="auth-heading">Create your account</div>'
                '<div class="auth-copy">Start organizing your study resources with StudyHub.</div>',
                unsafe_allow_html=True,
            )

            username = st.text_input("Username", key="register_username")
            email = st.text_input("Email", key="register_email")
            password = st.text_input(
                "Password",
                type="password",
                key="register_password",
            )
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                key="register_confirm_password",
            )

            if st.button(
                "Create Account",
                use_container_width=True,
                type="primary",
            ):
                if password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    success, message = register_user(
                        username,
                        email,
                        password,
                    )
                    if success:
                        st.success(message)
                        st.session_state.auth_mode = "login"
                        st.session_state.login_email = email.strip().lower()
                        st.rerun()
                    else:
                        st.error(message)

            st.markdown(
                '<div class="auth-divider"></div>'
                '<div class="auth-switch">Already have an account?</div>',
                unsafe_allow_html=True,
            )

            if st.button("Back to Login", use_container_width=True):
                st.session_state.auth_mode = "login"
                st.rerun()


# ============================================================
# SIDEBAR
# ============================================================

def show_sidebar(user):
    with st.sidebar:
        render_html(
            """
            <div class="sidebar-logo">
                <div class="sidebar-brand-icon">
                    <span class="green"></span>
                    <span class="pink"></span>
                    <span class="blue"></span>
                </div>
                <div class="sidebar-brand-text">StudyHub</div>
            </div>
            """
        )

        render_html(
            f"""
            <div class="sidebar-user">
                <div class="sidebar-user-name">{safe_text(user['username'])}</div>
                <div class="sidebar-user-email">{safe_text(user['email'])}</div>
            </div>
            """
        )

        # Use normal buttons for navigation instead of st.radio.
        # A radio widget keeps its own session-state value and can override
        # programmatic navigation after a rerun. Buttons avoid that problem.
        if st.button(
            "🏠  Dashboard",
            key="nav_dashboard",
            use_container_width=True,
            type="primary" if st.session_state.page == "Dashboard" else "secondary",
        ):
            st.session_state.page = "Dashboard"
            st.session_state.open_upload = False
            st.rerun()

        if st.button(
            "📚  My Resources",
            key="nav_resources",
            use_container_width=True,
            type="primary" if st.session_state.page == "My Resources" else "secondary",
        ):
            st.session_state.page = "My Resources"
            st.session_state.open_upload = False
            st.rerun()

        if st.button(
            "🤖  AI Assistant",
            key="nav_ai",
            use_container_width=True,
            type="primary" if st.session_state.page == "AI Assistant" else "secondary",
        ):
            st.session_state.page = "AI Assistant"
            st.rerun()

        st.write("")
        st.write("")

        if st.button("↪  Logout", key="nav_logout", use_container_width=True):
            logout_user()
            st.session_state.auth_mode = "login"
            st.session_state.page = "Dashboard"
            st.session_state.open_upload = False
            st.rerun()


# ============================================================
# DASHBOARD
# ============================================================

def dashboard_page(user):
    user_id = user["id"]
    resources = get_user_resources(user_id)

    total_resources = len(resources)
    categories = sorted({record["category"] for record in resources.values()})

    render_html(
        """
        <div class="hero">
            <div class="hero-badge">AI-POWERED STUDY</div>
            <div class="hero-title">Organize. Learn. <span>Understand.</span></div>
            <div class="hero-text">
                Keep your notes and study PDFs in one place, then use AI to search,
                summarize, and understand your own resources.
            </div>
            <div class="hero-art">
                <div class="book-shadow"></div>
                <div class="book-1"></div>
                <div class="book-2"></div>
                <div class="book-3">
                    <div class="book-page-line one"></div>
                    <div class="book-page-line two"></div>
                    <div class="book-page-line three"></div>
                </div>
            </div>
        </div>
        """
    )

    upload_col, ai_col = st.columns([1, 1])

    with upload_col:
        if st.button("＋  Upload Study Resources", use_container_width=True, type="primary"):
            st.session_state.page = "My Resources"
            st.session_state.open_upload = True
            st.rerun()

    with ai_col:
        if st.button("✦  Ask AI About My Resources", use_container_width=True):
            st.session_state.page = "AI Assistant"
            st.rerun()

    st.write("")

    m1, m2 = st.columns(2)
    with m1:
        render_html(
            f"""
            <div class="metric-card">
                <div class="metric-label">Total Resources</div>
                <div class="metric-value">{total_resources}</div>
            </div>
            """
        )
    with m2:
        render_html(
            f"""
            <div class="metric-card">
                <div class="metric-label">Categories</div>
                <div class="metric-value">{len(categories)}</div>
            </div>
            """
        )

    st.write("")

    left, right = st.columns([1, 0.18])
    with left:
        render_html(
            '<div class="section-title">Recent Resources</div>'
            '<div class="section-subtitle">Your latest uploaded study materials</div>'
        )
    with right:
        if resources and st.button("View All", use_container_width=True):
            st.session_state.page = "My Resources"
            st.rerun()

    st.write("")

    if not resources:
        render_html(
            """
            <div class="empty-state">
                <div class="empty-icon">📚</div>
                <div class="empty-title">No study resources yet</div>
                <div class="empty-text">Upload your first PDF to start building your StudyHub.</div>
            </div>
            """
        )
        return

    latest = sorted(
        resources.values(),
        key=lambda item: item.get("uploaded_at", datetime.min),
        reverse=True,
    )[:5]

    for start in range(0, len(latest), 2):
        row = latest[start : start + 2]
        columns = st.columns(len(row))

        for index, record in enumerate(row):
            with columns[index]:
                render_resource_card(record, compact=True)


def render_resource_card(record, compact=False):
    source = safe_text(record["source"])
    category = safe_text(record.get("category", "Other"))
    uploaded_at = format_date(record.get("uploaded_at", ""))

    render_html(
        f"""
        <div class="resource-card">
            <div class="resource-icon">📄</div>
            <div class="resource-name">{source}</div>
            <div class="resource-meta">Uploaded {safe_text(uploaded_at)}</div>
            <div class="tag">{category}</div>
        </div>
        """
    )


# ============================================================
# MY RESOURCES PAGE
# ============================================================

def upload_resources(user):
    user_id = user["id"]
    resources = get_user_resources(user_id)

    render_html(
        """
        <div class="section-title">Add Study Resources</div>
        <div class="section-subtitle">Upload one or more PDF files to build your private study library.</div>
        """
    )

    uploaded_files = st.file_uploader(
        "Upload PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        key="resource_uploader",
        label_visibility="collapsed",
    )

    if not uploaded_files:
        return

    current_hashes = set()
    for uploaded_file in uploaded_files:
        current_hashes.add(get_file_hash(uploaded_file.getvalue()))

    st.session_state.ignored_upload_hashes = {
        file_hash
        for file_hash in st.session_state.ignored_upload_hashes
        if file_hash in current_hashes
    }

    for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.getvalue()
        file_hash = get_file_hash(file_bytes)

        if file_hash in st.session_state.ignored_upload_hashes:
            continue

        if file_hash in resources:
            st.info(f"{uploaded_file.name} is already in your resources.")
            continue

        storage_path = get_storage_path(user_id, file_hash, uploaded_file.name)

        try:
            storage_path.write_bytes(file_bytes)
        except OSError as error:
            st.error(f"Could not save {uploaded_file.name}: {error}")
            continue

        with st.spinner(f"Processing {uploaded_file.name}..."):
            success, chunks, category, error = index_pdf(
                user_id=user_id,
                file_path=storage_path,
                original_name=uploaded_file.name,
                file_hash=file_hash,
            )

        if success:
            resources[file_hash] = resource_record(
                user_id=user_id,
                original_name=uploaded_file.name,
                file_hash=file_hash,
                stored_filename=storage_path.name,
                category=category,
            )
            st.success(
                f"{uploaded_file.name} added successfully"
                + (f" • {chunks} chunks indexed" if chunks else "")
            )
        else:
            try:
                storage_path.unlink(missing_ok=True)
            except OSError:
                pass
            st.error(f"Could not process {uploaded_file.name}: {error}")

    st.session_state.open_upload = False


def resource_detail_controls(user, record):
    user_id = user["id"]
    file_hash = record["file_hash"]
    source = record["source"]
    stored_path = get_user_resource_dir(user_id) / record["stored_filename"]

    action_col1, action_col2, action_col3 = st.columns([1, 1, 1])

    with action_col1:
        preview_key = f"preview_{file_hash}"
        if st.button("Preview", key=preview_key, use_container_width=True):
            st.session_state[f"show_preview_{file_hash}"] = not st.session_state.get(
                f"show_preview_{file_hash}", False
            )

    with action_col2:
        if stored_path.exists():
            st.download_button(
                "Download",
                data=stored_path.read_bytes(),
                file_name=source,
                mime="application/pdf",
                key=f"download_{file_hash}",
                use_container_width=True,
            )
        else:
            st.button("Download", key=f"download_missing_{file_hash}", disabled=True, use_container_width=True)

    with action_col3:
        delete_key = f"delete_{file_hash}"
        if st.button("Delete", key=delete_key, use_container_width=True):
            delete_resource(user_id, file_hash)
            st.session_state.pop(f"show_preview_{file_hash}", None)
            st.toast(f"Deleted {source}", icon="🗑️")
            st.rerun()

    if st.session_state.get(f"show_preview_{file_hash}", False):
        st.markdown("#### Preview")

        if stored_path.exists():
            data_uri = pdf_data_uri(stored_path)
            if data_uri:
                render_html(
                    f"""
                    <iframe
                        src="{data_uri}"
                        width="100%"
                        height="560"
                        style="border:1px solid #e5ebf1;border-radius:12px;background:#fff;"
                    ></iframe>
                    """
                )

        preview = preview_text(user_id, record)
        st.text_area(
            "Extracted text preview",
            value=preview,
            height=250,
            key=f"text_preview_{file_hash}",
        )


def show_resource_item(user, record):
    source = record["source"]
    category = record.get("category", "Other")
    uploaded_at = format_date(record.get("uploaded_at", ""))

    with st.container(border=True):
        top1, top2 = st.columns([0.8, 0.2])
        with top1:
            render_html(
                f"""
                <div class="resource-name">📄 {safe_text(source)}</div>
                <div class="resource-meta">{safe_text(category)} • Uploaded {safe_text(uploaded_at)}</div>
                """
            )
        with top2:
            st.write("")

        resource_detail_controls(user, record)

        with st.expander("AI Summary", expanded=False):
            summary_key = f"summary_{record['file_hash']}"

            if summary_key not in st.session_state:
                st.info("Generate an AI summary from this resource.")

            if st.button(
                "Generate Summary",
                key=f"summary_btn_{record['file_hash']}",
                type="primary",
            ):
                with st.spinner("Generating summary..."):
                    st.session_state[summary_key] = generate_resource_summary(
                        user["id"],
                        record["file_hash"],
                        source,
                    )

            if summary_key in st.session_state:
                st.markdown(st.session_state[summary_key])


def resources_page(user):
    user_id = user["id"]
    resources = get_user_resources(user_id)

    render_html(
        """
        <div class="page-kicker">LIBRARY</div>
        <div class="page-title">My Resources</div>
        <div class="page-subtitle">Manage your private study PDFs in one clean workspace.</div>
        """
    )

    st.write("")

    upload_expanded = bool(st.session_state.get("open_upload", False))
    with st.expander("＋  Add Study Resources", expanded=upload_expanded):
        upload_resources(user)

    st.write("")

    controls1, controls2 = st.columns([1, 0.35])
    with controls1:
        selected_category = st.selectbox(
            "Filter by category",
            ["All Resources"] + CATEGORIES,
            key="resource_category_filter",
        )
    with controls2:
        st.write("")
        st.write("")
        if resources and st.button("Clear All", use_container_width=True):
            st.session_state.confirm_clear_all = True

    if st.session_state.get("confirm_clear_all", False) and resources:
        st.warning("This will delete all resources for the current account in this session.")
        confirm1, confirm2 = st.columns(2)
        with confirm1:
            if st.button("Yes, clear all", use_container_width=True, type="primary"):
                clear_all_resources(user_id)
                st.session_state.confirm_clear_all = False
                st.toast("All resources cleared", icon="🗑️")
                st.rerun()
        with confirm2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_clear_all = False
                st.rerun()

    filtered = [
        record
        for record in resources.values()
        if selected_category == "All Resources"
        or record.get("category") == selected_category
    ]

    filtered.sort(
        key=lambda item: item.get("uploaded_at", datetime.min),
        reverse=True,
    )

    st.write("")

    if not filtered:
        render_html(
            """
            <div class="empty-state">
                <div class="empty-icon">📂</div>
                <div class="empty-title">No matching resources</div>
                <div class="empty-text">Upload a PDF or change your category filter.</div>
            </div>
            """
        )
        return

    for record in filtered:
        show_resource_item(user, record)


# ============================================================
# AI ASSISTANT PAGE
# ============================================================

def ai_assistant_page(user):
    user_id = user["id"]
    resources = get_user_resources(user_id)

    render_html(
        """
        <div class="page-kicker">AI ASSISTANT</div>
        <div class="page-title">Ask your study library</div>
        <div class="page-subtitle">Get answers grounded only in the resources uploaded to your account.</div>
        """
    )

    st.write("")

    render_html(
        """
        <div class="ai-banner">
            <div class="ai-banner-title">🤖 StudyHub AI</div>
            <div class="ai-banner-text">
                Your question is matched against your own indexed PDFs before Gemini
                generates an answer. Resources from other users are not included.
            </div>
        </div>
        """
    )

    if not resources:
        render_html(
            """
            <div class="empty-state">
                <div class="empty-icon">🤖</div>
                <div class="empty-title">Upload a resource first</div>
                <div class="empty-text">AI answers work from the PDFs in your private study library.</div>
            </div>
            """
        )
        if st.button("Go to My Resources", type="primary"):
            st.session_state.page = "My Resources"
            st.rerun()
        return

    top1, top2 = st.columns([1, 0.35])
    with top1:
        category_filter = st.selectbox(
            "Search category",
            ["All Resources"] + CATEGORIES,
            key="ai_category_filter",
        )
    with top2:
        number_of_results = st.slider(
            "Context chunks",
            min_value=2,
            max_value=8,
            value=5,
            step=1,
            key="ai_context_chunks",
        )

    question = st.text_area(
        "What do you want to understand?",
        height=130,
        placeholder="Example: Explain normalization in DBMS using my uploaded notes.",
        key="ai_question",
    )

    if st.button("Ask StudyHub AI", use_container_width=True, type="primary"):
        if not question.strip():
            st.warning("Please enter a question first.")
        else:
            with st.spinner("Searching your resources and generating an answer..."):
                documents, metadatas, distances = search_resources(
                    user_id,
                    question.strip(),
                    category_filter,
                    number_of_results=number_of_results,
                )
                answer = generate_answer(question.strip(), documents, metadatas)

            st.session_state.last_ai_answer = answer
            st.session_state.last_ai_sources = metadatas
            st.session_state.last_ai_distances = distances

    if "last_ai_answer" in st.session_state:
        render_html(
            '<div class="answer-box">'
            '<div class="answer-title">Answer</div>'
            '</div>'
        )

        st.markdown(st.session_state.last_ai_answer)

        sources = st.session_state.get("last_ai_sources", [])
        if sources:
            st.markdown("**Sources used**")
            for metadata in sources:
                source = safe_text(metadata.get("source", "Unknown resource"))
                category = safe_text(metadata.get("category", "Other"))
                render_html(
                    f'<span class="source-chip">📄 {source} • {category}</span>'
                )


# ============================================================
# APP ENTRY
# ============================================================

def main():
    if not is_authenticated():
        show_auth_screen()
        return

    user = get_logged_in_user()
    if not user:
        logout_user()
        st.rerun()

    show_sidebar(user)

    if st.session_state.page == "Dashboard":
        dashboard_page(user)
    elif st.session_state.page == "My Resources":
        resources_page(user)
    else:
        ai_assistant_page(user)


main()
