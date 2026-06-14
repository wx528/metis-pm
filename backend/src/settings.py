import json
import bcrypt
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "metis_pm"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./metis_pm.db"
    SECRET_KEY: str = ""
    ADMIN_PASSWORD_HASH: str = ""
    CORS_ORIGINS: str = "http://localhost:5173"
    AGENT_PASSWORDS_JSON: str = ""
    ENCRYPTION_KEY: str = ""

    @property
    def agent_password_map(self) -> dict[str, tuple[str, str]]:
        """解析 JSON 格式的 Agent 密码配置
        
        格式: '{"agent1": {"password_hash": "...", "role": "agent"}, ...}'
        或旧格式兼容: 'name:password:role,name2:password2:role2'
        """
        result = {}
        if not self.AGENT_PASSWORDS_JSON:
            return result
        
        # 尝试 JSON 格式
        try:
            data = json.loads(self.AGENT_PASSWORDS_JSON)
            for name, config in data.items():
                if isinstance(config, dict):
                    pwd_hash = config.get("password_hash", "")
                    role = config.get("role", "agent")
                    result[name] = (pwd_hash, role)
                elif isinstance(config, str):
                    # 简单字符串格式: {"name": "password_hash"}
                    result[name] = (config, "agent")
            return result
        except json.JSONDecodeError:
            pass
        
        # 兼容旧格式: name:password:role,name2:password2:role2
        for entry in self.AGENT_PASSWORDS_JSON.split(","):
            entry = entry.strip()
            if ":" in entry:
                parts = entry.split(":")
                name = parts[0].strip()
                pwd = parts[1].strip()
                role = parts[2].strip() if len(parts) > 2 else "agent"
                result[name] = (pwd, role)
        return result

    def resolve_identity(self, password: str) -> tuple[str, str] | None:
        """验证密码并返回身份 (sub, role)"""
        # 验证 admin 密码
        if self.ADMIN_PASSWORD_HASH and bcrypt.checkpw(
            password.encode(), self.ADMIN_PASSWORD_HASH.encode()
        ):
            return ("admin", "admin")
        
        # 验证 agent 密码
        for name, (pwd_hash, role) in self.agent_password_map.items():
            if pwd_hash.startswith("$2b$") or pwd_hash.startswith("$2a$"):
                if bcrypt.checkpw(password.encode(), pwd_hash.encode()):
                    return (name, role)
        return None

    def model_post_init(self, __context):
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY must be set in .env file")
        if not self.ADMIN_PASSWORD_HASH:
            raise ValueError(
                "ADMIN_PASSWORD_HASH must be set in .env file.\n"
                "Migration steps:\n"
                "  1. Generate bcrypt hash: python -c \"import bcrypt; print(bcrypt.hashpw('your_password'.encode(), bcrypt.gensalt()).decode())\"\n"
                "  2. Add to .env: ADMIN_PASSWORD_HASH=$2b$12$... (the output from step 1)\n"
                "  3. Remove old ADMIN_PASSWORD if present (no longer used)"
            )


settings = Settings()
