from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/tradelens"
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    ai_provider: str = "openai"  # openai | claude | deepseek | openrouter
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    ai_base_url: str = Field(default="", alias="BASE_URL")
    ai_model: str = Field(default="", alias="MODEL")

    class Config:
        env_file = ".env"
        populate_by_name = True


settings = Settings()
