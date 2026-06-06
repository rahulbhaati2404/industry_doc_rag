from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Enterprise_Document_RAG"
    APP_VERSION: str = "1.0.0"

    LOG_LEVEL: str = "INFO"

    API_V1_STR: str = "/api/v1"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL: str = "mistral"
    OLLAMA_LIGHT_MODEL: str = "llama3.2:1b"

    HF_EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    HF_RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    HF_HALLUCINATION_MODEL: str = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"

    MODEL_TIMEOUT: int = 120
    MODEL_MAX_RETRIES: int = 3

    VECTOR_STORE: str = "chroma"
    CHROMA_PERSIST_DIR: str = "./data/vectorstore"
    CHROMA_COLLECTION_NAME: str = "Enterprise_documents"
    VECTOR_STORE_BATCH_SIZE: int = 100

    DOCUMENT_SOURCE_PATH: str = "./data/raw"
    PROCESSED_DOCS_PATH: str = "./data/processed/chunks"
    EMBEDDED_DOCS_PATH: str = "./data/processed/embeddings"
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 300
    EMBEDDING_BATCH_SIZE: int = 32

    TOP_K_RETRIEVAL: int = 5
    RERANK_TOP_K: int = 3

    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 3600
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_BACKEND: str = "memory"

    MAX_INPUT_TOKENS: int = 10000
    ENABLE_PROMPT_INJECTION_DETECTION: bool = True
    ENABLE_PII_MASKING: bool = True
    ENABLE_TOXICITY_FILTER: bool = True

    HALLUCINATION_THRESHOLD: float = 0.75
    MAX_REGENERATION_ATTEMPTS: int = 2

    SESSION_TTL_MINUTES: int = 60
    MEMORY_WINDOW_SIZE: int = 6
    MAX_MEMORY_TOKENS: int = 1500
    ENABLE_CONVERSATION_SUMMARY: bool = True

    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "smart-rag-platform"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
