from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "project_manager"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./project_manager.db"
    SECRET_KEY: str = ""
    ADMIN_PASSWORD: str = ""
    CORS_ORIGINS: str = "http://localhost:5173"

    def model_post_init(self, __context):
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY must be set in .env file")
        if not self.ADMIN_PASSWORD:
            raise ValueError("ADMIN_PASSWORD must be set in .env file")


settings = Settings()
