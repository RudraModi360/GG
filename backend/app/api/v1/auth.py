"""
GearGuard Backend - Authentication Endpoints
Handles user registration, login, logout, and token management.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field
import logging

from app.api.deps import Db, CurrentUser, ClientInfo, get_current_user_optional
from app.core import (
    verify_password,
    get_password_hash,
    validate_password_strength,
    create_token_pair,
    decode_refresh_token,
    generate_id,
    hash_token,
    generate_reset_token,
    TokenPayload,
)
from app.core.permissions import get_role_permissions, Role
from app.core.exceptions import (
    InvalidCredentialsError,
    ResourceNotFoundError,
    ResourceAlreadyExistsError,
    ValidationError,
    to_http_exception,
)
from app.config import settings
from app.core.email import send_email, get_welcome_email_content, get_reset_password_email_content

logger = logging.getLogger(__name__)
router = APIRouter()


# ===========================================
# Request/Response Schemas
# ===========================================

class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None
    organization_name: Optional[str] = None  # If creating new org
    organization_id: Optional[str] = None    # If joining existing org


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token pair response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8)


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class UserProfileResponse(BaseModel):
    """User profile response."""
    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    profile_image_url: Optional[str]
    role: str
    organization_id: str
    organization_name: Optional[str]
    is_verified: bool
    created_at: str


class UpdateProfileRequest(BaseModel):
    """Update profile request."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None
    profile_image_url: Optional[str] = None


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


# ===========================================
# Authentication Endpoints
# ===========================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Db,
    client_info: ClientInfo,
    background_tasks: BackgroundTasks
):
    """
    Register a new user.
    
    If organization_name is provided, creates a new organization with the user as admin.
    If organization_id is provided, joins the existing organization as a viewer.
    """
    # Check if email already exists
    existing = db.fetch_one(
        "SELECT id FROM users WHERE email = ?",
        (request.email.lower(),)
    )
    if existing:
        raise to_http_exception(
            ResourceAlreadyExistsError("User", "email", request.email)
        )
    
    # Validate password strength
    is_valid, error_msg = validate_password_strength(request.password)
    if not is_valid:
        raise to_http_exception(ValidationError(error_msg, field="password"))
    
    # Create or get organization
    org_id = request.organization_id
    role = Role.TECHNICIAN  # Default role when joining
    
    if request.organization_name:
        # Create new organization
        org_id = generate_id()
        org_slug = f"{request.organization_name.lower().replace(' ', '-')}-{generate_id()[:8]}"
        
        db.execute(
            """
            INSERT INTO organizations (id, name, slug, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (org_id, request.organization_name, org_slug, datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
        )
        role = Role.ADMIN  # Creator becomes admin
    elif not org_id:
        # Create a default organization for the user
        org_id = generate_id()
        org_slug = f"org-{generate_id()[:8]}"
        
        db.execute(
            """
            INSERT INTO organizations (id, name, slug, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (org_id, f"{request.first_name}'s Organization", org_slug, datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
        )
        role = Role.ADMIN
    
    # Get role ID
    role_row = db.fetch_one("SELECT id FROM roles WHERE name = ?", (role,))
    if not role_row:
        # Create role if not exists (shouldn't happen if migrations ran)
        role_id = f"role_{role}"
    else:
        role_id = role_row[0]
    
    # Create user
    user_id = generate_id()
    password_hash = request.password
    now = datetime.utcnow().isoformat()
    
    db.execute(
        """
        INSERT INTO users (
            id, email, password_hash, first_name, last_name, phone,
            role_id, organization_id, is_active, is_verified,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id, request.email.lower(), password_hash,
            request.first_name, request.last_name, request.phone,
            role_id, org_id, True, False, now, now
        )
    )
    
    # Create tokens
    permissions = get_role_permissions(role)
    token_pair, session_id = create_token_pair(
        user_id=user_id,
        email=request.email.lower(),
        org_id=org_id,
        role=role,
        permissions=permissions
    )
    
    # Store session
    db.execute(
        """
        INSERT INTO sessions (
            id, user_id, refresh_token_hash, device_info, 
            ip_address, user_agent, is_active, expires_at, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id, user_id, token_pair.refresh_token,
            None, client_info.get("ip_address"), client_info.get("user_agent"),
            True, (datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).isoformat(),
            datetime.utcnow().isoformat()
        )
    )
    
    db.commit()
    db.sync()
    
    logger.info(f"New user registered: {request.email}")
    
    # Send welcome email
    html_content = get_welcome_email_content(f"{request.first_name} {request.last_name}")
    background_tasks.add_task(
        send_email, 
        to_email=request.email, 
        subject="Welcome to GearGuard", 
        html_content=html_content
    )
    
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Db,
    client_info: ClientInfo
):
    """
    Authenticate user and return JWT tokens.
    """
    # Get user by email
    user = db.fetch_one(
        """
        SELECT u.id, u.email, u.password_hash, u.first_name, u.last_name,
               u.organization_id, u.is_active, u.is_verified, r.name as role
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE u.email = ?
        """,
        (request.email.lower(),)
    )
    
    if not user:
        raise to_http_exception(InvalidCredentialsError())
    
    (
        user_id, email, password_hash, first_name, last_name,
        org_id, is_active, is_verified, role
    ) = user
    
    # Verify password (plain text comparison)
    if request.password != password_hash:
        raise to_http_exception(InvalidCredentialsError())
    
    # Check if user is active
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Create tokens
    permissions = get_role_permissions(role)
    token_pair, session_id = create_token_pair(
        user_id=user_id,
        email=email,
        org_id=org_id,
        role=role,
        permissions=permissions
    )
    
    # Store session
    db.execute(
        """
        INSERT INTO sessions (
            id, user_id, refresh_token_hash, device_info,
            ip_address, user_agent, is_active, expires_at, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id, user_id, token_pair.refresh_token,
            None, client_info.get("ip_address"), client_info.get("user_agent"),
            True, (datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).isoformat(),
            datetime.utcnow().isoformat()
        )
    )
    
    # Update last login
    db.execute(
        "UPDATE users SET last_login = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), user_id)
    )
    
    db.commit()
    db.sync()
    
    logger.info(f"User logged in: {email}")
    
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: CurrentUser,
    db: Db
):
    """
    Logout user by invalidating all sessions.
    """
    db.execute(
        "UPDATE sessions SET is_active = FALSE WHERE user_id = ?",
        (current_user.sub,)
    )
    db.commit()
    db.sync()
    
    logger.info(f"User logged out: {current_user.email}")
    
    return MessageResponse(message="Logged out successfully")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: Db,
    client_info: ClientInfo
):
    """
    Refresh access token using refresh token.
    """
    # Decode refresh token
    payload = decode_refresh_token(request.refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Verify session exists and is active
    session = db.fetch_one(
        """
        SELECT s.id, s.is_active, s.expires_at, u.email, u.organization_id, r.name as role
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        JOIN roles r ON u.role_id = r.id
        WHERE s.id = ? AND s.user_id = ?
        """,
        (payload.session_id, payload.sub)
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found"
        )
    
    session_id, is_active, expires_at, email, org_id, role = session
    
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked"
        )
    
    # Create new tokens
    permissions = get_role_permissions(role)
    token_pair, new_session_id = create_token_pair(
        user_id=payload.sub,
        email=email,
        org_id=org_id,
        role=role,
        permissions=permissions
    )
    
    # Invalidate old session and create new one
    db.execute("UPDATE sessions SET is_active = FALSE WHERE id = ?", (session_id,))
    
    db.execute(
        """
        INSERT INTO sessions (
            id, user_id, refresh_token_hash, device_info,
            ip_address, user_agent, is_active, expires_at, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_session_id, payload.sub, token_pair.refresh_token,
            None, client_info.get("ip_address"), client_info.get("user_agent"),
            True, (datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).isoformat(),
            datetime.utcnow().isoformat()
        )
    )
    
    db.commit()
    db.sync()
    
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in
    )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: PasswordResetRequest,
    db: Db,
    background_tasks: BackgroundTasks
):
    """
    Request a password reset email.
    """
    # Check if user exists
    user = db.fetch_one(
        "SELECT id FROM users WHERE email = ?",
        (request.email.lower(),)
    )
    
    # Always return success to prevent email enumeration
    if not user:
        logger.warning(f"Password reset requested for non-existent email: {request.email}")
        return MessageResponse(message="If the email exists, a reset link will be sent")
    
    user_id = user[0]
    
    # Generate reset token
    plain_token, hashed_token = generate_reset_token()
    expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    
    # Store token
    db.execute(
        """
        INSERT INTO password_reset_tokens (id, user_id, token_hash, expires_at, is_used)
        VALUES (?, ?, ?, ?, FALSE)
        """,
        (generate_id(), user_id, plain_token, expires_at)
    )
    db.commit()
    db.sync()
    
    # TODO: Send email with plain_token
    logger.info(f"Password reset token generated for: {request.email}")
    
    return MessageResponse(message="If the email exists, a reset link will be sent")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: PasswordResetConfirm,
    db: Db
):
    """
    Reset password using the reset token.
    """
    # Validate new password
    is_valid, error_msg = validate_password_strength(request.new_password)
    if not is_valid:
        raise to_http_exception(ValidationError(error_msg, field="new_password"))
    
    # Find valid token
    token_val = request.token
    token_row = db.fetch_one(
        """
        SELECT id, user_id, expires_at, is_used
        FROM password_reset_tokens
        WHERE token_hash = ?
        """,
        (token_val,)
    )
    
    if not token_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    token_id, user_id, expires_at, is_used = token_row
    
    if is_used or datetime.utcnow() > datetime.fromisoformat(str(expires_at)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Update password (store as plain text)
    db.execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
        (request.new_password, datetime.utcnow().isoformat(), user_id)
    )
    
    # Mark token as used
    db.execute(
        "UPDATE password_reset_tokens SET is_used = TRUE WHERE id = ?",
        (token_id,)
    )
    
    # Invalidate all sessions
    db.execute(
        "UPDATE sessions SET is_active = FALSE WHERE user_id = ?",
        (user_id,)
    )
    
    db.commit()
    db.sync()
    
    logger.info(f"Password reset successful for user: {user_id}")
    
    return MessageResponse(message="Password reset successfully. Please login with your new password.")


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: CurrentUser,
    db: Db
):
    """
    Get the current user's profile.
    """
    user = db.fetch_one(
        """
        SELECT u.id, u.email, u.first_name, u.last_name, u.phone,
               u.profile_image_url, u.is_verified, u.created_at,
               r.name as role, o.id as org_id, o.name as org_name
        FROM users u
        JOIN roles r ON u.role_id = r.id
        JOIN organizations o ON u.organization_id = o.id
        WHERE u.id = ?
        """,
        (current_user.sub,)
    )
    
    if not user:
        raise to_http_exception(ResourceNotFoundError("User", current_user.sub))
    
    (
        user_id, email, first_name, last_name, phone,
        profile_image_url, is_verified, created_at,
        role, org_id, org_name
    ) = user
    
    return UserProfileResponse(
        id=user_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        profile_image_url=profile_image_url,
        role=role,
        organization_id=org_id,
        organization_name=org_name,
        is_verified=bool(is_verified),
        created_at=str(created_at)
    )


@router.put("/me", response_model=UserProfileResponse)
async def update_current_user_profile(
    request: UpdateProfileRequest,
    current_user: CurrentUser,
    db: Db
):
    """
    Update the current user's profile.
    """
    updates = []
    params = []
    
    if request.first_name is not None:
        updates.append("first_name = ?")
        params.append(request.first_name)
    
    if request.last_name is not None:
        updates.append("last_name = ?")
        params.append(request.last_name)
    
    if request.phone is not None:
        updates.append("phone = ?")
        params.append(request.phone)
    
    if request.profile_image_url is not None:
        updates.append("profile_image_url = ?")
        params.append(request.profile_image_url)
    
    if updates:
        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(current_user.sub)
        
        db.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
        db.commit()
        db.sync()
    
    # Return updated profile
    return await get_current_user_profile(current_user, db)


@router.put("/me/password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentUser,
    db: Db
):
    """
    Change the current user's password.
    """
    # Get current password hash
    user = db.fetch_one(
        "SELECT password_hash FROM users WHERE id = ?",
        (current_user.sub,)
    )
    
    if not user:
        raise to_http_exception(ResourceNotFoundError("User", current_user.sub))
    
    # Verify current password (plain text comparison)
    if request.current_password != user[0]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    is_valid, error_msg = validate_password_strength(request.new_password)
    if not is_valid:
        raise to_http_exception(ValidationError(error_msg, field="new_password"))
    
    # Update password (store as plain text)
    db.execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
        (request.new_password, datetime.utcnow().isoformat(), current_user.sub)
    )
    
    db.commit()
    db.sync()
    
    logger.info(f"Password changed for user: {current_user.email}")
    
    return MessageResponse(message="Password changed successfully")
