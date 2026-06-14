import os
import bcrypt
import pytest

_secret_key = "test-secret-key-for-pytest-min-32-chars!!"
_admin_hash = bcrypt.hashpw(b"test-admin-password", bcrypt.gensalt()).decode()
_agent_hash = bcrypt.hashpw(b"test-agent-password", bcrypt.gensalt()).decode()
_encryption_key = "REDACTED-FERNET-KEY="

os.environ.setdefault("SECRET_KEY", _secret_key)
os.environ.setdefault("ADMIN_PASSWORD_HASH", _admin_hash)
os.environ.setdefault("AGENT_PASSWORDS_JSON", f'{{"testagent": {{"password_hash": "{_agent_hash}", "role": "agent"}}}}')
os.environ.setdefault("ENCRYPTION_KEY", _encryption_key)

pytest_plugins = ["pytest_asyncio"]
