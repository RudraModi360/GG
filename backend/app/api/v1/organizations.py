"""
GearGuard Backend - Organizations Endpoints
Organization management operations.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..deps import Db, CurrentUser, PermissionChecker
from ...core import generate_id
from ...core.permissions import Permission, Role

router = APIRouter()


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    logo_url: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    website: Optional[str]
    subscription_tier: str
    is_active: bool
    created_at: str


class OrganizationUpdateRequest(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None


class OrganizationStatsResponse(BaseModel):
    total_users: int
    total_equipment: int
    total_work_orders: int
    pending_work_orders: int
    completed_work_orders: int
    total_parts: int
    low_stock_parts: int


@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    current_user: CurrentUser,
    db: Db
):
    """List organizations (super admin sees all, others see their own)."""
    if current_user.role == Role.SUPER_ADMIN:
        rows = db.fetch_all(
            """
            SELECT id, name, slug, logo_url, address, city, state, country,
                   phone, email, website, subscription_tier, is_active, created_at
            FROM organizations
            ORDER BY name
            """
        )
    else:
        rows = db.fetch_all(
            """
            SELECT id, name, slug, logo_url, address, city, state, country,
                   phone, email, website, subscription_tier, is_active, created_at
            FROM organizations WHERE id = ?
            """,
            (current_user.org_id,)
        )
    
    return [
        OrganizationResponse(
            id=r[0], name=r[1], slug=r[2], logo_url=r[3], address=r[4],
            city=r[5], state=r[6], country=r[7], phone=r[8], email=r[9],
            website=r[10], subscription_tier=r[11], is_active=bool(r[12]),
            created_at=str(r[13])
        )
        for r in rows
    ]


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    current_user: CurrentUser,
    db: Db
):
    """Get organization details."""
    if current_user.role != Role.SUPER_ADMIN and org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    row = db.fetch_one(
        """
        SELECT id, name, slug, logo_url, address, city, state, country,
               phone, email, website, subscription_tier, is_active, created_at
        FROM organizations WHERE id = ?
        """,
        (org_id,)
    )
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    return OrganizationResponse(
        id=row[0], name=row[1], slug=row[2], logo_url=row[3], address=row[4],
        city=row[5], state=row[6], country=row[7], phone=row[8], email=row[9],
        website=row[10], subscription_tier=row[11], is_active=bool(row[12]),
        created_at=str(row[13])
    )


@router.put(
    "/{org_id}",
    response_model=OrganizationResponse,
    dependencies=[Depends(PermissionChecker(Permission.ORG_UPDATE))]
)
async def update_organization(
    org_id: str,
    request: OrganizationUpdateRequest,
    current_user: CurrentUser,
    db: Db
):
    """Update organization details."""
    if current_user.role != Role.SUPER_ADMIN and org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    updates = []
    params = []
    
    for field in ["name", "logo_url", "address", "city", "state", "country", "phone", "email", "website"]:
        value = getattr(request, field)
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(value)
    
    if updates:
        updates.append("updated_at = ?")
        params.append(datetime.utcnow())
        params.append(org_id)
        
        db.execute(
            f"UPDATE organizations SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
        db.commit()
        db.sync()
    
    return await get_organization(org_id, current_user, db)


@router.get("/{org_id}/stats", response_model=OrganizationStatsResponse)
async def get_organization_stats(
    org_id: str,
    current_user: CurrentUser,
    db: Db
):
    """Get organization statistics."""
    if current_user.role != Role.SUPER_ADMIN and org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Users count
    users = db.fetch_one("SELECT COUNT(*) FROM users WHERE organization_id = ?", (org_id,))
    
    # Equipment count
    equipment = db.fetch_one("SELECT COUNT(*) FROM equipment WHERE organization_id = ?", (org_id,))
    
    # Work orders
    wo_total = db.fetch_one("SELECT COUNT(*) FROM work_orders WHERE organization_id = ?", (org_id,))
    wo_pending = db.fetch_one(
        "SELECT COUNT(*) FROM work_orders WHERE organization_id = ? AND status IN ('pending', 'in_progress')",
        (org_id,)
    )
    wo_completed = db.fetch_one(
        "SELECT COUNT(*) FROM work_orders WHERE organization_id = ? AND status = 'completed'",
        (org_id,)
    )
    
    # Parts
    parts_total = db.fetch_one("SELECT COUNT(*) FROM parts_inventory WHERE organization_id = ?", (org_id,))
    parts_low = db.fetch_one(
        "SELECT COUNT(*) FROM parts_inventory WHERE organization_id = ? AND quantity_in_stock <= minimum_stock_level",
        (org_id,)
    )
    
    return OrganizationStatsResponse(
        total_users=users[0] if users else 0,
        total_equipment=equipment[0] if equipment else 0,
        total_work_orders=wo_total[0] if wo_total else 0,
        pending_work_orders=wo_pending[0] if wo_pending else 0,
        completed_work_orders=wo_completed[0] if wo_completed else 0,
        total_parts=parts_total[0] if parts_total else 0,
        low_stock_parts=parts_low[0] if parts_low else 0
    )
