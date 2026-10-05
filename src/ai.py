from dotenv import load_dotenv
from google import genai

from src.config import GEMINI_MODEL

import os

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is missing from .env"
    )

client = genai.Client(
    api_key=API_KEY
)


def generate_answer(question, search_results):
    documents = search_results.get(
        "documents",
        [[]]
    )[0]

    metadatas = search_results.get(
        "metadatas",
        [[]]
    )[0]

    if not documents:
        return {
            "answer": (
                "I couldn't find relevant information "
                "in your uploaded resources."
            ),
            "sources": []
        }

    context_parts = []

    for index, document in enumerate(documents):
        source = "Unknown"

        if index < len(metadatas):
            source = metadatas[index].get(
                "source",
                "Unknown"
            )

        context_parts.append(
            f"[Source: {source}]\n{document}"
        )

    context = "\n\n".join(
        context_parts
    )

    prompt = f"""
You are StudyHub AI, a helpful educational assistant.

Use ONLY the study material provided below
to answer the user's question.

Rules:
- Do not use outside knowledge.
- Do not invent facts.
- Give a clear explanation.
- Stay focused on the user's question.
- If the information is not present, say:
"I couldn't find this information in your uploaded resources."
- Never mention chunks, embeddings, vector databases,
retrieval systems, or internal implementation details.

STUDY MATERIAL:
{context}

USER QUESTION:
{question}
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        if not response.text:
            raise RuntimeError(
                "No answer was generated."
            )

        answer = response.text.strip()

    except Exception as error:
        error_text = str(error).lower()

        print("GEMINI ERROR:", error)

        if (
            "429" in error_text
            or "resource_exhausted" in error_text
            or "quota" in error_text
        ):
            raise RuntimeError(
                "The AI usage limit has been reached. "
                "Please try again later."
            )

        if (
            "api key" in error_text
            or "authentication" in error_text
            or "permission" in error_text
        ):
            raise RuntimeError(
                "There is a problem with the Gemini API key."
            )

        raise RuntimeError(
            "The AI assistant could not generate "
            "an answer right now."
        )

    sources = []

    for metadata in metadatas:
        source = metadata.get("source")

        if source and source not in sources:
            sources.append(source)

    return {
        "answer": answer,
        "sources": sources
    }


def generate_summary(filename, documents):
    if not documents:
        raise RuntimeError(
            "No study material was found for this resource."
        )

    text = "\n\n".join(documents)

    prompt = f"""
You are StudyHub AI.

Create a clear study summary from the material below.

Rules:
- Use ONLY the provided material.
- Do not add outside information.
- Highlight the important concepts.
- Use headings and bullet points where useful.
- Keep it easy for a student to understand.
- Do not mention chunks, embeddings, ChromaDB,
or internal systems.

RESOURCE:
{filename}

STUDY MATERIAL:
{text}
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        if not response.text:
            raise RuntimeError(
                "No summary was generated."
            )

        return response.text.strip()

    except Exception as error:
        error_text = str(error).lower()

        print("SUMMARY ERROR:", error)

        if (
            "429" in error_text
            or "resource_exhausted" in error_text
            or "quota" in error_text
        ):
            raise RuntimeError(
                "The AI usage limit has been reached. "
                "Please try again later."
            )

        raise RuntimeError(
            "The summary could not be generated right now."
        )