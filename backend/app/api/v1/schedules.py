"""
GearGuard Backend - Maintenance Schedules Endpoints
Preventive maintenance schedule management.
"""
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from ..deps import Db, CurrentUser, Pagination, PermissionChecker
from ...core import generate_id
from ...core.permissions import Permission

router = APIRouter()


class ScheduleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    equipment_id: str
    equipment_name: str
    type: str
    frequency_type: str
    frequency_value: Optional[int]
    frequency_unit: Optional[str]
    priority: str
    assigned_to: Optional[str]
    assigned_to_name: Optional[str]
    last_performed: Optional[str]
    next_due: Optional[str]
    estimated_duration_minutes: Optional[int]
    is_active: bool
    created_at: str


class ScheduleCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    equipment_id: str
    type: str = "preventive"  # preventive, predictive, condition_based
    frequency_type: str  # daily, weekly, monthly, yearly, meter_based
    frequency_value: Optional[int] = None
    frequency_unit: Optional[str] = None
    meter_threshold: Optional[float] = None
    priority: str = "medium"
    assigned_to: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    checklist_template_id: Optional[str] = None


class ScheduleUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    frequency_type: Optional[str] = None
    frequency_value: Optional[int] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    is_active: Optional[bool] = None


def calculate_next_due(frequency_type: str, frequency_value: int, last_performed: datetime = None) -> datetime:
    """Calculate next due date based on frequency."""
    base = last_performed or datetime.utcnow()
    
    if frequency_type == "daily":
        return base + timedelta(days=frequency_value or 1)
    elif frequency_type == "weekly":
        return base + timedelta(weeks=frequency_value or 1)
    elif frequency_type == "monthly":
        return base + timedelta(days=30 * (frequency_value or 1))
    elif frequency_type == "yearly":
        return base + timedelta(days=365 * (frequency_value or 1))
    else:
        return base + timedelta(days=30)  # Default


@router.post(
    "",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(Permission.SCHEDULE_CREATE))]
)
async def create_schedule(request: ScheduleCreateRequest, current_user: CurrentUser, db: Db):
    """Create a new maintenance schedule."""
    schedule_id = generate_id()
    now = datetime.utcnow()
    next_due = calculate_next_due(request.frequency_type, request.frequency_value)
    
    db.execute(
        """
        INSERT INTO maintenance_schedules (
            id, organization_id, equipment_id, name, description, type,
            frequency_type, frequency_value, frequency_unit, meter_threshold,
            next_due, estimated_duration_minutes, priority, assigned_to,
            checklist_template_id, is_active, created_by, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            schedule_id, current_user.org_id, request.equipment_id, request.name,
            request.description, request.type, request.frequency_type, request.frequency_value,
            request.frequency_unit, request.meter_threshold, next_due,
            request.estimated_duration_minutes, request.priority, request.assigned_to,
            request.checklist_template_id, True, current_user.sub, now, now
        )
    )
    db.commit()
    db.sync()
    
    return await get_schedule(schedule_id, current_user, db)


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(
    current_user: CurrentUser,
    db: Db,
    equipment_id: Optional[str] = Query(None),
    is_active: bool = Query(True)
):
    """List all maintenance schedules."""
    where_clauses = ["s.organization_id = ?", "s.is_active = ?"]
    params = [current_user.org_id, is_active]
    
    if equipment_id:
        where_clauses.append("s.equipment_id = ?")
        params.append(equipment_id)
    
    rows = db.fetch_all(
        f"""
        SELECT s.id, s.name, s.description, s.equipment_id, e.name, s.type,
               s.frequency_type, s.frequency_value, s.frequency_unit, s.priority,
               s.assigned_to, u.first_name || ' ' || u.last_name,
               s.last_performed, s.next_due, s.estimated_duration_minutes,
               s.is_active, s.created_at
        FROM maintenance_schedules s
        JOIN equipment e ON s.equipment_id = e.id
        LEFT JOIN users u ON s.assigned_to = u.id
        WHERE {' AND '.join(where_clauses)}
        ORDER BY s.next_due
        """,
        tuple(params)
    )
    
    return [
        ScheduleResponse(
            id=r[0], name=r[1], description=r[2], equipment_id=r[3], equipment_name=r[4],
            type=r[5], frequency_type=r[6], frequency_value=r[7], frequency_unit=r[8],
            priority=r[9], assigned_to=r[10], assigned_to_name=r[11],
            last_performed=str(r[12]) if r[12] else None, next_due=str(r[13]) if r[13] else None,
            estimated_duration_minutes=r[14], is_active=bool(r[15]), created_at=str(r[16])
        )
        for r in rows
    ]


@router.get("/upcoming", response_model=List[ScheduleResponse])
async def get_upcoming_maintenance(
    current_user: CurrentUser,
    db: Db,
    days: int = Query(7, ge=1, le=90)
):
    """Get maintenance schedules due in the next N days."""
    future_date = datetime.utcnow() + timedelta(days=days)
    
    rows = db.fetch_all(
        """
        SELECT s.id, s.name, s.description, s.equipment_id, e.name, s.type,
               s.frequency_type, s.frequency_value, s.frequency_unit, s.priority,
               s.assigned_to, u.first_name || ' ' || u.last_name,
               s.last_performed, s.next_due, s.estimated_duration_minutes,
               s.is_active, s.created_at
        FROM maintenance_schedules s
        JOIN equipment e ON s.equipment_id = e.id
        LEFT JOIN users u ON s.assigned_to = u.id
        WHERE s.organization_id = ? AND s.is_active = TRUE AND s.next_due <= ?
        ORDER BY s.next_due
        """,
        (current_user.org_id, future_date)
    )
    
    return [
        ScheduleResponse(
            id=r[0], name=r[1], description=r[2], equipment_id=r[3], equipment_name=r[4],
            type=r[5], frequency_type=r[6], frequency_value=r[7], frequency_unit=r[8],
            priority=r[9], assigned_to=r[10], assigned_to_name=r[11],
            last_performed=str(r[12]) if r[12] else None, next_due=str(r[13]) if r[13] else None,
            estimated_duration_minutes=r[14], is_active=bool(r[15]), created_at=str(r[16])
        )
        for r in rows
    ]


@router.get("/overdue", response_model=List[ScheduleResponse])
async def get_overdue_maintenance(current_user: CurrentUser, db: Db):
    """Get overdue maintenance schedules."""
    now = datetime.utcnow()
    
    rows = db.fetch_all(
        """
        SELECT s.id, s.name, s.description, s.equipment_id, e.name, s.type,
               s.frequency_type, s.frequency_value, s.frequency_unit, s.priority,
               s.assigned_to, u.first_name || ' ' || u.last_name,
               s.last_performed, s.next_due, s.estimated_duration_minutes,
               s.is_active, s.created_at
        FROM maintenance_schedules s
        JOIN equipment e ON s.equipment_id = e.id
        LEFT JOIN users u ON s.assigned_to = u.id
        WHERE s.organization_id = ? AND s.is_active = TRUE AND s.next_due < ?
        ORDER BY s.next_due
        """,
        (current_user.org_id, now)
    )
    
    return [
        ScheduleResponse(
            id=r[0], name=r[1], description=r[2], equipment_id=r[3], equipment_name=r[4],
            type=r[5], frequency_type=r[6], frequency_value=r[7], frequency_unit=r[8],
            priority=r[9], assigned_to=r[10], assigned_to_name=r[11],
            last_performed=str(r[12]) if r[12] else None, next_due=str(r[13]) if r[13] else None,
            estimated_duration_minutes=r[14], is_active=bool(r[15]), created_at=str(r[16])
        )
        for r in rows
    ]


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(schedule_id: str, current_user: CurrentUser, db: Db):
    """Get schedule details."""
    row = db.fetch_one(
        """
        SELECT s.id, s.name, s.description, s.equipment_id, e.name, s.type,
               s.frequency_type, s.frequency_value, s.frequency_unit, s.priority,
               s.assigned_to, u.first_name || ' ' || u.last_name,
               s.last_performed, s.next_due, s.estimated_duration_minutes,
               s.is_active, s.created_at
        FROM maintenance_schedules s
        JOIN equipment e ON s.equipment_id = e.id
        LEFT JOIN users u ON s.assigned_to = u.id
        WHERE s.id = ? AND s.organization_id = ?
        """,
        (schedule_id, current_user.org_id)
    )
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    
    return ScheduleResponse(
        id=row[0], name=row[1], description=row[2], equipment_id=row[3], equipment_name=row[4],
        type=row[5], frequency_type=row[6], frequency_value=row[7], frequency_unit=row[8],
        priority=row[9], assigned_to=row[10], assigned_to_name=row[11],
        last_performed=str(row[12]) if row[12] else None, next_due=str(row[13]) if row[13] else None,
        estimated_duration_minutes=row[14], is_active=bool(row[15]), created_at=str(row[16])
    )


@router.post(
    "/{schedule_id}/generate-workorder",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(Permission.WORKORDER_CREATE))]
)
async def generate_work_order_from_schedule(schedule_id: str, current_user: CurrentUser, db: Db):
    """Generate a work order from a maintenance schedule."""
    # Get schedule
    schedule = db.fetch_one(
        """
        SELECT s.name, s.description, s.equipment_id, s.priority, s.assigned_to,
               s.estimated_duration_minutes, s.checklist_template_id, s.frequency_type, s.frequency_value
        FROM maintenance_schedules s
        WHERE s.id = ? AND s.organization_id = ?
        """,
        (schedule_id, current_user.org_id)
    )
    
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    
    wo_id = generate_id()
    wo_number = f"WO-{datetime.utcnow().strftime('%Y%m%d')}-{wo_id[:6].upper()}"
    now = datetime.utcnow()
    
    db.execute(
        """
        INSERT INTO work_orders (
            id, organization_id, equipment_id, schedule_id, work_order_number,
            title, description, type, status, priority, assigned_to,
            estimated_hours, checklist_template_id, created_by, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            wo_id, current_user.org_id, schedule[2], schedule_id, wo_number,
            f"PM: {schedule[0]}", schedule[1], "preventive", "pending", schedule[3],
            schedule[4], (schedule[5] or 60) / 60, schedule[6], current_user.sub, now, now
        )
    )
    
    # Update schedule - set last performed and calculate next due
    next_due = calculate_next_due(schedule[7], schedule[8], now)
    db.execute(
        """
        UPDATE maintenance_schedules 
        SET last_performed = ?, next_due = ?, updated_at = ?
        WHERE id = ?
        """,
        (now, next_due, now, schedule_id)
    )
    
    db.commit()
    db.sync()
    
    return {"message": "Work order generated", "work_order_id": wo_id, "work_order_number": wo_number}


@router.put(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    dependencies=[Depends(PermissionChecker(Permission.SCHEDULE_UPDATE))]
)
async def update_schedule(schedule_id: str, request: ScheduleUpdateRequest, current_user: CurrentUser, db: Db):
    """Update a schedule."""
    updates = []
    params = []
    
    for field in ["name", "description", "frequency_type", "frequency_value", "priority", "assigned_to", "is_active"]:
        value = getattr(request, field, None)
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(value)
    
    if updates:
        updates.append("updated_at = ?")
        params.extend([datetime.utcnow(), schedule_id, current_user.org_id])
        db.execute(
            f"UPDATE maintenance_schedules SET {', '.join(updates)} WHERE id = ? AND organization_id = ?",
            tuple(params)
        )
        db.commit()
        db.sync()
    
    return await get_schedule(schedule_id, current_user, db)


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(Permission.SCHEDULE_DELETE))]
)
async def delete_schedule(schedule_id: str, current_user: CurrentUser, db: Db):
    """Deactivate a schedule."""
    db.execute(
        "UPDATE maintenance_schedules SET is_active = FALSE, updated_at = ? WHERE id = ? AND organization_id = ?",
        (datetime.utcnow(), schedule_id, current_user.org_id)
    )
    db.commit()
    db.sync()
