# StudyHub — AI-Powered Study Resource Organizer

StudyHub is an AI-powered web application that helps students organize, search, summarize, and understand their study resources.

Users can upload PDF study materials, automatically categorize them, search their content using semantic search, generate AI-powered summaries, and ask questions based only on their uploaded resources.

---

## Features

### 📚 Resource Management
- Upload PDF study materials
- Persistent resource storage
- Automatic resource categorization
- Search resources by name or category
- Filter resources by category
- Preview PDFs directly in the browser
- Download uploaded resources
- Delete individual resources
- Clear all resources

### ✨ AI Assistant
- Ask questions about uploaded study materials
- Search across all uploaded resources
- Search within a specific PDF
- Answers are generated using retrieved study material
- Source files are displayed with AI answers
- Chat history during the current session
- Clear question and clear chat controls

### 📝 AI Summaries
- Generate summaries for uploaded PDFs
- Important concepts are highlighted
- Student-friendly formatting
- Summaries are based only on the selected resource

---

## How It Works

StudyHub uses a Retrieval-Augmented Generation (RAG) workflow.

```text
PDF Upload
    ↓
Text Extraction
    ↓
Text Cleaning
    ↓
Text Chunking
    ↓
Sentence Embeddings
    ↓
ChromaDB Vector Storage
    ↓
Semantic Search
    ↓
Relevant Study Material
    ↓
Gemini AI
    ↓
Answer / Summary