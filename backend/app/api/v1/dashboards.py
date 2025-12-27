"""
GearGuard Backend - Dashboards Endpoints
Custom dashboard management.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import json

from ..deps import Db, CurrentUser
from ...core import generate_id

router = APIRouter()


class DashboardResponse(BaseModel):
    id: str
    name: str
    layout: dict
    is_default: bool
    is_public: bool
    created_at: str


class DashboardCreateRequest(BaseModel):
    name: str
    layout: dict
    is_default: bool = False
    is_public: bool = False


class DashboardUpdateRequest(BaseModel):
    name: Optional[str] = None
    layout: Optional[dict] = None
    is_default: Optional[bool] = None


@router.get("", response_model=List[DashboardResponse])
async def list_dashboards(current_user: CurrentUser, db: Db):
    """Get user's dashboards."""
    rows = db.fetch_all(
        """SELECT id, name, layout, is_default, is_public, created_at FROM dashboards
        WHERE organization_id = ? AND (user_id = ? OR is_public = TRUE) ORDER BY is_default DESC, name""",
        (current_user.org_id, current_user.sub)
    )
    return [DashboardResponse(
        id=r[0], name=r[1], layout=json.loads(r[2]) if r[2] else {},
        is_default=bool(r[3]), is_public=bool(r[4]), created_at=str(r[5])
    ) for r in rows]


@router.post("", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(request: DashboardCreateRequest, current_user: CurrentUser, db: Db):
    """Create a custom dashboard."""
    dash_id = generate_id()
    now = datetime.utcnow()
    
    if request.is_default:
        db.execute("UPDATE dashboards SET is_default = FALSE WHERE user_id = ?", (current_user.sub,))
    
    db.execute(
        """INSERT INTO dashboards (id, organization_id, user_id, name, layout, is_default, is_public, created_by, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (dash_id, current_user.org_id, current_user.sub, request.name, json.dumps(request.layout),
         request.is_default, request.is_public, current_user.sub, now, now)
    )
    db.commit()
    db.sync()
    return await get_dashboard(dash_id, current_user, db)


@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(dashboard_id: str, current_user: CurrentUser, db: Db):
    """Get dashboard by ID."""
    row = db.fetch_one(
        "SELECT id, name, layout, is_default, is_public, created_at FROM dashboards WHERE id = ? AND (user_id = ? OR is_public = TRUE)",
        (dashboard_id, current_user.sub)
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    return DashboardResponse(
        id=row[0], name=row[1], layout=json.loads(row[2]) if row[2] else {},
        is_default=bool(row[3]), is_public=bool(row[4]), created_at=str(row[5])
    )


@router.put("/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(dashboard_id: str, request: DashboardUpdateRequest, current_user: CurrentUser, db: Db):
    """Update a dashboard."""
    updates = []
    params = []
    if request.name is not None:
        updates.append("name = ?")
        params.append(request.name)
    if request.layout is not None:
        updates.append("layout = ?")
        params.append(json.dumps(request.layout))
    if request.is_default is not None:
        if request.is_default:
            db.execute("UPDATE dashboards SET is_default = FALSE WHERE user_id = ?", (current_user.sub,))
        updates.append("is_default = ?")
        params.append(request.is_default)
    
    if updates:
        updates.append("updated_at = ?")
        params.extend([datetime.utcnow(), dashboard_id, current_user.sub])
        db.execute(f"UPDATE dashboards SET {', '.join(updates)} WHERE id = ? AND user_id = ?", tuple(params))
        db.commit()
        db.sync()
    return await get_dashboard(dashboard_id, current_user, db)


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(dashboard_id: str, current_user: CurrentUser, db: Db):
    """Delete a dashboard."""
    db.execute("DELETE FROM dashboards WHERE id = ? AND user_id = ?", (dashboard_id, current_user.sub))
    db.commit()
    db.sync()
