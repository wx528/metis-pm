import os
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-min-32-chars!!")
os.environ.setdefault("ADMIN_PASSWORD", "testadmin")
os.environ.setdefault("AGENT_PASSWORDS", "testagent:agentpass")
os.environ.setdefault("ENCRYPTION_KEY", "REDACTED-FERNET-KEY=")

pytest_plugins = ["pytest_asyncio"]
