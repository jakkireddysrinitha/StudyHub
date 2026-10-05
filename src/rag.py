import hashlib
import re
from pathlib import Path

import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from src.config import (
    CHROMA_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL
)


embedding_model = SentenceTransformer(
    EMBEDDING_MODEL
)


chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)


collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={
        "hnsw:space": "cosine"
    }
)


def extract_pdf_text(file_path):
    reader = PdfReader(file_path)

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""

        if text.strip():
            pages.append(text)

    return "\n".join(pages)


def clean_text(text):
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def chunk_text(
    text,
    chunk_size=800,
    overlap=120
):
    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = end - overlap

    return chunks


def get_category(text, filename):
    sample = f"{filename} {text[:5000]}".lower()

    categories = {
        "AI & Machine Learning": [
            "machine learning",
            "artificial intelligence",
            "neural network",
            "deep learning",
            "natural language processing",
            "computer vision",
            "tensorflow",
            "pytorch"
        ],
        "Programming": [
            "python",
            "java",
            "javascript",
            "programming",
            "algorithm",
            "data structure",
            "function",
            "class",
            "object oriented"
        ],
        "Database / DBMS": [
            "database",
            "dbms",
            "sql",
            "mysql",
            "postgresql",
            "normalization",
            "query",
            "transaction"
        ],
        "Mathematics": [
            "mathematics",
            "calculus",
            "algebra",
            "probability",
            "statistics",
            "matrix",
            "derivative",
            "integral"
        ]
    }

    scores = {}

    for category, keywords in categories.items():
        scores[category] = sum(
            1
            for keyword in keywords
            if keyword in sample
        )

    best_category = max(
        scores,
        key=scores.get
    )

    if scores[best_category] == 0:
        return "General Study"

    return best_category


def process_pdf(file_path):
    file_path = Path(file_path)

    raw_text = extract_pdf_text(
        file_path
    )

    cleaned_text = clean_text(
        raw_text
    )

    if not cleaned_text:
        raise ValueError(
            "No readable text was found in the PDF."
        )

    chunks = chunk_text(
        cleaned_text
    )

    if not chunks:
        raise ValueError(
            "Could not create text chunks from the PDF."
        )

    category = get_category(
        cleaned_text,
        file_path.name
    )

    delete_resource(
        file_path.name
    )

    embeddings = embedding_model.encode(
        chunks,
        show_progress_bar=False
    )

    ids = []
    metadatas = []

    for index in range(len(chunks)):
        raw_id = (
            f"{file_path.name}-{index}"
        )

        chunk_id = hashlib.md5(
            raw_id.encode("utf-8")
        ).hexdigest()

        ids.append(
            chunk_id
        )

        metadatas.append({
            "source": file_path.name,
            "category": category,
            "chunk_index": index
        })

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings.tolist(),
        metadatas=metadatas
    )

    return {
        "name": file_path.name,
        "category": category
    }


def delete_resource(filename):
    collection.delete(
        where={
            "source": filename
        }
    )


def delete_all_resources():
    results = collection.get()

    ids = results.get(
        "ids",
        []
    )

    if ids:
        collection.delete(
            ids=ids
        )


def search_resources(
    query,
    filename=None,
    category=None,
    n_results=5
):
    query_embedding = embedding_model.encode(
        [query]
    ).tolist()

    where = None
    conditions = []

    if filename:
        conditions.append({
            "source": filename
        })

    if category:
        conditions.append({
            "category": category
        })

    if len(conditions) == 1:
        where = conditions[0]

    elif len(conditions) > 1:
        where = {
            "$and": conditions
        }

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        where=where
    )

    return results


def get_resource_documents(filename):
    results = collection.get(
        where={
            "source": filename
        }
    )

    documents = results.get(
        "documents",
        []
    )

    return documents