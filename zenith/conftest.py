"""Pytest defaults: required environment variables before importing the app."""
import os

# Must run before `main` / `config` import so pydantic-settings sees these values.
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "unit-test-jwt-secret-key-do-not-use-in-production-32b",
)
