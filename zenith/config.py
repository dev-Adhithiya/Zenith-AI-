"""
Zenith AI Configuration
Multi-tenant Personal Assistant with GCP Integration
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # GCP Configuration
    gcp_project_id: str = Field(..., env="GCP_PROJECT_ID")
    gcp_region: str = Field(default="us-central1", env="GCP_REGION")
    
    # OAuth 2.0 Configuration
    google_client_id: str = Field(..., env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    oauth_redirect_uri: str = Field(
        default="http://localhost:8000/auth/callback",
        env="OAUTH_REDIRECT_URI"
    )
    
    # Firestore Configuration
    firestore_collection_users: str = "users"
    firestore_collection_conversations: str = "conversations"
    firestore_collection_notes: str = "notes"
    
    # Vertex AI Configuration
    vertex_ai_model: str = Field(
        default="gemini-2.5-flash",
        env="VERTEX_AI_MODEL"
    )
    vertex_ai_location: str = Field(
        default="us-central1",
        env="VERTEX_AI_LOCATION"
    )
    
    # JWT Configuration for Session Management
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # Application Settings
    app_name: str = "Zenith AI"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    
    # Google API Scopes
    @property
    def google_scopes(self) -> list[str]:
        return [
            "openid",  # Required - Google always returns this
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/tasks",
            "https://www.googleapis.com/auth/drive",  # For syncing notes to Google Drive
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


# Convenience export
settings = get_settings()
