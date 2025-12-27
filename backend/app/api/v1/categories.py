"""
GearGuard Backend - Categories Endpoints
Equipment category management.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..deps import Db, CurrentUser, PermissionChecker
from ...core import generate_id
from ...core.permissions import Permission

router = APIRouter()


class CategoryResponse(BaseModel):
    id: str
    name: str
    code: Optional[str]
    description: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    parent_category_id: Optional[str]
    parent_category_name: Optional[str]
    equipment_count: int
    created_at: str


class CategoryCreateRequest(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    parent_category_id: Optional[str] = None


class CategoryUpdateRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(Permission.EQUIPMENT_CREATE))]
)
async def create_category(request: CategoryCreateRequest, current_user: CurrentUser, db: Db):
    """Create a new equipment category."""
    cat_id = generate_id()
    now = datetime.utcnow()
    
    db.execute(
        """
        INSERT INTO equipment_categories (id, organization_id, name, code, description, icon, color, parent_category_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (cat_id, current_user.org_id, request.name, request.code, request.description,
         request.icon, request.color, request.parent_category_id, now)
    )
    db.commit()
    db.sync()
    
    return await get_category(cat_id, current_user, db)


@router.get("", response_model=List[CategoryResponse])
async def list_categories(current_user: CurrentUser, db: Db):
    """List all equipment categories."""
    rows = db.fetch_all(
        """
        SELECT c.id, c.name, c.code, c.description, c.icon, c.color,
               c.parent_category_id, p.name, c.created_at,
               (SELECT COUNT(*) FROM equipment WHERE category_id = c.id)
        FROM equipment_categories c
        LEFT JOIN equipment_categories p ON c.parent_category_id = p.id
        WHERE c.organization_id = ?
        ORDER BY c.name
        """,
        (current_user.org_id,)
    )
    
    return [
        CategoryResponse(
            id=r[0], name=r[1], code=r[2], description=r[3], icon=r[4], color=r[5],
            parent_category_id=r[6], parent_category_name=r[7], created_at=str(r[8]),
            equipment_count=r[9]
        )
        for r in rows
    ]


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: str, current_user: CurrentUser, db: Db):
    """Get category details."""
    row = db.fetch_one(
        """
        SELECT c.id, c.name, c.code, c.description, c.icon, c.color,
               c.parent_category_id, p.name, c.created_at,
               (SELECT COUNT(*) FROM equipment WHERE category_id = c.id)
        FROM equipment_categories c
        LEFT JOIN equipment_categories p ON c.parent_category_id = p.id
        WHERE c.id = ? AND c.organization_id = ?
        """,
        (category_id, current_user.org_id)
    )
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    return CategoryResponse(
        id=row[0], name=row[1], code=row[2], description=row[3], icon=row[4], color=row[5],
        parent_category_id=row[6], parent_category_name=row[7], created_at=str(row[8]),
        equipment_count=row[9]
    )


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    dependencies=[Depends(PermissionChecker(Permission.EQUIPMENT_UPDATE))]
)
async def update_category(category_id: str, request: CategoryUpdateRequest, current_user: CurrentUser, db: Db):
    """Update a category."""
    updates = []
    params = []
    
    for field in ["name", "code", "description", "icon", "color"]:
        value = getattr(request, field, None)
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(value)
    
    if updates:
        params.extend([category_id, current_user.org_id])
        db.execute(
            f"UPDATE equipment_categories SET {', '.join(updates)} WHERE id = ? AND organization_id = ?",
            tuple(params)
        )
        db.commit()
        db.sync()
    
    return await get_category(category_id, current_user, db)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(Permission.EQUIPMENT_DELETE))]
)
async def delete_category(category_id: str, current_user: CurrentUser, db: Db):
    """Delete a category."""
    # Check if category has equipment
    count = db.fetch_one(
        "SELECT COUNT(*) FROM equipment WHERE category_id = ?",
        (category_id,)
    )
    if count and count[0] > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category with associated equipment"
        )
    
    db.execute(
        "DELETE FROM equipment_categories WHERE id = ? AND organization_id = ?",
        (category_id, current_user.org_id)
    )
    db.commit()
    db.sync()
