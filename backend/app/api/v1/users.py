"""
GearGuard Backend - Users Endpoints
User management operations.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field

from ..deps import Db, CurrentUser, Pagination, PermissionChecker
from ...core import generate_id, get_password_hash
from ...core.permissions import Permission, Role, can_manage_role

router = APIRouter()


# ===========================================
# Schemas
# ===========================================

class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    profile_image_url: Optional[str]
    role: str
    organization_id: str
    is_active: bool
    is_verified: bool
    last_login: Optional[str]
    created_at: str


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None
    role: str = Role.TECHNICIAN


class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int


class RoleUpdateRequest(BaseModel):
    role: str


# ===========================================
# Endpoints
# ===========================================

@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(Permission.USER_CREATE))]
)
async def create_user(
    request: UserCreateRequest,
    current_user: CurrentUser,
    db: Db
):
    """Create a new user in the organization."""
    # Check if email exists
    existing = db.fetch_one(
        "SELECT id FROM users WHERE email = ?",
        (request.email.lower(),)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
    
    # Check role assignment permission
    if not can_manage_role(current_user.role, request.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign a role equal to or higher than your own"
        )
    
    # Get role ID
    role_row = db.fetch_one("SELECT id FROM roles WHERE name = ?", (request.role,))
    if not role_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role"
        )
    
    user_id = generate_id()
    now = datetime.utcnow()
    
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
            user_id, request.email.lower(), get_password_hash(request.password),
            request.first_name, request.last_name, request.phone,
            role_row[0], current_user.org_id, True, False, now, now
        )
    )
    db.commit()
    db.sync()
    
    return UserResponse(
        id=user_id,
        email=request.email.lower(),
        first_name=request.first_name,
        last_name=request.last_name,
        phone=request.phone,
        profile_image_url=None,
        role=request.role,
        organization_id=current_user.org_id,
        is_active=True,
        is_verified=False,
        last_login=None,
        created_at=str(now)
    )


@router.get(
    "",
    response_model=UserListResponse,
    dependencies=[Depends(PermissionChecker(Permission.USER_READ))]
)
async def list_users(
    current_user: CurrentUser,
    db: Db,
    pagination: Pagination,
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None)
):
    """List users in the organization."""
    where_clauses = ["u.organization_id = ?"]
    params = [current_user.org_id]
    
    if role:
        where_clauses.append("r.name = ?")
        params.append(role)
    
    if is_active is not None:
        where_clauses.append("u.is_active = ?")
        params.append(is_active)
    
    if search:
        where_clauses.append("(u.first_name LIKE ? OR u.last_name LIKE ? OR u.email LIKE ?)")
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])
    
    where_sql = " AND ".join(where_clauses)
    
    # Get total count
    count_row = db.fetch_one(
        f"""
        SELECT COUNT(*)
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE {where_sql}
        """,
        tuple(params)
    )
    total = count_row[0] if count_row else 0
    
    # Get users
    params.extend([pagination.limit, pagination.offset])
    rows = db.fetch_all(
        f"""
        SELECT u.id, u.email, u.first_name, u.last_name, u.phone,
               u.profile_image_url, r.name as role, u.organization_id,
               u.is_active, u.is_verified, u.last_login, u.created_at
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE {where_sql}
        ORDER BY u.created_at DESC
        LIMIT ? OFFSET ?
        """,
        tuple(params)
    )
    
    users = [
        UserResponse(
            id=row[0], email=row[1], first_name=row[2], last_name=row[3],
            phone=row[4], profile_image_url=row[5], role=row[6],
            organization_id=row[7], is_active=bool(row[8]), is_verified=bool(row[9]),
            last_login=str(row[10]) if row[10] else None, created_at=str(row[11])
        )
        for row in rows
    ]
    
    return UserListResponse(
        items=users,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(PermissionChecker(Permission.USER_READ))]
)
async def get_user(
    user_id: str,
    current_user: CurrentUser,
    db: Db
):
    """Get a specific user by ID."""
    row = db.fetch_one(
        """
        SELECT u.id, u.email, u.first_name, u.last_name, u.phone,
               u.profile_image_url, r.name as role, u.organization_id,
               u.is_active, u.is_verified, u.last_login, u.created_at
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE u.id = ? AND u.organization_id = ?
        """,
        (user_id, current_user.org_id)
    )
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=row[0], email=row[1], first_name=row[2], last_name=row[3],
        phone=row[4], profile_image_url=row[5], role=row[6],
        organization_id=row[7], is_active=bool(row[8]), is_verified=bool(row[9]),
        last_login=str(row[10]) if row[10] else None, created_at=str(row[11])
    )


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(PermissionChecker(Permission.USER_UPDATE))]
)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    current_user: CurrentUser,
    db: Db
):
    """Update a user's information."""
    # Verify user exists in same org
    existing = db.fetch_one(
        "SELECT id FROM users WHERE id = ? AND organization_id = ?",
        (user_id, current_user.org_id)
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
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
    
    if request.is_active is not None:
        updates.append("is_active = ?")
        params.append(request.is_active)
    
    if updates:
        updates.append("updated_at = ?")
        params.append(datetime.utcnow())
        params.append(user_id)
        
        db.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
        db.commit()
        db.sync()
    
    return await get_user(user_id, current_user, db)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(Permission.USER_DELETE))]
)
async def delete_user(
    user_id: str,
    current_user: CurrentUser,
    db: Db
):
    """Deactivate a user (soft delete)."""
    if user_id == current_user.sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    db.execute(
        """
        UPDATE users 
        SET is_active = FALSE, updated_at = ?
        WHERE id = ? AND organization_id = ?
        """,
        (datetime.utcnow(), user_id, current_user.org_id)
    )
    db.commit()
    db.sync()


@router.put(
    "/{user_id}/role",
    response_model=UserResponse,
    dependencies=[Depends(PermissionChecker(Permission.USER_MANAGE_ROLES))]
)
async def update_user_role(
    user_id: str,
    request: RoleUpdateRequest,
    current_user: CurrentUser,
    db: Db
):
    """Change a user's role."""
    if user_id == current_user.sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )
    
    if not can_manage_role(current_user.role, request.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign a role equal to or higher than your own"
        )
    
    role_row = db.fetch_one("SELECT id FROM roles WHERE name = ?", (request.role,))
    if not role_row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    
    db.execute(
        """
        UPDATE users 
        SET role_id = ?, updated_at = ?
        WHERE id = ? AND organization_id = ?
        """,
        (role_row[0], datetime.utcnow(), user_id, current_user.org_id)
    )
    db.commit()
    db.sync()
    
    return await get_user(user_id, current_user, db)
