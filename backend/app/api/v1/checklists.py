"""
GearGuard Backend - Checklists Endpoints
Checklist template management.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import json

from ..deps import Db, CurrentUser, PermissionChecker
from ...core import generate_id
from ...core.permissions import Permission

router = APIRouter()


class ChecklistItemSchema(BaseModel):
    order: int
    title: str
    type: str = "checkbox"  # checkbox, text, number, select
    options: Optional[List[str]] = None
    required: bool = True


class ChecklistResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    category: Optional[str]
    items: List[ChecklistItemSchema]
    is_active: bool
    created_at: str


class ChecklistCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    items: List[ChecklistItemSchema]


class ChecklistUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    items: Optional[List[ChecklistItemSchema]] = None
    is_active: Optional[bool] = None


@router.post("", response_model=ChecklistResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(PermissionChecker(Permission.SCHEDULE_CREATE))])
async def create_checklist(request: ChecklistCreateRequest, current_user: CurrentUser, db: Db):
    """Create a new checklist template."""
    checklist_id = generate_id()
    now = datetime.utcnow()
    items_json = json.dumps([item.model_dump() for item in request.items])
    
    db.execute(
        """INSERT INTO checklist_templates (id, organization_id, name, description, category, items, is_active, created_by, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (checklist_id, current_user.org_id, request.name, request.description, request.category, items_json, True, current_user.sub, now, now)
    )
    db.commit()
    db.sync()
    return await get_checklist(checklist_id, current_user, db)


@router.get("", response_model=List[ChecklistResponse])
async def list_checklists(current_user: CurrentUser, db: Db, category: Optional[str] = None):
    """List checklist templates."""
    if category:
        rows = db.fetch_all(
            "SELECT id, name, description, category, items, is_active, created_at FROM checklist_templates WHERE organization_id = ? AND category = ? AND is_active = TRUE ORDER BY name",
            (current_user.org_id, category)
        )
    else:
        rows = db.fetch_all(
            "SELECT id, name, description, category, items, is_active, created_at FROM checklist_templates WHERE organization_id = ? AND is_active = TRUE ORDER BY name",
            (current_user.org_id,)
        )
    return [
        ChecklistResponse(
            id=r[0], name=r[1], description=r[2], category=r[3],
            items=[ChecklistItemSchema(**item) for item in json.loads(r[4])] if r[4] else [],
            is_active=bool(r[5]), created_at=str(r[6])
        ) for r in rows
    ]


@router.get("/{checklist_id}", response_model=ChecklistResponse)
async def get_checklist(checklist_id: str, current_user: CurrentUser, db: Db):
    """Get checklist template details."""
    row = db.fetch_one(
        "SELECT id, name, description, category, items, is_active, created_at FROM checklist_templates WHERE id = ? AND organization_id = ?",
        (checklist_id, current_user.org_id)
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist not found")
    return ChecklistResponse(
        id=row[0], name=row[1], description=row[2], category=row[3],
        items=[ChecklistItemSchema(**item) for item in json.loads(row[4])] if row[4] else [],
        is_active=bool(row[5]), created_at=str(row[6])
    )


@router.put("/{checklist_id}", response_model=ChecklistResponse,
            dependencies=[Depends(PermissionChecker(Permission.SCHEDULE_UPDATE))])
async def update_checklist(checklist_id: str, request: ChecklistUpdateRequest, current_user: CurrentUser, db: Db):
    """Update checklist template."""
    updates = []
    params = []
    if request.name is not None:
        updates.append("name = ?")
        params.append(request.name)
    if request.description is not None:
        updates.append("description = ?")
        params.append(request.description)
    if request.items is not None:
        updates.append("items = ?")
        params.append(json.dumps([item.model_dump() for item in request.items]))
    if request.is_active is not None:
        updates.append("is_active = ?")
        params.append(request.is_active)
    
    if updates:
        updates.append("updated_at = ?")
        params.extend([datetime.utcnow(), checklist_id, current_user.org_id])
        db.execute(f"UPDATE checklist_templates SET {', '.join(updates)} WHERE id = ? AND organization_id = ?", tuple(params))
        db.commit()
        db.sync()
    return await get_checklist(checklist_id, current_user, db)


@router.delete("/{checklist_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(PermissionChecker(Permission.SCHEDULE_DELETE))])
async def delete_checklist(checklist_id: str, current_user: CurrentUser, db: Db):
    """Deactivate checklist template."""
    db.execute("UPDATE checklist_templates SET is_active = FALSE, updated_at = ? WHERE id = ? AND organization_id = ?",
               (datetime.utcnow(), checklist_id, current_user.org_id))
    db.commit()
    db.sync()
