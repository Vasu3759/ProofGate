from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./proofgate.db"
    demo_mode: bool = False
    frontend_origin: str = "http://localhost:3000"
    gemini_api_key: str | None = None
    ai_model_name: str = "gemini-2.5-flash"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
