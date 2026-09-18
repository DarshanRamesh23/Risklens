from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://risklens:risklens@localhost:5432/risklens"
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db_name: str = "risklens_docs"

    gemini_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"

    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 200
    retrieval_top_k: int = 5

    ml_model_path: str = "ml/model.pkl"

    class Config:
        env_file = ".env"


settings = Settings()