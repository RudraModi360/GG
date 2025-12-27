"""
GearGuard Backend - API Dependencies
Dependency injection for FastAPI routes.
"""
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from app.database import get_database, Database
from app.core.security import decode_access_token, TokenPayload
from app.core.permissions import has_permission, Permission
from app.core.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
    AccountDisabledError,
    to_http_exception,
)

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


# ===========================================
# Database Dependency
# ===========================================

def get_db() -> Database:
    """
    Get database instance.
    
    Returns:
        Database connection instance
    """
    return get_database()


# ===========================================
# Authentication Dependencies
# ===========================================

async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Database = Depends(get_db)
) -> TokenPayload:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database instance
        
    Returns:
        Decoded token payload with user info
        
    Raises:
        HTTPException: If authentication fails
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Decode and validate the token
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Optional: Verify user still exists and is active
    # This adds a DB query but ensures immediate revocation
    user = db.fetch_one(
        "SELECT id, is_active, is_verified FROM users WHERE id = ?",
        (payload.sub,)
    )
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    user_id, is_active, is_verified = user
    
    if not is_active:
        raise to_http_exception(AccountDisabledError())
    
    return payload


async def get_current_user_optional(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
) -> Optional[TokenPayload]:
    """
    Get current user if authenticated, None otherwise.
    Use for endpoints that work both authenticated and anonymous.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        Token payload if authenticated, None otherwise
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    return decode_access_token(token)


async def get_current_active_user(
    current_user: Annotated[TokenPayload, Depends(get_current_user)]
) -> TokenPayload:
    """
    Get current user and verify they are active.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Token payload for active user
    """
    # User is already verified as active in get_current_user
    return current_user


# ===========================================
# Permission Dependencies
# ===========================================

class PermissionChecker:
    """
    Dependency class for checking permissions.
    
    Usage:
        @router.get("/equipment")
        async def get_equipment(
            _: bool = Depends(PermissionChecker(Permission.EQUIPMENT_READ))
        ):
            ...
    """
    
    def __init__(self, permission: str):
        self.permission = permission
    
    async def __call__(
        self, 
        current_user: Annotated[TokenPayload, Depends(get_current_user)]
    ) -> bool:
        if not has_permission(current_user.permissions, self.permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {self.permission} required"
            )
        return True


class MultiPermissionChecker:
    """
    Dependency class for checking multiple permissions (OR logic).
    
    Usage:
        @router.get("/resource")
        async def get_resource(
            _: bool = Depends(MultiPermissionChecker([Permission.READ, Permission.ADMIN]))
        ):
            ...
    """
    
    def __init__(self, permissions: list[str], require_all: bool = False):
        self.permissions = permissions
        self.require_all = require_all
    
    async def __call__(
        self, 
        current_user: Annotated[TokenPayload, Depends(get_current_user)]
    ) -> bool:
        if self.require_all:
            # AND logic - user must have all permissions
            for perm in self.permissions:
                if not has_permission(current_user.permissions, perm):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: {perm} required"
                    )
        else:
            # OR logic - user must have at least one permission
            has_any = any(
                has_permission(current_user.permissions, perm) 
                for perm in self.permissions
            )
            if not has_any:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: One of {self.permissions} required"
                )
        
        return True


# ===========================================
# Organization Context
# ===========================================

async def get_org_id(
    current_user: Annotated[TokenPayload, Depends(get_current_user)]
) -> str:
    """
    Get the current user's organization ID.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Organization ID
    """
    return current_user.org_id


# ===========================================
# Pagination Dependencies
# ===========================================

class PaginationParams:
    """
    Pagination parameters.
    
    Usage:
        @router.get("/items")
        async def get_items(pagination: PaginationParams = Depends()):
            offset = pagination.offset
            limit = pagination.limit
    """
    
    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
        max_page_size: int = 100
    ):
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > max_page_size:
            page_size = max_page_size
        
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size
        self.limit = page_size


# ===========================================
# Request Context
# ===========================================

async def get_client_info(request: Request) -> dict:
    """
    Extract client information from request.
    Useful for audit logging.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dictionary with client info
    """
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "origin": request.headers.get("origin"),
    }


# ===========================================
# Type Aliases for Cleaner Code
# ===========================================

CurrentUser = Annotated[TokenPayload, Depends(get_current_user)]
OptionalUser = Annotated[Optional[TokenPayload], Depends(get_current_user_optional)]
ActiveUser = Annotated[TokenPayload, Depends(get_current_active_user)]
OrgId = Annotated[str, Depends(get_org_id)]
Pagination = Annotated[PaginationParams, Depends()]
ClientInfo = Annotated[dict, Depends(get_client_info)]
Db = Annotated[Database, Depends(get_db)]
