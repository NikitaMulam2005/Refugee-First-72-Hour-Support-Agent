import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Core
    ENV = os.getenv("ENVIRONMENT", "development")
    DEBUG = ENV == "development"

    # GroQ (you installed it → we use it)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # REQUIRED
    PUBLIC_URL = os.getenv("PUBLIC_URL")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "refugee_first_2025_k9x!mPvL2qW8zR4tY6uIoP0aSdF3gH5jK7lZxC1vB9nM8eU2wQ6rT4yI")

    # Vertex AI Embeddings
    VERTEX_AI_PROJECT = os.getenv("VERTEX_AI_PROJECT")
    VERTEX_AI_LOCATION = os.getenv("VERTEX_AI_LOCATION", "us-central1")
    VERTEX_AI_EMBEDDING_MODEL = "text-embedding-004"

    # Twilio WhatsApp
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

    # Paths
    BASE_DIR = Path(__file__).resolve().parent
    VECTOR_DB_PATH = BASE_DIR / "rag" / "vector_db"
    PDF_OUTPUT_PATH = BASE_DIR / "downloads"
    KNOWLEDGE_PATH = BASE_DIR / "knowledge"
    SESSION_DB_PATH = VECTOR_DB_PATH / "session_faiss"

    VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)
    PDF_OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_PATH.mkdir(parents=True, exist_ok=True)
    SESSION_DB_PATH.mkdir(parents=True, exist_ok=True)
    # Server
    HOST = "0.0.0.0"
    PORT = 8000

config = Config()