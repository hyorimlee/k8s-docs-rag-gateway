"""Basic application configuration."""

from os import getenv

APP_NAME = getenv("APP_NAME", "k8s-docs-rag-gateway")
APP_ENV = getenv("APP_ENV", "local")
APP_VERSION = getenv("APP_VERSION", "0.1.0")
