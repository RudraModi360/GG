"""
GearGuard Backend - Equipment Endpoints
Equipment/asset management operations.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from ..deps import Db, CurrentUser, Pagination, PermissionChecker
from ...core import generate_id
from ...core.permissions import Permission

router = APIRouter()


class EquipmentResponse(BaseModel):
    id: str
    name: str
    code: Optional[str]
    serial_number: Optional[str]
    model: Optional[str]
    manufacturer: Optional[str]
    description: Optional[str]
    image_url: Optional[str]
    category_id: Optional[str]
    category_name: Optional[str]
    location_id: Optional[str]
    location_name: Optional[str]
    status: str
    health_score: int
    criticality: str
    purchase_date: Optional[str]
    warranty_expiry: Optional[str]
    last_maintenance_date: Optional[str]
    next_maintenance_date: Optional[str]
    created_at: str


class EquipmentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: Optional[str] = None
    serial_number: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    category_id: Optional[str] = None
    location_id: Optional[str] = None
    status: str = "operational"
    criticality: str = "medium"
    purchase_date: Optional[str] = None
    purchase_cost: Optional[float] = None
    warranty_expiry: Optional[str] = None


class EquipmentUpdateRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    serial_number: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    category_id: Optional[str] = None
    location_id: Optional[str] = None
    status: Optional[str] = None
    health_score: Optional[int] = None
    criticality: Optional[str] = None


class EquipmentListResponse(BaseModel):
    items: List[EquipmentResponse]
    total: int
    page: int
    page_size: int


class MeterReadingRequest(BaseModel):
    meter_type: str  # hours, km, cycles
    reading_value: float
    notes: Optional[str] = None


class MeterReadingResponse(BaseModel):
    id: str
    meter_type: str
    reading_value: float
    recorded_by: str
    recorded_at: str
    notes: Optional[str]


class IssueReportRequest(BaseModel):
    title: str
    description: str
    priority: str = "medium"


@router.post(
    "",
    response_model=EquipmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(Permission.EQUIPMENT_CREATE))]
)
async def create_equipment(
    request: EquipmentCreateRequest,
    current_user: CurrentUser,
    db: Db
):
    """Create new equipment."""
    equipment_id = generate_id()
    now = datetime.utcnow()
    
    db.execute(
        """
        INSERT INTO equipment (
            id, organization_id, name, code, serial_number, model, manufacturer,
            description, image_url, category_id, location_id, status, health_score,
            criticality, purchase_date, purchase_cost, warranty_expiry,
            created_by, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            equipment_id, current_user.org_id, request.name, request.code,
            request.serial_number, request.model, request.manufacturer,
            request.description, request.image_url, request.category_id,
            request.location_id, request.status, 100, request.criticality,
            request.purchase_date, request.purchase_cost, request.warranty_expiry,
            current_user.sub, now, now
        )
    )
    db.commit()
    db.sync()
    
    return await get_equipment(equipment_id, current_user, db)


@router.get("", response_model=EquipmentListResponse)
async def list_equipment(
    current_user: CurrentUser,
    db: Db,
    pagination: Pagination,
    status: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    location_id: Optional[str] = Query(None),
    criticality: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """List all equipment with filters."""
    where_clauses = ["e.organization_id = ?"]
    params = [current_user.org_id]
    
    if status:
        where_clauses.append("e.status = ?")
        params.append(status)
    
    if category_id:
        where_clauses.append("e.category_id = ?")
        params.append(category_id)
    
    if location_id:
        where_clauses.append("e.location_id = ?")
        params.append(location_id)
    
    if criticality:
        where_clauses.append("e.criticality = ?")
        params.append(criticality)
    
    if search:
        where_clauses.append("(e.name LIKE ? OR e.code LIKE ? OR e.serial_number LIKE ?)")
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])
    
    where_sql = " AND ".join(where_clauses)
    
    # Count
    count = db.fetch_one(
        f"SELECT COUNT(*) FROM equipment e WHERE {where_sql}",
        tuple(params)
    )
    
    # Fetch
    params.extend([pagination.limit, pagination.offset])
    rows = db.fetch_all(
        f"""
        SELECT e.id, e.name, e.code, e.serial_number, e.model, e.manufacturer,
               e.description, e.image_url, e.category_id, c.name, e.location_id,
               l.name, e.status, e.health_score, e.criticality, e.purchase_date,
               e.warranty_expiry, e.last_maintenance_date, e.next_maintenance_date,
               e.created_at
        FROM equipment e
        LEFT JOIN equipment_categories c ON e.category_id = c.id
        LEFT JOIN locations l ON e.location_id = l.id
        WHERE {where_sql}
        ORDER BY e.created_at DESC
        LIMIT ? OFFSET ?
        """,
        tuple(params)
    )
    
    items = [
        EquipmentResponse(
            id=r[0], name=r[1], code=r[2], serial_number=r[3], model=r[4],
            manufacturer=r[5], description=r[6], image_url=r[7], category_id=r[8],
            category_name=r[9], location_id=r[10], location_name=r[11], status=r[12],
            health_score=r[13], criticality=r[14], purchase_date=str(r[15]) if r[15] else None,
            warranty_expiry=str(r[16]) if r[16] else None,
            last_maintenance_date=str(r[17]) if r[17] else None,
            next_maintenance_date=str(r[18]) if r[18] else None,
            created_at=str(r[19])
        )
        for r in rows
    ]
    
    return EquipmentListResponse(
        items=items, total=count[0] if count else 0,
        page=pagination.page, page_size=pagination.page_size
    )


@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: str,
    current_user: CurrentUser,
    db: Db
):
    """Get equipment details."""
    row = db.fetch_one(
        """
        SELECT e.id, e.name, e.code, e.serial_number, e.model, e.manufacturer,
               e.description, e.image_url, e.category_id, c.name, e.location_id,
               l.name, e.status, e.health_score, e.criticality, e.purchase_date,
               e.warranty_expiry, e.last_maintenance_date, e.next_maintenance_date,
               e.created_at
        FROM equipment e
        LEFT JOIN equipment_categories c ON e.category_id = c.id
        LEFT JOIN locations l ON e.location_id = l.id
        WHERE e.id = ? AND e.organization_id = ?
        """,
        (equipment_id, current_user.org_id)
    )
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    
    return EquipmentResponse(
        id=row[0], name=row[1], code=row[2], serial_number=row[3], model=row[4],
        manufacturer=row[5], description=row[6], image_url=row[7], category_id=row[8],
        category_name=row[9], location_id=row[10], location_name=row[11], status=row[12],
        health_score=row[13], criticality=row[14], purchase_date=str(row[15]) if row[15] else None,
        warranty_expiry=str(row[16]) if row[16] else None,
        last_maintenance_date=str(row[17]) if row[17] else None,
        next_maintenance_date=str(row[18]) if row[18] else None,
        created_at=str(row[19])
    )


@router.put(
    "/{equipment_id}",
    response_model=EquipmentResponse,
    dependencies=[Depends(PermissionChecker(Permission.EQUIPMENT_UPDATE))]
)
async def update_equipment(
    equipment_id: str,
    request: EquipmentUpdateRequest,
    current_user: CurrentUser,
    db: Db
):
    """Update equipment."""
    updates = []
    params = []
    
    for field in ["name", "code", "serial_number", "model", "manufacturer",
                  "description", "image_url", "category_id", "location_id",
                  "status", "health_score", "criticality"]:
        value = getattr(request, field, None)
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(value)
    
    if updates:
        updates.append("updated_at = ?")
        params.extend([datetime.utcnow(), equipment_id, current_user.org_id])
        
        db.execute(
            f"UPDATE equipment SET {', '.join(updates)} WHERE id = ? AND organization_id = ?",
            tuple(params)
        )
        db.commit()
        db.sync()
    
    return await get_equipment(equipment_id, current_user, db)


@router.delete(
    "/{equipment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(Permission.EQUIPMENT_DELETE))]
)
async def delete_equipment(
    equipment_id: str,
    current_user: CurrentUser,
    db: Db
):
    """Delete equipment (soft delete - set status to retired)."""
    db.execute(
        "UPDATE equipment SET status = 'retired', updated_at = ? WHERE id = ? AND organization_id = ?",
        (datetime.utcnow(), equipment_id, current_user.org_id)
    )
    db.commit()
    db.sync()


@router.post(
    "/{equipment_id}/meter-reading",
    response_model=MeterReadingResponse,
    dependencies=[Depends(PermissionChecker(Permission.EQUIPMENT_UPDATE))]
)
async def add_meter_reading(
    equipment_id: str,
    request: MeterReadingRequest,
    current_user: CurrentUser,
    db: Db
):
    """Add a meter reading to equipment."""
    reading_id = generate_id()
    now = datetime.utcnow()
    
    db.execute(
        """
        INSERT INTO meter_readings (id, equipment_id, meter_type, reading_value, recorded_by, recorded_at, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (reading_id, equipment_id, request.meter_type, request.reading_value,
         current_user.sub, now, request.notes)
    )
    db.commit()
    db.sync()
    
    return MeterReadingResponse(
        id=reading_id, meter_type=request.meter_type, reading_value=request.reading_value,
        recorded_by=current_user.email, recorded_at=str(now), notes=request.notes
    )


@router.post(
    "/{equipment_id}/report-issue",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(Permission.EQUIPMENT_REPORT_ISSUE))]
)
async def report_equipment_issue(
    equipment_id: str,
    request: IssueReportRequest,
    current_user: CurrentUser,
    db: Db
):
    """Report an issue with equipment (creates a work order)."""
    wo_id = generate_id()
    wo_number = f"WO-{datetime.utcnow().strftime('%Y%m%d')}-{wo_id[:6].upper()}"
    now = datetime.utcnow()
    
    db.execute(
        """
        INSERT INTO work_orders (
            id, organization_id, equipment_id, work_order_number, title,
            description, type, status, priority, requested_by, created_by,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            wo_id, current_user.org_id, equipment_id, wo_number, request.title,
            request.description, "corrective", "pending", request.priority,
            current_user.sub, current_user.sub, now, now
        )
    )
    db.commit()
    db.sync()
    
    return {"message": "Issue reported successfully", "work_order_id": wo_id, "work_order_number": wo_number}
