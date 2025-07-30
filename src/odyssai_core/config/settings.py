import os
from dotenv import load_dotenv
from .paths import SECRET_DIR

load_dotenv()

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Google Cloud Text-to-Speech configuration
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(SECRET_DIR / "google_tts.json")

# Hugging Face
HF_API_KEY = os.getenv("HF_API_KEY")

# Pinecone
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# LangSmith
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")

# SerpAPI
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# ChromaDB Cloud
CHROMA_API_KEY = os.getenv("CHROMA_API_KEY")
CHROMA_TENANT = os.getenv("CHROMA_TENANT")
CHROMA_DATABASE = os.getenv("CHROMA_DATABASE")
