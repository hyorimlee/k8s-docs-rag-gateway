"""Basic application configuration."""

from os import getenv
from pathlib import Path

APP_NAME = getenv("APP_NAME", "k8s-docs-rag-gateway")
APP_ENV = getenv("APP_ENV", "local")
APP_VERSION = getenv("APP_VERSION", "0.1.0")
CHUNKS_PATH = Path(getenv("CHUNKS_PATH", "artifacts/chunks.jsonl"))
CHROMA_PERSIST_DIRECTORY = Path(getenv("CHROMA_PERSIST_DIRECTORY", "artifacts/chroma"))
PROVIDER_TIMEOUT_SECONDS = float(getenv("PROVIDER_TIMEOUT_SECONDS", "5"))
