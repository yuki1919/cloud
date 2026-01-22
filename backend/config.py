from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ppt-agent"
    openai_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")
    model_name: str = Field(default="deepseek-ai/DeepSeek-V3.2", env="MODEL_NAME")
    llm_base_url: str = Field(
        default="https://api.siliconflow.cn/v1/chat/completions", env="LLM_BASE_URL"
    )
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", env="EMBEDDING_MODEL"
    )
    data_dir: Path = Field(default=Path("data"), env="DATA_DIR")
    faiss_path: Path = Field(default=Path("data/faiss.index"), env="FAISS_PATH")
    top_k: int = Field(default=4, env="TOP_K")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        # 避免 pydantic 对字段名 model_* 的保留保护
        "protected_namespaces": ("settings_",),
    }


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
