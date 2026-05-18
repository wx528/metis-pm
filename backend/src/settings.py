from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "project_manager"
    APP_VERSION: str = "0.4.0"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./project_manager.db"
    SECRET_KEY: str = ""
    ADMIN_PASSWORD: str = ""
    CORS_ORIGINS: str = "http://localhost:5173"
    AGENT_PASSWORDS: str = ""
    ENCRYPTION_KEY: str = ""  # Fernet key, generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    @property
    def agent_password_map(self) -> dict[str, str]:
        result = {}
        if not self.AGENT_PASSWORDS:
            return result
        for entry in self.AGENT_PASSWORDS.split(","):
            entry = entry.strip()
            if ":" in entry:
                name, pwd = entry.split(":", 1)
                result[name.strip()] = pwd.strip()
        return result

    def resolve_identity(self, password: str) -> tuple[str, str] | None:
        if password == self.ADMIN_PASSWORD:
            return ("admin", "admin")
        for name, pwd in self.agent_password_map.items():
            if password == pwd:
                return (name, "agent")
        return None

    def model_post_init(self, __context):
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY must be set in .env file")
        if not self.ADMIN_PASSWORD:
            raise ValueError("ADMIN_PASSWORD must be set in .env file")


settings = Settings()
