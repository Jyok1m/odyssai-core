from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from odyssai_core.constants.llm_models import EMBEDDING_MODEL

def get_embeddings_model():
    """
    Fallback function to output the appropriate embeddings model
    """
    try:
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        # return OpenAIEmbeddings(model=EMBEDDING_MODEL)
    except Exception:
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
