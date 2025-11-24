# backend/rag/retrieve.py
import shutil
from pathlib import Path
from typing import List
import logging
from langchain_core.documents import Document
from langchain.schema import Document
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter

from config import config

logger = logging.getLogger(__name__)

# Shared embedding model (reused across requests)
embeddings = VertexAIEmbeddings(
    model_name=config.VERTEX_AI_EMBEDDING_MODEL,
    project=config.VERTEX_AI_PROJECT,
    location=config.VERTEX_AI_LOCATION,
)

# Per-session FAISS databases stored on disk
SESSION_DB_ROOT = config.SESSION_DB_PATH  # ← from config.py (rag/vector_db/session_faiss)
SESSION_DB_ROOT.mkdir(parents=True, exist_ok=True)


def _session_db_path(session_id: str) -> str:
    return str(SESSION_DB_ROOT / f"session_{session_id}")


def build_session_vectorstore(session_id: str, markdown_content: str) -> None:
    """
    Called ONCE per WhatsApp user when they say their city.
    Builds a private FAISS index just for them.
    """
    session_path = _session_db_path(session_id)

    # Remove old session if exists (fresh start)
    if Path(session_path).exists():
        shutil.rmtree(session_path)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100,
        separators=["\n### ", "\n## ", "\n- ", "\n\n", "\n"],
        keep_separator=True,
    )

    chunks = splitter.split_text(markdown_content)

    documents = [
        Document(
            page_content=chunk.strip(),
            metadata={
                "source": f"osm_session_{session_id}",
                "chunk_id": i,
                "session_id": session_id,
            },
        )
        for i, chunk in enumerate(chunks)
    ]

    logger.info(f"Building session FAISS index → {session_id[:12]} | {len(documents)} chunks")

    # This one line does everything your old code did manually
    db = FAISS.from_documents(documents, embeddings)
    db.save_local(session_path)

    logger.info(f"Session vectorstore ready → {Path(session_path).name}")


def search_relevant_chunks(session_id: str, query: str, k: int = 6) -> List[Document]:
    """
    Main function used by the graph.
    Returns top-k relevant chunks for the user's private knowledge base.
    """
    session_path = _session_db_path(session_id)

    if not Path(session_path).exists():
        logger.warning(f"No vectorstore for session {session_id[:12]}")
        return [
            Document(page_content="No local information available yet. Go to the main train station or look for Red Cross/UNHCR tents.")
        ]

    try:
        db = FAISS.load_local(
            folder_path=session_path,
            embeddings=embeddings,
            allow_dangerous_deserialization=True,
        )
        retriever = db.as_retriever(search_kwargs={"k": k})
        docs = retriever.invoke(query)
        logger.info(f"RAG → {session_id[:12]} | Retrieved {len(docs)} chunks")
        return docs
    except Exception as e:
        logger.error(f"RAG search failed for {session_id[:12]}: {e}")
        return [Document(page_content="Sorry, I couldn't access local information right now.")]


def cleanup_old_sessions(max_age_hours: int = 72):
    """Optional: run daily to clean up old sessions"""
    import time
    now = time.time()
    for session_dir in SESSION_DB_ROOT.iterdir():
        if session_dir.is_dir() and session_dir.name.startswith("session_"):
            age = now - session_dir.stat().st_mtime
            if age > max_age_hours * 3600:
                shutil.rmtree(session_dir)
                logger.info(f"Cleaned old session: {session_dir.name}")