"""
Google OAuth 2.0 Authentication Manager
Handles multi-tenant user authentication with Google Workspace APIs
"""
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from functools import lru_cache

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import httpx
import structlog

from config import settings
from memory.firestore_client import get_firestore_client

logger = structlog.get_logger()

# In-memory fallback cache for PKCE code verifiers (state -> code_verifier)
_code_verifier_cache: dict[str, str] = {}


def _state_fingerprint(state: str) -> str:
    """Short stable id for logs (never log raw OAuth state)."""
    return hashlib.sha256(state.encode("utf-8")).hexdigest()[:16]


class GoogleOAuthManager:
    """Manages Google OAuth 2.0 authentication flow for multi-tenant users."""
    
    def __init__(self):
        self.firestore = get_firestore_client()
        self.client_config = {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.oauth_redirect_uri],
            }
        }
        self.scopes = settings.google_scopes

    async def _store_code_verifier(self, state: str, code_verifier: str) -> None:
        """Store PKCE verifier with TTL in Firestore, fallback to memory."""
        data = {
            "code_verifier": code_verifier,
            "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
        }
        try:
            await self.firestore.set_document(
                collection=settings.firestore_collection_auth_state,
                document_id=state,
                data=data,
                merge=True,
            )
        except Exception as exc:
            logger.warning("Failed to store PKCE verifier in Firestore, using memory fallback", error=str(exc))
            _code_verifier_cache[state] = code_verifier

    async def _pop_code_verifier(self, state: str) -> Optional[str]:
        """Read and delete PKCE verifier, preferring Firestore over memory fallback."""
        try:
            auth_state = await self.firestore.get_document(
                collection=settings.firestore_collection_auth_state,
                document_id=state,
            )
            if auth_state:
                expires_at_raw = auth_state.get("expires_at")
                if expires_at_raw:
                    expires_at = datetime.fromisoformat(expires_at_raw)
                    if expires_at < datetime.utcnow():
                        await self.firestore.delete_document(
                            collection=settings.firestore_collection_auth_state,
                            document_id=state,
                        )
                        return None

                code_verifier = auth_state.get("code_verifier")
                await self.firestore.delete_document(
                    collection=settings.firestore_collection_auth_state,
                    document_id=state,
                )
                return code_verifier
        except Exception as exc:
            logger.warning("Failed reading PKCE verifier from Firestore, using memory fallback", error=str(exc))

        return _code_verifier_cache.pop(state, None)
    
    async def create_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """
        Create OAuth authorization URL for user login.
        
        Returns:
            Tuple of (authorization_url, state)
        """
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.scopes,
            redirect_uri=settings.oauth_redirect_uri
        )
        
        # Generate PKCE code verifier manually to ensure it's always present
        import secrets
        import hashlib
        import base64
        
        # Generate code verifier (43-128 chars of URL-safe base64)
        code_verifier = secrets.token_urlsafe(32)
        
        # Generate code challenge (S256 = SHA256 hash, base64-url encoded)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        
        authorization_url, state = flow.authorization_url(
            access_type="offline",  # Get refresh token
            include_granted_scopes="true",
            prompt="consent",  # Force consent to ensure refresh token
            state=state,
            code_challenge=code_challenge,
            code_challenge_method='S256'
        )
        
        # Store code verifier for callback (PKCE requirement)
        await self._store_code_verifier(state=state, code_verifier=code_verifier)
        logger.info("stored_pkce_verifier", state_fp=_state_fingerprint(state))

        logger.info("created_oauth_authorization_url", state_fp=_state_fingerprint(state))
        return authorization_url, state
    
    async def exchange_code_for_tokens(self, code: str, state: Optional[str] = None) -> dict:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from OAuth callback
            state: OAuth state parameter (used to retrieve stored code verifier)
            
        Returns:
            Dict containing credentials and user info
        """
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.scopes,
            redirect_uri=settings.oauth_redirect_uri
        )
        
        # Retrieve and restore PKCE code verifier
        code_verifier = await self._pop_code_verifier(state=state or "") if state else None
        if code_verifier:
            flow.code_verifier = code_verifier
            logger.info("retrieved_pkce_verifier", state_fp=_state_fingerprint(state or ""))
        else:
            logger.warning("pkce_verifier_missing", state_fp=_state_fingerprint(state or ""))
            raise ValueError(f"PKCE code verifier not found for state: {state}. This may happen if the server was restarted. Please try logging in again.")
        
        # Exchange code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get user info
        user_info = await self._get_user_info(credentials)
        
        logger.info("Exchanged code for tokens", user_email=user_info.get("email"))
        
        return {
            "credentials": self._credentials_to_dict(credentials),
            "user_info": user_info
        }
    
    async def _get_user_info(self, credentials: Credentials) -> dict:
        """Fetch user info from Google."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {credentials.token}"}
            )
            response.raise_for_status()
            return response.json()
    
    def refresh_credentials(self, credentials_dict: dict) -> dict:
        """
        Refresh expired credentials using refresh token.
        
        Args:
            credentials_dict: Dictionary containing credential data
            
        Returns:
            Updated credentials dictionary
        """
        credentials = self._dict_to_credentials(credentials_dict)
        
        if credentials.expired and credentials.refresh_token:
            logger.info("Refreshing expired credentials")
            credentials.refresh(Request())
            return self._credentials_to_dict(credentials)
        
        return credentials_dict
    
    def get_credentials(self, credentials_dict: dict) -> Credentials:
        """
        Get Credentials object from dictionary, refreshing if needed.
        
        Args:
            credentials_dict: Dictionary containing credential data
            
        Returns:
            Valid Credentials object
        """
        credentials = self._dict_to_credentials(credentials_dict)
        
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        
        return credentials
    
    def _credentials_to_dict(self, credentials: Credentials) -> dict:
        """Convert Credentials object to dictionary for storage."""
        return {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes) if credentials.scopes else [],
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None
        }
    
    def _dict_to_credentials(self, credentials_dict: dict) -> Credentials:
        """Convert dictionary to Credentials object."""
        expiry = None
        if credentials_dict.get("expiry"):
            expiry = datetime.fromisoformat(credentials_dict["expiry"])
        
        return Credentials(
            token=credentials_dict["token"],
            refresh_token=credentials_dict.get("refresh_token"),
            token_uri=credentials_dict.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=credentials_dict.get("client_id", settings.google_client_id),
            client_secret=credentials_dict.get("client_secret", settings.google_client_secret),
            scopes=credentials_dict.get("scopes", self.scopes),
            expiry=expiry
        )
    
    def build_service(self, service_name: str, version: str, credentials_dict: dict):
        """
        Build a Google API service client.
        
        Args:
            service_name: Name of the service (e.g., 'calendar', 'gmail')
            version: API version (e.g., 'v3', 'v1')
            credentials_dict: User's stored credentials
            
        Returns:
            Google API service client
        """
        credentials = self.get_credentials(credentials_dict)
        return build(service_name, version, credentials=credentials)


@lru_cache()
def get_oauth_manager() -> GoogleOAuthManager:
    """Get cached OAuth manager instance."""
    return GoogleOAuthManager()
