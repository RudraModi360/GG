"""
GearGuard Backend - Parts/Inventory Endpoints
Spare parts inventory management.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from ..deps import Db, CurrentUser, Pagination, PermissionChecker
from ...core import generate_id
from ...core.permissions import Permission

router = APIRouter()


class PartResponse(BaseModel):
    id: str
    name: str
    part_number: Optional[str]
    description: Optional[str]
    category: Optional[str]
    manufacturer: Optional[str]
    unit: str
    quantity_in_stock: int
    minimum_stock_level: int
    reorder_quantity: Optional[int]
    unit_cost: Optional[float]
    storage_location: Optional[str]
    location_id: Optional[str]
    location_name: Optional[str]
    is_low_stock: bool
    created_at: str


class PartCreateRequest(BaseModel):
    name: str
    part_number: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    manufacturer: Optional[str] = None
    unit: str = "piece"
    quantity_in_stock: int = 0
    minimum_stock_level: int = 0
    reorder_quantity: Optional[int] = None
    unit_cost: Optional[float] = None
    storage_location: Optional[str] = None
    location_id: Optional[str] = None


class PartUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    unit_cost: Optional[float] = None
    minimum_stock_level: Optional[int] = None
    storage_location: Optional[str] = None


class StockAdjustRequest(BaseModel):
    quantity_change: int  # Positive for adding, negative for removing
    reason: str


class PartListResponse(BaseModel):
    items: List[PartResponse]
    total: int
    page: int
    page_size: int


@router.post("", response_model=PartResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(PermissionChecker(Permission.PARTS_CREATE))])
async def create_part(request: PartCreateRequest, current_user: CurrentUser, db: Db):
    """Create a new part."""
    part_id = generate_id()
    now = datetime.utcnow()
    
    db.execute(
        """INSERT INTO parts_inventory (id, organization_id, name, part_number, description, category,
               manufacturer, unit, quantity_in_stock, minimum_stock_level, reorder_quantity,
               unit_cost, storage_location, location_id, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (part_id, current_user.org_id, request.name, request.part_number, request.description,
         request.category, request.manufacturer, request.unit, request.quantity_in_stock,
         request.minimum_stock_level, request.reorder_quantity, request.unit_cost,
         request.storage_location, request.location_id, True, now, now)
    )
    db.commit()
    db.sync()
    return await get_part(part_id, current_user, db)


@router.get("", response_model=PartListResponse)
async def list_parts(current_user: CurrentUser, db: Db, pagination: Pagination,
                     category: Optional[str] = Query(None), search: Optional[str] = Query(None),
                     low_stock_only: bool = Query(False)):
    """List parts inventory."""
    where_clauses = ["p.organization_id = ?", "p.is_active = TRUE"]
    params = [current_user.org_id]
    
    if category:
        where_clauses.append("p.category = ?")
        params.append(category)
    if search:
        where_clauses.append("(p.name LIKE ? OR p.part_number LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if low_stock_only:
        where_clauses.append("p.quantity_in_stock <= p.minimum_stock_level")
    
    where_sql = " AND ".join(where_clauses)
    count = db.fetch_one(f"SELECT COUNT(*) FROM parts_inventory p WHERE {where_sql}", tuple(params))
    
    params.extend([pagination.limit, pagination.offset])
    rows = db.fetch_all(
        f"""SELECT p.id, p.name, p.part_number, p.description, p.category, p.manufacturer,
               p.unit, p.quantity_in_stock, p.minimum_stock_level, p.reorder_quantity,
               p.unit_cost, p.storage_location, p.location_id, l.name, p.created_at
        FROM parts_inventory p LEFT JOIN locations l ON p.location_id = l.id
        WHERE {where_sql} ORDER BY p.name LIMIT ? OFFSET ?""", tuple(params)
    )
    
    return PartListResponse(
        items=[PartResponse(
            id=r[0], name=r[1], part_number=r[2], description=r[3], category=r[4],
            manufacturer=r[5], unit=r[6], quantity_in_stock=r[7], minimum_stock_level=r[8],
            reorder_quantity=r[9], unit_cost=r[10], storage_location=r[11], location_id=r[12],
            location_name=r[13], is_low_stock=r[7] <= r[8], created_at=str(r[14])
        ) for r in rows],
        total=count[0] if count else 0, page=pagination.page, page_size=pagination.page_size
    )


@router.get("/low-stock", response_model=List[PartResponse])
async def get_low_stock_parts(current_user: CurrentUser, db: Db):
    """Get parts with low stock."""
    rows = db.fetch_all(
        """SELECT p.id, p.name, p.part_number, p.description, p.category, p.manufacturer,
               p.unit, p.quantity_in_stock, p.minimum_stock_level, p.reorder_quantity,
               p.unit_cost, p.storage_location, p.location_id, l.name, p.created_at
        FROM parts_inventory p LEFT JOIN locations l ON p.location_id = l.id
        WHERE p.organization_id = ? AND p.is_active = TRUE AND p.quantity_in_stock <= p.minimum_stock_level
        ORDER BY (p.minimum_stock_level - p.quantity_in_stock) DESC""", (current_user.org_id,)
    )
    return [PartResponse(
        id=r[0], name=r[1], part_number=r[2], description=r[3], category=r[4], manufacturer=r[5],
        unit=r[6], quantity_in_stock=r[7], minimum_stock_level=r[8], reorder_quantity=r[9],
        unit_cost=r[10], storage_location=r[11], location_id=r[12], location_name=r[13],
        is_low_stock=True, created_at=str(r[14])
    ) for r in rows]


@router.get("/{part_id}", response_model=PartResponse)
async def get_part(part_id: str, current_user: CurrentUser, db: Db):
    """Get part details."""
    row = db.fetch_one(
        """SELECT p.id, p.name, p.part_number, p.description, p.category, p.manufacturer,
               p.unit, p.quantity_in_stock, p.minimum_stock_level, p.reorder_quantity,
               p.unit_cost, p.storage_location, p.location_id, l.name, p.created_at
        FROM parts_inventory p LEFT JOIN locations l ON p.location_id = l.id
        WHERE p.id = ? AND p.organization_id = ?""", (part_id, current_user.org_id)
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")
    return PartResponse(
        id=row[0], name=row[1], part_number=row[2], description=row[3], category=row[4],
        manufacturer=row[5], unit=row[6], quantity_in_stock=row[7], minimum_stock_level=row[8],
        reorder_quantity=row[9], unit_cost=row[10], storage_location=row[11], location_id=row[12],
        location_name=row[13], is_low_stock=row[7] <= row[8], created_at=str(row[14])
    )


@router.post("/{part_id}/adjust-stock", response_model=PartResponse,
             dependencies=[Depends(PermissionChecker(Permission.PARTS_UPDATE))])
async def adjust_stock(part_id: str, request: StockAdjustRequest, current_user: CurrentUser, db: Db):
    """Adjust stock level for a part."""
    db.execute(
        "UPDATE parts_inventory SET quantity_in_stock = quantity_in_stock + ?, updated_at = ? WHERE id = ? AND organization_id = ?",
        (request.quantity_change, datetime.utcnow(), part_id, current_user.org_id)
    )
    db.commit()
    db.sync()
    return await get_part(part_id, current_user, db)


@router.put("/{part_id}", response_model=PartResponse, dependencies=[Depends(PermissionChecker(Permission.PARTS_UPDATE))])
async def update_part(part_id: str, request: PartUpdateRequest, current_user: CurrentUser, db: Db):
    """Update part information."""
    updates = []
    params = []
    for field in ["name", "description", "unit_cost", "minimum_stock_level", "storage_location"]:
        value = getattr(request, field, None)
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(value)
    if updates:
        updates.append("updated_at = ?")
        params.extend([datetime.utcnow(), part_id, current_user.org_id])
        db.execute(f"UPDATE parts_inventory SET {', '.join(updates)} WHERE id = ? AND organization_id = ?", tuple(params))
        db.commit()
        db.sync()
    return await get_part(part_id, current_user, db)


@router.delete("/{part_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(PermissionChecker(Permission.PARTS_DELETE))])
async def delete_part(part_id: str, current_user: CurrentUser, db: Db):
    """Deactivate a part."""
    db.execute("UPDATE parts_inventory SET is_active = FALSE, updated_at = ? WHERE id = ? AND organization_id = ?",
               (datetime.utcnow(), part_id, current_user.org_id))
    db.commit()
    db.sync()
