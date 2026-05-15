import os
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-min-32-chars!!")
os.environ.setdefault("ADMIN_PASSWORD", "testadmin")

pytest_plugins = ["pytest_asyncio"]
