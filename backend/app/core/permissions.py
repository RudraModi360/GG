"""
GearGuard Backend - Permission System
Role-Based Access Control (RBAC) implementation.
"""
from functools import wraps
from typing import Optional, Callable, Any
from fastapi import HTTPException, status
import logging

from .security import TokenPayload

logger = logging.getLogger(__name__)


# ===========================================
# Permission Definitions
# ===========================================

class Permission:
    """Permission string constants."""
    
    # Organization
    ORG_CREATE = "organization:create"
    ORG_READ = "organization:read"
    ORG_UPDATE = "organization:update"
    ORG_DELETE = "organization:delete"
    
    # User
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_MANAGE_ROLES = "user:manage_roles"
    
    # Equipment
    EQUIPMENT_CREATE = "equipment:create"
    EQUIPMENT_READ = "equipment:read"
    EQUIPMENT_UPDATE = "equipment:update"
    EQUIPMENT_DELETE = "equipment:delete"
    EQUIPMENT_REPORT_ISSUE = "equipment:report_issue"
    
    # Work Order
    WORKORDER_CREATE = "workorder:create"
    WORKORDER_READ = "workorder:read"
    WORKORDER_UPDATE = "workorder:update"
    WORKORDER_DELETE = "workorder:delete"
    WORKORDER_ASSIGN = "workorder:assign"
    WORKORDER_COMPLETE = "workorder:complete"
    
    # Schedule
    SCHEDULE_CREATE = "schedule:create"
    SCHEDULE_READ = "schedule:read"
    SCHEDULE_UPDATE = "schedule:update"
    SCHEDULE_DELETE = "schedule:delete"
    
    # Parts
    PARTS_CREATE = "parts:create"
    PARTS_READ = "parts:read"
    PARTS_UPDATE = "parts:update"
    PARTS_DELETE = "parts:delete"
    PARTS_USE = "parts:use"
    
    # Report
    REPORT_CREATE = "report:create"
    REPORT_READ = "report:read"
    REPORT_UPDATE = "report:update"
    REPORT_DELETE = "report:delete"
    REPORT_EXPORT = "report:export"
    
    # Admin
    SETTINGS_MANAGE = "settings:manage"
    AUDIT_READ = "audit:read"
    NOTIFICATION_MANAGE = "notification:manage"


# ===========================================
# Role Definitions
# ===========================================

class Role:
    """Role name constants."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    TECHNICIAN = "technician"


# Default permissions for each role
ROLE_PERMISSIONS: dict[str, list[str]] = {
    Role.SUPER_ADMIN: ["*"],  # Wildcard for all permissions
    
    Role.ADMIN: [
        Permission.ORG_READ,
        Permission.ORG_UPDATE,
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.USER_MANAGE_ROLES,
        Permission.EQUIPMENT_CREATE,
        Permission.EQUIPMENT_READ,
        Permission.EQUIPMENT_UPDATE,
        Permission.EQUIPMENT_DELETE,
        Permission.EQUIPMENT_REPORT_ISSUE,
        Permission.WORKORDER_CREATE,
        Permission.WORKORDER_READ,
        Permission.WORKORDER_UPDATE,
        Permission.WORKORDER_DELETE,
        Permission.WORKORDER_ASSIGN,
        Permission.WORKORDER_COMPLETE,
        Permission.SCHEDULE_CREATE,
        Permission.SCHEDULE_READ,
        Permission.SCHEDULE_UPDATE,
        Permission.SCHEDULE_DELETE,
        Permission.PARTS_CREATE,
        Permission.PARTS_READ,
        Permission.PARTS_UPDATE,
        Permission.PARTS_DELETE,
        Permission.PARTS_USE,
        Permission.REPORT_CREATE,
        Permission.REPORT_READ,
        Permission.REPORT_EXPORT,
        Permission.SETTINGS_MANAGE,
        Permission.AUDIT_READ,
    ],
    
    Role.MANAGER: [
        Permission.USER_READ,
        Permission.EQUIPMENT_CREATE,
        Permission.EQUIPMENT_READ,
        Permission.EQUIPMENT_UPDATE,
        Permission.EQUIPMENT_DELETE,
        Permission.EQUIPMENT_REPORT_ISSUE,
        Permission.WORKORDER_CREATE,
        Permission.WORKORDER_READ,
        Permission.WORKORDER_UPDATE,
        Permission.WORKORDER_DELETE,
        Permission.WORKORDER_ASSIGN,
        Permission.WORKORDER_COMPLETE,
        Permission.SCHEDULE_CREATE,
        Permission.SCHEDULE_READ,
        Permission.SCHEDULE_UPDATE,
        Permission.SCHEDULE_DELETE,
        Permission.PARTS_CREATE,
        Permission.PARTS_READ,
        Permission.PARTS_UPDATE,
        Permission.PARTS_DELETE,
        Permission.PARTS_USE,
        Permission.REPORT_CREATE,
        Permission.REPORT_READ,
        Permission.REPORT_EXPORT,
    ],
    
    Role.TECHNICIAN: [
        Permission.EQUIPMENT_READ,
        Permission.EQUIPMENT_UPDATE,
        Permission.EQUIPMENT_REPORT_ISSUE,
        Permission.WORKORDER_CREATE,
        Permission.WORKORDER_READ,
        Permission.WORKORDER_UPDATE,
        Permission.WORKORDER_COMPLETE,
        Permission.SCHEDULE_READ,
        Permission.PARTS_READ,
        Permission.PARTS_USE,
        Permission.REPORT_READ,
    ],
}


# ===========================================
# Permission Checking Functions
# ===========================================

def has_permission(
    user_permissions: list[str], 
    required_permission: str
) -> bool:
    """
    Check if user has the required permission.
    
    Supports:
    - Exact match: "equipment:read" matches "equipment:read"
    - Wildcard: "*" matches everything
    - Resource wildcard: "equipment:*" matches "equipment:read", "equipment:update", etc.
    
    Args:
        user_permissions: List of user's permissions
        required_permission: Permission string to check
        
    Returns:
        True if user has permission, False otherwise
    """
    # Super admin wildcard
    if "*" in user_permissions:
        return True
    
    # Exact match
    if required_permission in user_permissions:
        return True
    
    # Resource wildcard (e.g., "equipment:*" matches "equipment:read")
    if ":" in required_permission:
        resource = required_permission.split(":")[0]
        wildcard = f"{resource}:*"
        if wildcard in user_permissions:
            return True
    
    return False


def has_any_permission(
    user_permissions: list[str], 
    required_permissions: list[str]
) -> bool:
    """
    Check if user has any of the required permissions.
    
    Args:
        user_permissions: List of user's permissions
        required_permissions: List of permissions to check (OR logic)
        
    Returns:
        True if user has at least one permission, False otherwise
    """
    for permission in required_permissions:
        if has_permission(user_permissions, permission):
            return True
    return False


def has_all_permissions(
    user_permissions: list[str], 
    required_permissions: list[str]
) -> bool:
    """
    Check if user has all of the required permissions.
    
    Args:
        user_permissions: List of user's permissions
        required_permissions: List of permissions to check (AND logic)
        
    Returns:
        True if user has all permissions, False otherwise
    """
    for permission in required_permissions:
        if not has_permission(user_permissions, permission):
            return False
    return True


def get_role_permissions(role: str) -> list[str]:
    """
    Get list of permissions for a role.
    
    Args:
        role: Role name
        
    Returns:
        List of permission strings
    """
    return ROLE_PERMISSIONS.get(role, [])


def can_manage_role(manager_role: str, target_role: str) -> bool:
    """
    Check if a manager role can assign/manage a target role.
    Prevents privilege escalation.
    
    Args:
        manager_role: Role of the user trying to manage
        target_role: Role being assigned
        
    Returns:
        True if manager can manage the target role
    """
    role_hierarchy = {
        Role.SUPER_ADMIN: 1,
        Role.ADMIN: 2,
        Role.MANAGER: 3,
        Role.TECHNICIAN: 4,
    }
    
    manager_level = role_hierarchy.get(manager_role, 99)
    target_level = role_hierarchy.get(target_role, 0)
    
    # Can only assign roles at same level or lower (higher number)
    return manager_level < target_level


# ===========================================
# Permission Decorators
# ===========================================

def require_permission(permission: str):
    """
    Decorator to require a specific permission for an endpoint.
    
    Usage:
        @router.get("/equipment")
        @require_permission(Permission.EQUIPMENT_READ)
        async def get_equipment(current_user: TokenPayload = Depends(get_current_user)):
            ...
    
    Args:
        permission: Required permission string
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, current_user: Optional[TokenPayload] = None, **kwargs):
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not has_permission(current_user.permissions, permission):
                logger.warning(
                    f"Permission denied: User {current_user.sub} "
                    f"lacks permission {permission}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission} required"
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


def require_any_permission(*permissions: str):
    """
    Decorator to require at least one of the specified permissions.
    
    Usage:
        @router.get("/resource")
        @require_any_permission(Permission.READ, Permission.ADMIN)
        async def get_resource(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, current_user: Optional[TokenPayload] = None, **kwargs):
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not has_any_permission(current_user.permissions, list(permissions)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: One of {permissions} required"
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


def require_role(role: str):
    """
    Decorator to require a specific role.
    
    Usage:
        @router.get("/admin")
        @require_role(Role.ADMIN)
        async def admin_endpoint(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, current_user: Optional[TokenPayload] = None, **kwargs):
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if current_user.role != role and current_user.role != Role.SUPER_ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role {role} required"
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


def require_same_org(org_id_param: str = "org_id"):
    """
    Decorator to ensure user can only access resources in their organization.
    
    Usage:
        @router.get("/organizations/{org_id}/equipment")
        @require_same_org("org_id")
        async def get_org_equipment(org_id: str, current_user: ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, current_user: Optional[TokenPayload] = None, **kwargs):
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Super admin can access any organization
            if current_user.role == Role.SUPER_ADMIN:
                return await func(*args, current_user=current_user, **kwargs)
            
            # Check if org_id matches user's organization
            requested_org_id = kwargs.get(org_id_param)
            if requested_org_id and requested_org_id != current_user.org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Cannot access resources from other organizations"
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
