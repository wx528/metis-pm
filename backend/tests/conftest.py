import os
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-min-32-chars!!")
os.environ.setdefault("ADMIN_PASSWORD_HASH", "REDACTED-Bcrypt-HASH6MpcMDywNJeE8zLpdpP6Dw3lmbPaBhGwfgJQdWR0oe")
os.environ.setdefault("AGENT_PASSWORDS_JSON", '{"testagent": {"password_hash": "REDACTED-Bcrypt-HASHaBoAA4A9XoexRMqI1PDYodJLzw0B49QA.TnkAWxdNi", "role": "agent"}}')
os.environ.setdefault("ENCRYPTION_KEY", "REDACTED-FERNET-KEY=")

pytest_plugins = ["pytest_asyncio"]
