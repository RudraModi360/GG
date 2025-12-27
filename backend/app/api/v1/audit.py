"""
GearGuard Backend - Audit Logs Endpoints
System audit trail access.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..deps import Db, CurrentUser, Pagination, PermissionChecker
from ...core.permissions import Permission

router = APIRouter()


class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str]
    user_email: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    ip_address: Optional[str]
    created_at: str


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int


@router.get("", response_model=AuditLogListResponse, dependencies=[Depends(PermissionChecker(Permission.AUDIT_READ))])
async def list_audit_logs(
    current_user: CurrentUser,
    db: Db,
    pagination: Pagination,
    resource_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None)
):
    """List audit logs for the organization."""
    where_clauses = ["a.organization_id = ?"]
    params = [current_user.org_id]
    
    if resource_type:
        where_clauses.append("a.resource_type = ?")
        params.append(resource_type)
    if action:
        where_clauses.append("a.action = ?")
        params.append(action)
    if user_id:
        where_clauses.append("a.user_id = ?")
        params.append(user_id)
    
    where_sql = " AND ".join(where_clauses)
    
    count = db.fetch_one(f"SELECT COUNT(*) FROM audit_logs a WHERE {where_sql}", tuple(params))
    
    params.extend([pagination.limit, pagination.offset])
    rows = db.fetch_all(
        f"""SELECT a.id, a.user_id, u.email, a.action, a.resource_type, a.resource_id, a.ip_address, a.created_at
        FROM audit_logs a LEFT JOIN users u ON a.user_id = u.id
        WHERE {where_sql} ORDER BY a.created_at DESC LIMIT ? OFFSET ?""",
        tuple(params)
    )
    
    return AuditLogListResponse(
        items=[AuditLogResponse(
            id=r[0], user_id=r[1], user_email=r[2], action=r[3],
            resource_type=r[4], resource_id=r[5], ip_address=r[6], created_at=str(r[7])
        ) for r in rows],
        total=count[0] if count else 0,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.get("/{resource_type}/{resource_id}", response_model=List[AuditLogResponse],
            dependencies=[Depends(PermissionChecker(Permission.AUDIT_READ))])
async def get_resource_audit_trail(resource_type: str, resource_id: str, current_user: CurrentUser, db: Db):
    """Get audit trail for a specific resource."""
    rows = db.fetch_all(
        """SELECT a.id, a.user_id, u.email, a.action, a.resource_type, a.resource_id, a.ip_address, a.created_at
        FROM audit_logs a LEFT JOIN users u ON a.user_id = u.id
        WHERE a.organization_id = ? AND a.resource_type = ? AND a.resource_id = ?
        ORDER BY a.created_at DESC LIMIT 100""",
        (current_user.org_id, resource_type, resource_id)
    )
    return [AuditLogResponse(
        id=r[0], user_id=r[1], user_email=r[2], action=r[3],
        resource_type=r[4], resource_id=r[5], ip_address=r[6], created_at=str(r[7])
    ) for r in rows]
