import os

# Importing the referentiel pulls in the LLM client, which refuses to load
# without these settings. No test here calls the LLM.
os.environ.setdefault("LLM_BASE_URL", "http://llm.invalid/v1")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_MODEL", "test")
# mathutrice.database builds its engine at import time; tests use their own.
os.environ.setdefault("DATABASE_URL", "sqlite://")
