"""
GearGuard Backend - Locations Endpoints
Location/facility management operations.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from ..deps import Db, CurrentUser, Pagination, PermissionChecker
from ...core import generate_id
from ...core.permissions import Permission

router = APIRouter()


class LocationResponse(BaseModel):
    id: str
    name: str
    code: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    type: Optional[str]
    parent_location_id: Optional[str]
    parent_location_name: Optional[str]
    is_active: bool
    created_at: str


class LocationCreateRequest(BaseModel):
    name: str
    code: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    type: Optional[str] = None  # site, building, floor, room, area
    parent_location_id: Optional[str] = None


class LocationUpdateRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    type: Optional[str] = None
    is_active: Optional[bool] = None


@router.post(
    "",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(Permission.EQUIPMENT_CREATE))]
)
async def create_location(
    request: LocationCreateRequest,
    current_user: CurrentUser,
    db: Db
):
    """Create a new location."""
    location_id = generate_id()
    now = datetime.utcnow()
    
    db.execute(
        """
        INSERT INTO locations (
            id, organization_id, name, code, address, city, state, country,
            postal_code, latitude, longitude, type, parent_location_id,
            is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            location_id, current_user.org_id, request.name, request.code,
            request.address, request.city, request.state, request.country,
            request.postal_code, request.latitude, request.longitude,
            request.type, request.parent_location_id, True, now, now
        )
    )
    db.commit()
    db.sync()
    
    return await get_location(location_id, current_user, db)


@router.get("", response_model=List[LocationResponse])
async def list_locations(
    current_user: CurrentUser,
    db: Db,
    type: Optional[str] = Query(None),
    parent_id: Optional[str] = Query(None),
    is_active: bool = Query(True)
):
    """List all locations in the organization."""
    where_clauses = ["l.organization_id = ?", "l.is_active = ?"]
    params = [current_user.org_id, is_active]
    
    if type:
        where_clauses.append("l.type = ?")
        params.append(type)
    
    if parent_id:
        where_clauses.append("l.parent_location_id = ?")
        params.append(parent_id)
    
    rows = db.fetch_all(
        f"""
        SELECT l.id, l.name, l.code, l.address, l.city, l.state, l.country,
               l.type, l.parent_location_id, p.name as parent_name,
               l.is_active, l.created_at
        FROM locations l
        LEFT JOIN locations p ON l.parent_location_id = p.id
        WHERE {' AND '.join(where_clauses)}
        ORDER BY l.name
        """,
        tuple(params)
    )
    
    return [
        LocationResponse(
            id=r[0], name=r[1], code=r[2], address=r[3], city=r[4],
            state=r[5], country=r[6], type=r[7], parent_location_id=r[8],
            parent_location_name=r[9], is_active=bool(r[10]), created_at=str(r[11])
        )
        for r in rows
    ]


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: str,
    current_user: CurrentUser,
    db: Db
):
    """Get a specific location."""
    row = db.fetch_one(
        """
        SELECT l.id, l.name, l.code, l.address, l.city, l.state, l.country,
               l.type, l.parent_location_id, p.name as parent_name,
               l.is_active, l.created_at
        FROM locations l
        LEFT JOIN locations p ON l.parent_location_id = p.id
        WHERE l.id = ? AND l.organization_id = ?
        """,
        (location_id, current_user.org_id)
    )
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    
    return LocationResponse(
        id=row[0], name=row[1], code=row[2], address=row[3], city=row[4],
        state=row[5], country=row[6], type=row[7], parent_location_id=row[8],
        parent_location_name=row[9], is_active=bool(row[10]), created_at=str(row[11])
    )


@router.put(
    "/{location_id}",
    response_model=LocationResponse,
    dependencies=[Depends(PermissionChecker(Permission.EQUIPMENT_UPDATE))]
)
async def update_location(
    location_id: str,
    request: LocationUpdateRequest,
    current_user: CurrentUser,
    db: Db
):
    """Update a location."""
    updates = []
    params = []
    
    for field in ["name", "code", "address", "city", "state", "country", "type", "is_active"]:
        value = getattr(request, field, None)
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(value)
    
    if updates:
        updates.append("updated_at = ?")
        params.extend([datetime.utcnow(), location_id, current_user.org_id])
        
        db.execute(
            f"UPDATE locations SET {', '.join(updates)} WHERE id = ? AND organization_id = ?",
            tuple(params)
        )
        db.commit()
        db.sync()
    
    return await get_location(location_id, current_user, db)


@router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(Permission.EQUIPMENT_DELETE))]
)
async def delete_location(
    location_id: str,
    current_user: CurrentUser,
    db: Db
):
    """Soft delete a location."""
    db.execute(
        "UPDATE locations SET is_active = FALSE, updated_at = ? WHERE id = ? AND organization_id = ?",
        (datetime.utcnow(), location_id, current_user.org_id)
    )
    db.commit()
    db.sync()
