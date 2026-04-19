"""
Authentication Dependencies for FastAPI
Provides user authentication and authorization middleware
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import structlog
from google.cloud import firestore

from config import settings
from memory.firestore_client import get_firestore_client

logger = structlog.get_logger()

# Security scheme
security = HTTPBearer(auto_error=False)


def create_access_token(user_id: str, email: str, extra_data: Optional[dict] = None) -> str:
    """
    Create a JWT access token for a user.
    
    Args:
        user_id: Unique user identifier
        email: User's email address
        extra_data: Additional claims to include
        
    Returns:
        Encoded JWT token
    """
    expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
    
    to_encode = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    if extra_data:
        to_encode.update(extra_data)
    
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.warning("Token verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    Get current authenticated user from request.
    
    This dependency extracts and validates the JWT token,
    then returns the user information.
    
    Args:
        request: FastAPI request object
        credentials: Bearer token credentials
        
    Returns:
        Dict containing user_id, email, and other token claims
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    payload = verify_token(credentials.credentials)
    
    return {
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
        "exp": payload.get("exp"),
        **{k: v for k, v in payload.items() if k not in ["sub", "email", "exp", "iat", "type"]}
    }


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Get current user if authenticated, None otherwise.
    
    Use this for endpoints that work both authenticated and unauthenticated.
    """
    if not credentials:
        return None
    
    try:
        payload = verify_token(credentials.credentials)
        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
        }
    except HTTPException:
        return None


def require_auth(user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency that requires authentication.
    
    Use this as a shorthand for routes that require auth:
        @app.get("/protected", dependencies=[Depends(require_auth)])
    """
    return user


class RateLimiter:
    """Firestore-backed rate limiter with in-memory fallback."""
    
    def __init__(self, requests: int = 100, window_seconds: int = 60):
        self.requests = requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[datetime]] = {}
        self._firestore = get_firestore_client()

    async def _check_distributed(self, user_id: str) -> bool:
        """Check rate limit across instances using Firestore atomic increment."""
        now = datetime.utcnow()
        window_id = int(now.timestamp()) // self.window_seconds
        doc_id = f"{user_id}:{window_id}"

        doc_ref = (
            self._firestore.async_db
            .collection(settings.firestore_collection_rate_limits)
            .document(doc_id)
        )

        # Atomic increment to avoid race conditions across multiple instances.
        await doc_ref.set(
            {
                "user_id": user_id,
                "window_id": window_id,
                "window_start": (window_id * self.window_seconds),
                "expires_at": (now + timedelta(seconds=(self.window_seconds * 2))).isoformat(),
                "count": firestore.Increment(1),
            },
            merge=True,
        )

        doc = await doc_ref.get()
        if not doc.exists:
            return True

        data = doc.to_dict() or {}
        count = int(data.get("count", 0))
        return count <= self.requests

    async def _check_in_memory(self, user_id: str) -> bool:
        """Fallback limiter used if Firestore is unavailable."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        if user_id not in self._requests:
            self._requests[user_id] = []

        self._requests[user_id] = [
            req_time for req_time in self._requests[user_id]
            if req_time > window_start
        ]

        if len(self._requests[user_id]) >= self.requests:
            return False

        self._requests[user_id].append(now)
        return True
    
    async def check(self, user_id: str) -> bool:
        """Check if user is within rate limit."""
        try:
            return await self._check_distributed(user_id)
        except Exception as exc:
            logger.warning("Distributed rate limiting unavailable, using in-memory fallback", error=str(exc))
            return await self._check_in_memory(user_id)


# Global rate limiter instance
rate_limiter = RateLimiter(
    requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds
)


async def check_rate_limit(user: dict = Depends(get_current_user)):
    """Dependency to check rate limit for authenticated user."""
    if not await rate_limiter.check(user["user_id"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    return user
