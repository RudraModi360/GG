"""
GearGuard Backend - Security Module
Handles JWT token generation, password hashing, and authentication utilities.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel
import ulid
import logging

from app.config import settings

logger = logging.getLogger(__name__)


# ===========================================
# Token Models
# ===========================================

class TokenPayload(BaseModel):
    """Access token payload structure."""
    sub: str  # user_id
    email: str
    org_id: str
    role: str
    permissions: list[str]
    type: str = "access"
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None


class RefreshTokenPayload(BaseModel):
    """Refresh token payload structure."""
    sub: str  # user_id
    session_id: str
    type: str = "refresh"
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


# ===========================================
# Password Functions
# ===========================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The bcrypt hash to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        # bcrypt requires bytes
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Bcrypt hash of the password
    """
    # bcrypt returns bytes, we need string for storage
    return bcrypt.hashpw(
        password.encode('utf-8'), 
        bcrypt.gensalt()
    ).decode('utf-8')


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets minimum security requirements.
    
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character"
    
    return True, ""


# ===========================================
# JWT Token Functions
# ===========================================

def create_access_token(
    user_id: str,
    email: str,
    org_id: str,
    role: str,
    permissions: list[str],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a new JWT access token.
    
    Args:
        user_id: User's unique identifier
        email: User's email address
        org_id: User's organization ID
        role: User's role name
        permissions: List of permission strings
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT access token
    """
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    
    payload = {
        "sub": user_id,
        "email": email,
        "org_id": org_id,
        "role": role,
        "permissions": permissions,
        "type": "access",
        "exp": expire,
        "iat": now,
    }
    
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token(
    user_id: str,
    session_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> tuple[str, str]:
    """
    Create a new JWT refresh token.
    
    Args:
        user_id: User's unique identifier
        session_id: Optional session ID, generated if not provided
        expires_delta: Optional custom expiration time
        
    Returns:
        Tuple of (refresh_token, session_id)
    """
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    
    if session_id is None:
        session_id = generate_id()
    
    payload = {
        "sub": user_id,
        "session_id": session_id,
        "type": "refresh",
        "exp": expire,
        "iat": now,
    }
    
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return token, session_id


def create_token_pair(
    user_id: str,
    email: str,
    org_id: str,
    role: str,
    permissions: list[str]
) -> tuple[TokenPair, str]:
    """
    Create both access and refresh tokens.
    
    Args:
        user_id: User's unique identifier
        email: User's email address
        org_id: User's organization ID
        role: User's role name
        permissions: List of permission strings
        
    Returns:
        Tuple of (TokenPair, session_id)
    """
    access_token = create_access_token(
        user_id=user_id,
        email=email,
        org_id=org_id,
        role=role,
        permissions=permissions
    )
    
    refresh_token, session_id = create_refresh_token(user_id=user_id)
    
    token_pair = TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return token_pair, session_id


def decode_access_token(token: str) -> Optional[TokenPayload]:
    """
    Decode and validate an access token.
    
    Args:
        token: JWT access token string
        
    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Verify it's an access token
        if payload.get("type") != "access":
            logger.warning("Token is not an access token")
            return None
        
        return TokenPayload(**payload)
    
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding token: {e}")
        return None


def decode_refresh_token(token: str) -> Optional[RefreshTokenPayload]:
    """
    Decode and validate a refresh token.
    
    Args:
        token: JWT refresh token string
        
    Returns:
        RefreshTokenPayload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            logger.warning("Token is not a refresh token")
            return None
        
        return RefreshTokenPayload(**payload)
    
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding token: {e}")
        return None


# ===========================================
# Utility Functions
# ===========================================

def generate_id() -> str:
    """
    Generate a unique ID using ULID.
    ULIDs are sortable and URL-safe.
    
    Returns:
        Unique identifier string
    """
    return str(ulid.new())


def hash_token(token: str) -> str:
    """
    Hash a token for secure storage.
    Used for refresh tokens stored in database.
    
    Args:
        token: Token to hash
        
    Returns:
        Hashed token
    """
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()


def generate_reset_token() -> tuple[str, str]:
    """
    Generate a password reset token.
    
    Returns:
        Tuple of (plain_token, hashed_token)
    """
    import secrets
    plain_token = secrets.token_urlsafe(32)
    hashed_token = hash_token(plain_token)
    return plain_token, hashed_token


def generate_verification_token() -> tuple[str, str]:
    """
    Generate an email verification token.
    
    Returns:
        Tuple of (plain_token, hashed_token)
    """
    import secrets
    plain_token = secrets.token_urlsafe(32)
    hashed_token = hash_token(plain_token)
    return plain_token, hashed_token


def utcnow_iso() -> str:
    """
    Get current UTC time as ISO format string.
    Use this for database operations with libsql.
    
    Returns:
        ISO 8601 formatted UTC datetime string
    """
    return datetime.utcnow().isoformat()

