import hashlib
import os
import re
from pathlib import Path

import chromadb
import streamlit as st
from dotenv import load_dotenv
from google import genai
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


load_dotenv()


# ==========================================================
# PAGE CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="StudyHub",
    page_icon="📚",
    layout="wide"
)


# ==========================================================
# FILE STORAGE
# ==========================================================

RESOURCE_DIR = Path("data") / "resources"
RESOURCE_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================================
# CATEGORIES
# ==========================================================

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
    "Other"
]


# ==========================================================
# SESSION STATE
# ==========================================================

if "ignored_upload_hashes" not in st.session_state:
    st.session_state.ignored_upload_hashes = set()


# ==========================================================
# EMBEDDING MODEL
# ==========================================================

@st.cache_resource
def load_embedding_model():
    return SentenceTransformer("all-MiniLM-L6-v2")


# ==========================================================
# CHROMADB
# ==========================================================

@st.cache_resource
def get_chroma_collection():

    client = chromadb.PersistentClient(
        path="chroma_db"
    )

    return client.get_or_create_collection(
        name="study_resources_v2"
    )


# ==========================================================
# GEMINI CLIENT
# ==========================================================

@st.cache_resource
def get_gemini_client():

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return None

    return genai.Client(
        api_key=api_key
    )


# ==========================================================
# FILE HASH
# ==========================================================

def get_file_hash(file_bytes):
    return hashlib.sha256(file_bytes).hexdigest()


# ==========================================================
# STORAGE PATH
# ==========================================================

def get_storage_path(file_hash, original_name):

    safe_name = Path(original_name).name

    return RESOURCE_DIR / (
        f"{file_hash[:12]}__{safe_name}"
    )


# ==========================================================
# TEXT CLEANING
# ==========================================================

def clean_text(text):

    text = text.replace("\x00", " ")

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ==========================================================
# TEXT CHUNKING
# ==========================================================

def chunk_text(
    text,
    chunk_size=1000,
    overlap=200
):

    words = text.split()

    chunks = []

    current_chunk = []
    current_length = 0

    for word in words:

        word_length = len(word) + 1

        if current_length + word_length > chunk_size:

            if current_chunk:
                chunks.append(
                    " ".join(current_chunk)
                )

            overlap_words = []
            overlap_length = 0

            for old_word in reversed(
                current_chunk
            ):

                if (
                    overlap_length
                    + len(old_word)
                    + 1
                    > overlap
                ):
                    break

                overlap_words.insert(
                    0,
                    old_word
                )

                overlap_length += (
                    len(old_word) + 1
                )

            current_chunk = (
                overlap_words + [word]
            )

            current_length = sum(
                len(word) + 1
                for word in current_chunk
            )

        else:

            current_chunk.append(word)

            current_length += word_length

    if current_chunk:
        chunks.append(
            " ".join(current_chunk)
        )

    return chunks


# ==========================================================
# GEMINI ERROR HANDLER
# ==========================================================

def handle_gemini_error(error):

    error_text = str(error)

    if (
        "RESOURCE_EXHAUSTED" in error_text
        or "429" in error_text
        or "quota" in error_text.lower()
    ):
        return (
            "⏳ Gemini API quota has been reached. "
            "Please wait until the quota resets."
        )

    return (
        "⚠️ Gemini could not process this request."
    )


# ==========================================================
# CATEGORIZE RESOURCE
# ==========================================================

def categorize_resource(
    text,
    client,
    model_name
):

    if not client:
        return "Other"

    sample = text[:4000]

    prompt = f"""
You are organizing a student's study resources.

Choose ONE category from this list:

AI & Machine Learning
Programming
Data Structures
Database / DBMS
Web Development
Mathematics
Computer Networks
Operating Systems
Cybersecurity
Cloud Computing
Software Engineering
Electronics
General Study
Other

Return ONLY the category name.

Study material:
{sample}
"""

    try:

        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )

        category = response.text.strip()

        for valid_category in CATEGORIES:

            if (
                category.lower()
                == valid_category.lower()
            ):
                return valid_category

        return "Other"

    except Exception:

        return "Other"


# ==========================================================
# CHECK INDEXED FILE
# ==========================================================

def is_file_indexed(
    file_hash,
    collection
):

    results = collection.get(
        where={
            "file_hash": file_hash
        },
        include=[]
    )

    return bool(
        results.get("ids")
    )


# ==========================================================
# INDEX PDF
# ==========================================================

def index_pdf(
    file_path,
    original_name,
    file_hash,
    embedding_model,
    collection,
    gemini_client,
    model_name
):

    if is_file_indexed(
        file_hash,
        collection
    ):
        return True, 0, None

    try:

        reader = PdfReader(
            str(file_path)
        )

        text = ""

        for page in reader.pages:

            page_text = page.extract_text(
                extraction_mode="layout"
            )

            if page_text:
                text += page_text + "\n"

        text = clean_text(text)

        if not text:
            return False, 0, None

        chunks = chunk_text(text)

        category = categorize_resource(
            text,
            gemini_client,
            model_name
        )

        embeddings = (
            embedding_model
            .encode(chunks)
            .tolist()
        )

        ids = [
            f"{file_hash}_{i}"
            for i in range(len(chunks))
        ]

        metadatas = [
            {
                "source": original_name,
                "category": category,
                "file_hash": file_hash,
                "stored_filename": file_path.name
            }
            for _ in chunks
        ]

        collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas
        )

        return True, len(chunks), category

    except Exception as error:

        st.error(
            f"Could not process {original_name}: {error}"
        )

        return False, 0, None


# ==========================================================
# RESOURCE INFORMATION
# ==========================================================

def get_resource_info(collection):

    data = collection.get(
        include=["metadatas"]
    )

    metadatas = data.get(
        "metadatas",
        []
    )

    resource_info = {}

    for metadata in metadatas:

        source = metadata["source"]

        if source not in resource_info:

            resource_info[source] = {
                "category": metadata.get(
                    "category",
                    "Other"
                ),
                "file_hash": metadata.get(
                    "file_hash"
                ),
                "stored_filename": metadata.get(
                    "stored_filename"
                )
            }

    return resource_info


# ==========================================================
# SEARCH RESOURCES
# ==========================================================

def search_resources(
    question,
    embedding_model,
    collection,
    category_filter,
    number_of_results=3
):

    question_embedding = (
        embedding_model
        .encode([question])
        .tolist()
    )

    search_arguments = {
        "query_embeddings": question_embedding,
        "n_results": number_of_results
    }

    if category_filter != "All Resources":

        search_arguments["where"] = {
            "category": category_filter
        }

    results = collection.query(
        **search_arguments
    )

    documents = results.get(
        "documents",
        [[]]
    )[0]

    metadatas = results.get(
        "metadatas",
        [[]]
    )[0]

    return documents, metadatas


# ==========================================================
# GENERATE AI ANSWER
# ==========================================================

def generate_answer(
    question,
    documents,
    client,
    model_name
):

    context = "\n\n".join(
        [
            f"Source {i + 1}:\n{document}"
            for i, document in enumerate(
                documents
            )
        ]
    )

    prompt = f"""
You are an AI study assistant.

Answer the student's question using ONLY
the study material provided below.

Do not use outside knowledge.

If the answer cannot be found in the
study material, say:

"I couldn't find the answer in the uploaded
study resources."

Give a clear and student-friendly answer.

Study material:
{context}

Student question:
{question}
"""

    try:

        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )

        return response.text

    except Exception as error:

        return handle_gemini_error(error)


# ==========================================================
# GENERATE SUMMARY
# ==========================================================

def generate_resource_summary(
    source,
    collection,
    client,
    model_name
):

    results = collection.get(
        where={
            "source": source
        },
        include=["documents"]
    )

    documents = results.get(
        "documents",
        []
    )

    if not documents:
        return None

    full_text = "\n\n".join(
        documents
    )

    study_text = full_text[:12000]

    prompt = f"""
You are a study assistant.

Create a useful study summary of the following
resource.

Return your response in exactly this structure:

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

Only use information from the provided resource.

Resource name:
{source}

Resource content:
{study_text}
"""

    try:

        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )

        return response.text

    except Exception as error:

        return handle_gemini_error(error)


# ==========================================================
# DELETE RESOURCE
# ==========================================================

def delete_resource(
    file_hash,
    stored_filename,
    collection
):

    results = collection.get(
        where={
            "file_hash": file_hash
        },
        include=[]
    )

    ids = results.get(
        "ids",
        []
    )

    if ids:
        collection.delete(
            ids=ids
        )

    file_path = (
        RESOURCE_DIR
        / stored_filename
    )

    if file_path.exists():

        file_path.unlink()


# ==========================================================
# LOAD COMPONENTS
# ==========================================================

embedding_model = load_embedding_model()
collection = get_chroma_collection()
gemini_client = get_gemini_client()

model_name = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
)


# ==========================================================
# LOAD EXISTING PDF FILES
# ==========================================================

saved_files = list(
    RESOURCE_DIR.glob("*.pdf")
)

for saved_file in saved_files:

    parts = saved_file.name.split(
        "__",
        1
    )

    if len(parts) != 2:
        continue

    file_hash = parts[0]
    original_name = parts[1]

    if not is_file_indexed(
        file_hash,
        collection
    ):

        index_pdf(
            saved_file,
            original_name,
            file_hash,
            embedding_model,
            collection,
            gemini_client,
            model_name
        )


# ==========================================================
# NAVIGATION
# ==========================================================

with st.sidebar:

    st.markdown(
        """
        <h1 style="font-size: 28px;">
            📚 StudyHub
        </h1>
        """,
        unsafe_allow_html=True
    )

    page = st.radio(
        "Navigation",
        [
            "🏠 Dashboard",
            "📂 My Resources",
            "🤖 AI Assistant"
        ],
        label_visibility="collapsed"
    )


# ==========================================================
# GET CURRENT RESOURCES
# ==========================================================

resource_info = get_resource_info(
    collection
)


# ==========================================================
# DASHBOARD
# ==========================================================

if page == "🏠 Dashboard":

    st.title("📚 StudyHub")

    st.write(
        "Organize your study resources and learn with AI."
    )

    st.divider()

    categories = {
        info["category"]
        for info in resource_info.values()
    }

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "📚 Study Resources",
            len(resource_info)
        )

    with col2:

        st.metric(
            "🏷️ Categories",
            len(categories)
        )

    st.divider()

    st.subheader("🆕 Recently Added")

    if resource_info:

        for source, info in list(
            resource_info.items()
        )[:5]:

            with st.container(border=True):

                st.markdown(
                    f"### 📄 {source}"
                )

                st.caption(
                    f"Category: {info['category']}"
                )

    else:

        st.info(
            "You haven't added any study resources yet."
        )

    st.divider()

    st.subheader(
        "🚀 Get Started"
    )

    st.write(
        "Go to **My Resources** to upload your "
        "study materials."
    )


# ==========================================================
# MY RESOURCES
# ==========================================================

elif page == "📂 My Resources":

    st.title("📂 My Resources")

    st.write(
        "Upload, manage, preview, download, "
        "summarize, and delete your study materials."
    )

    st.divider()

    # ------------------------------------------------------
    # UPLOAD
    # ------------------------------------------------------

    st.subheader(
        "➕ Add Study Resources"
    )

    uploaded_files = st.file_uploader(
        "Upload your PDF study materials",
        type=["pdf"],
        accept_multiple_files=True,
        key="resource_uploader"
    )

    current_upload_hashes = set()

    if uploaded_files:

        for uploaded_file in uploaded_files:

            current_upload_hashes.add(
                get_file_hash(
                    uploaded_file.getvalue()
                )
            )

    st.session_state.ignored_upload_hashes = {
        file_hash
        for file_hash in (
            st.session_state.ignored_upload_hashes
        )
        if file_hash in current_upload_hashes
    }

    if uploaded_files:

        for file in uploaded_files:

            file_bytes = file.getvalue()

            file_hash = get_file_hash(
                file_bytes
            )

            if file_hash in (
                st.session_state.ignored_upload_hashes
            ):
                continue

            storage_path = get_storage_path(
                file_hash,
                file.name
            )

            if not storage_path.exists():

                storage_path.write_bytes(
                    file_bytes
                )

            if not is_file_indexed(
                file_hash,
                collection
            ):

                with st.spinner(
                    f"Processing {file.name}..."
                ):

                    (
                        success,
                        _chunks,
                        category
                    ) = index_pdf(
                        storage_path,
                        file.name,
                        file_hash,
                        embedding_model,
                        collection,
                        gemini_client,
                        model_name
                    )

                if success:

                    st.success(
                        f"{file.name} added successfully."
                    )

                    st.info(
                        f"Category: {category}"
                    )

            else:

                st.success(
                    f"{file.name} is already in your resources."
                )

        resource_info = get_resource_info(
            collection
        )

    st.divider()

    # ------------------------------------------------------
    # FILTER
    # ------------------------------------------------------

    st.subheader(
        "📚 Your Study Library"
    )

    selected_category = st.selectbox(
        "Filter by category",
        ["All Resources"] + CATEGORIES,
        key="resource_category_filter"
    )

    filtered_resources = {}

    for source, info in resource_info.items():

        if (
            selected_category == "All Resources"
            or info["category"] == selected_category
        ):

            filtered_resources[source] = info

    st.divider()

    # ------------------------------------------------------
    # RESOURCE CARDS
    # ------------------------------------------------------

    if filtered_resources:

        for source, info in (
            filtered_resources.items()
        ):

            with st.container(border=True):

                st.markdown(
                    f"### 📄 {source}"
                )

                st.caption(
                    f"🏷️ {info['category']}"
                )

                col1, col2, col3 = st.columns(3)

                with col1:

                    if st.button(
                        "👀 Preview",
                        key=f"preview_{info['file_hash']}",
                        use_container_width=True
                    ):

                        preview_results = collection.get(
                            where={
                                "file_hash": info[
                                    "file_hash"
                                ]
                            },
                            include=["documents"]
                        )

                        documents = (
                            preview_results.get(
                                "documents",
                                []
                            )
                        )

                        if documents:

                            preview_text = (
                                "\n\n".join(
                                    documents
                                )
                            )

                            st.text_area(
                                "Preview",
                                preview_text[:5000],
                                height=250,
                                key=f"preview_text_{info['file_hash']}"
                            )

                with col2:

                    file_path = (
                        RESOURCE_DIR
                        / info["stored_filename"]
                    )

                    if file_path.exists():

                        st.download_button(
                            label="⬇️ Download",
                            data=file_path.read_bytes(),
                            file_name=source,
                            mime="application/pdf",
                            use_container_width=True,
                            key=f"download_{info['file_hash']}"
                        )

                with col3:

                    if st.button(
                        "🗑️ Delete",
                        key=f"delete_{info['file_hash']}",
                        use_container_width=True
                    ):

                        delete_resource(
                            info["file_hash"],
                            info["stored_filename"],
                            collection
                        )

                        st.session_state.ignored_upload_hashes.add(
                            info["file_hash"]
                        )

                        st.success(
                            f"{source} deleted."
                        )

                        st.rerun()

    else:

        st.info(
            "No study resources found."
        )

    st.divider()

    # ------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------

    st.subheader(
        "📝 AI Resource Summary"
    )

    available_sources = list(
        filtered_resources.keys()
    )

    if available_sources:

        selected_resource = st.selectbox(
            "Choose a resource",
            available_sources,
            key="summary_resource"
        )

        if st.button(
            "✨ Generate AI Summary",
            use_container_width=True
        ):

            if gemini_client is None:

                st.error(
                    "Gemini API key not found."
                )

            else:

                with st.spinner(
                    "Creating your study summary..."
                ):

                    summary = (
                        generate_resource_summary(
                            selected_resource,
                            collection,
                            gemini_client,
                            model_name
                        )
                    )

                if summary:

                    st.markdown(summary)

    else:

        st.info(
            "Add a resource to generate a summary."
        )


# ==========================================================
# AI ASSISTANT
# ==========================================================

elif page == "🤖 AI Assistant":

    st.title("🤖 AI Study Assistant")

    st.write(
        "Ask questions about your uploaded study resources."
    )

    st.divider()

    selected_category = st.selectbox(
        "Search in",
        ["All Resources"] + CATEGORIES,
        key="ai_category_filter"
    )

    question = st.text_input(
        "Ask a question",
        placeholder=(
            "Example: What are the benefits "
            "of augmented reality?"
        )
    )

    if question:

        if gemini_client is None:

            st.error(
                "Gemini API key not found. "
                "Add GEMINI_API_KEY to your .env file."
            )

        elif collection.count() == 0:

            st.warning(
                "Please upload a study resource first."
            )

        else:

            documents, metadatas = search_resources(
                question,
                embedding_model,
                collection,
                selected_category,
                number_of_results=3
            )

            if not documents:

                st.warning(
                    "No relevant study resources were found."
                )

            else:

                with st.spinner(
                    "Finding the answer..."
                ):

                    answer = generate_answer(
                        question,
                        documents,
                        gemini_client,
                        model_name
                    )

                st.subheader(
                    "🤖 Answer"
                )

                st.write(answer)

                st.divider()

                st.subheader(
                    "📚 Sources"
                )

                shown_sources = set()

                for metadata in metadatas:

                    source = metadata["source"]

                    if source not in shown_sources:

                        st.write(
                            f"📄 {source}"
                        )

                        shown_sources.add(
                            source
                        )