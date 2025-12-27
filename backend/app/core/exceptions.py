"""
GearGuard Backend - Custom Exceptions
Application-specific exception classes.
"""
from typing import Optional, Any, Dict
from fastapi import HTTPException, status


class GearGuardException(Exception):
    """Base exception for GearGuard application."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "GEARGUARD_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


# ===========================================
# Authentication Exceptions
# ===========================================

class AuthenticationError(GearGuardException):
    """Base authentication error."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Invalid email or password."""
    
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message, code="INVALID_CREDENTIALS")


class TokenExpiredError(AuthenticationError):
    """JWT token has expired."""
    
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message, code="TOKEN_EXPIRED")


class InvalidTokenError(AuthenticationError):
    """JWT token is invalid."""
    
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message, code="INVALID_TOKEN")


class SessionExpiredError(AuthenticationError):
    """User session has expired."""
    
    def __init__(self, message: str = "Session has expired, please login again"):
        super().__init__(message, code="SESSION_EXPIRED")


class AccountDisabledError(AuthenticationError):
    """User account is disabled."""
    
    def __init__(self, message: str = "Account is disabled"):
        super().__init__(message, code="ACCOUNT_DISABLED")


class EmailNotVerifiedError(AuthenticationError):
    """Email address not verified."""
    
    def __init__(self, message: str = "Email address not verified"):
        super().__init__(message, code="EMAIL_NOT_VERIFIED")


# ===========================================
# Authorization Exceptions
# ===========================================

class AuthorizationError(GearGuardException):
    """Base authorization error."""
    pass


class PermissionDeniedError(AuthorizationError):
    """User lacks required permission."""
    
    def __init__(
        self, 
        message: str = "Permission denied",
        required_permission: Optional[str] = None
    ):
        details = {}
        if required_permission:
            details["required_permission"] = required_permission
        super().__init__(message, code="PERMISSION_DENIED", details=details)


class ResourceAccessDeniedError(AuthorizationError):
    """User cannot access the requested resource."""
    
    def __init__(
        self, 
        message: str = "Access to resource denied",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, code="RESOURCE_ACCESS_DENIED", details=details)


# ===========================================
# Resource Exceptions
# ===========================================

class ResourceError(GearGuardException):
    """Base resource error."""
    pass


class ResourceNotFoundError(ResourceError):
    """Requested resource not found."""
    
    def __init__(
        self, 
        resource_type: str,
        resource_id: Optional[str] = None,
        message: Optional[str] = None
    ):
        if message is None:
            if resource_id:
                message = f"{resource_type} with ID '{resource_id}' not found"
            else:
                message = f"{resource_type} not found"
        
        super().__init__(
            message, 
            code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class ResourceAlreadyExistsError(ResourceError):
    """Resource already exists (duplicate)."""
    
    def __init__(
        self, 
        resource_type: str,
        field: str,
        value: str,
        message: Optional[str] = None
    ):
        if message is None:
            message = f"{resource_type} with {field} '{value}' already exists"
        
        super().__init__(
            message,
            code="RESOURCE_EXISTS",
            details={"resource_type": resource_type, "field": field, "value": value}
        )


class ResourceConflictError(ResourceError):
    """Resource state conflict."""
    
    def __init__(
        self, 
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ):
        super().__init__(
            message,
            code="RESOURCE_CONFLICT",
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


# ===========================================
# Validation Exceptions
# ===========================================

class ValidationError(GearGuardException):
    """Data validation error."""
    
    def __init__(
        self, 
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None
    ):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class InvalidInputError(ValidationError):
    """Invalid input data."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, field=field)
        self.code = "INVALID_INPUT"


# ===========================================
# Business Logic Exceptions
# ===========================================

class BusinessLogicError(GearGuardException):
    """Business rule violation."""
    pass


class WorkOrderError(BusinessLogicError):
    """Work order related error."""
    
    def __init__(self, message: str, work_order_id: Optional[str] = None):
        super().__init__(
            message,
            code="WORKORDER_ERROR",
            details={"work_order_id": work_order_id}
        )


class InventoryError(BusinessLogicError):
    """Inventory/parts related error."""
    
    def __init__(self, message: str, part_id: Optional[str] = None):
        super().__init__(
            message,
            code="INVENTORY_ERROR",
            details={"part_id": part_id}
        )


class InsufficientStockError(InventoryError):
    """Not enough parts in stock."""
    
    def __init__(
        self, 
        part_name: str,
        requested: int,
        available: int
    ):
        message = f"Insufficient stock for '{part_name}': requested {requested}, available {available}"
        super().__init__(message)
        self.code = "INSUFFICIENT_STOCK"
        self.details = {
            "part_name": part_name,
            "requested": requested,
            "available": available
        }


# ===========================================
# HTTP Exception Converters
# ===========================================

def to_http_exception(error: GearGuardException) -> HTTPException:
    """
    Convert a GearGuard exception to FastAPI HTTPException.
    
    Args:
        error: GearGuard exception instance
        
    Returns:
        FastAPI HTTPException
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    if isinstance(error, InvalidCredentialsError):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(error, (TokenExpiredError, InvalidTokenError, SessionExpiredError)):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(error, (AccountDisabledError, EmailNotVerifiedError)):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(error, (PermissionDeniedError, ResourceAccessDeniedError)):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(error, ResourceNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, (ResourceAlreadyExistsError, ResourceConflictError)):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(error, (ValidationError, InvalidInputError)):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(error, BusinessLogicError):
        status_code = status.HTTP_400_BAD_REQUEST
    
    return HTTPException(
        status_code=status_code,
        detail={
            "message": error.message,
            "code": error.code,
            "details": error.details
        }
    )
