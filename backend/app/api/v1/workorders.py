"""
GearGuard Backend - Work Orders Endpoints
Work order management operations.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from ..deps import Db, CurrentUser, Pagination, PermissionChecker
from ...core import generate_id
from ...core.permissions import Permission

router = APIRouter()


class WorkOrderResponse(BaseModel):
    id: str
    work_order_number: str
    title: str
    description: Optional[str]
    equipment_id: str
    equipment_name: str
    type: str
    status: str
    priority: str
    assigned_to: Optional[str]
    assigned_to_name: Optional[str]
    assigned_team_id: Optional[str]
    due_date: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    estimated_hours: Optional[float]
    actual_hours: Optional[float]
    created_by: str
    created_at: str


class WorkOrderCreateRequest(BaseModel):
    equipment_id: str
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    type: str = "corrective"  # preventive, corrective, emergency, inspection
    priority: str = "medium"  # low, medium, high, critical
    assigned_to: Optional[str] = None
    assigned_team_id: Optional[str] = None
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    checklist_template_id: Optional[str] = None


class WorkOrderUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None


class WorkOrderListResponse(BaseModel):
    items: List[WorkOrderResponse]
    total: int
    page: int
    page_size: int


class StatusUpdateRequest(BaseModel):
    status: str


class AssignRequest(BaseModel):
    assigned_to: Optional[str] = None
    assigned_team_id: Optional[str] = None


class CommentRequest(BaseModel):
    comment: str
    is_internal: bool = False


class CommentResponse(BaseModel):
    id: str
    user_id: str
    user_name: str
    comment: str
    is_internal: bool
    created_at: str


class TaskResponse(BaseModel):
    id: str
    task_order: int
    title: str
    description: Optional[str]
    status: str
    is_required: bool
    completed_by: Optional[str]
    completed_at: Optional[str]


class TaskUpdateRequest(BaseModel):
    status: str
    notes: Optional[str] = None
    time_spent_minutes: Optional[int] = None


class PartUsageRequest(BaseModel):
    part_id: str
    quantity_used: int
    notes: Optional[str] = None


@router.post(
    "",
    response_model=WorkOrderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(Permission.WORKORDER_CREATE))]
)
async def create_work_order(request: WorkOrderCreateRequest, current_user: CurrentUser, db: Db):
    """Create a new work order."""
    wo_id = generate_id()
    wo_number = f"WO-{datetime.utcnow().strftime('%Y%m%d')}-{wo_id[:6].upper()}"
    now = datetime.utcnow()
    
    db.execute(
        """
        INSERT INTO work_orders (
            id, organization_id, equipment_id, work_order_number, title, description,
            type, status, priority, assigned_to, assigned_team_id, due_date,
            estimated_hours, checklist_template_id, created_by, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            wo_id, current_user.org_id, request.equipment_id, wo_number, request.title,
            request.description, request.type, "pending", request.priority,
            request.assigned_to, request.assigned_team_id, request.due_date,
            request.estimated_hours, request.checklist_template_id, current_user.sub, now, now
        )
    )
    db.commit()
    db.sync()
    
    return await get_work_order(wo_id, current_user, db)


@router.get("", response_model=WorkOrderListResponse)
async def list_work_orders(
    current_user: CurrentUser,
    db: Db,
    pagination: Pagination,
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    equipment_id: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """List work orders with filters."""
    where_clauses = ["w.organization_id = ?"]
    params = [current_user.org_id]
    
    if status:
        where_clauses.append("w.status = ?")
        params.append(status)
    if type:
        where_clauses.append("w.type = ?")
        params.append(type)
    if priority:
        where_clauses.append("w.priority = ?")
        params.append(priority)
    if equipment_id:
        where_clauses.append("w.equipment_id = ?")
        params.append(equipment_id)
    if assigned_to:
        where_clauses.append("w.assigned_to = ?")
        params.append(assigned_to)
    if search:
        where_clauses.append("(w.title LIKE ? OR w.work_order_number LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    
    where_sql = " AND ".join(where_clauses)
    
    count = db.fetch_one(f"SELECT COUNT(*) FROM work_orders w WHERE {where_sql}", tuple(params))
    
    params.extend([pagination.limit, pagination.offset])
    rows = db.fetch_all(
        f"""
        SELECT w.id, w.work_order_number, w.title, w.description, w.equipment_id,
               e.name, w.type, w.status, w.priority, w.assigned_to,
               u.first_name || ' ' || u.last_name, w.assigned_team_id, w.due_date,
               w.started_at, w.completed_at, w.estimated_hours, w.actual_hours,
               w.created_by, w.created_at
        FROM work_orders w
        JOIN equipment e ON w.equipment_id = e.id
        LEFT JOIN users u ON w.assigned_to = u.id
        WHERE {where_sql}
        ORDER BY w.created_at DESC
        LIMIT ? OFFSET ?
        """,
        tuple(params)
    )
    
    return WorkOrderListResponse(
        items=[
            WorkOrderResponse(
                id=r[0], work_order_number=r[1], title=r[2], description=r[3],
                equipment_id=r[4], equipment_name=r[5], type=r[6], status=r[7],
                priority=r[8], assigned_to=r[9], assigned_to_name=r[10],
                assigned_team_id=r[11], due_date=str(r[12]) if r[12] else None,
                started_at=str(r[13]) if r[13] else None, completed_at=str(r[14]) if r[14] else None,
                estimated_hours=r[15], actual_hours=r[16], created_by=r[17], created_at=str(r[18])
            )
            for r in rows
        ],
        total=count[0] if count else 0,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.get("/{wo_id}", response_model=WorkOrderResponse)
async def get_work_order(wo_id: str, current_user: CurrentUser, db: Db):
    """Get work order details."""
    row = db.fetch_one(
        """
        SELECT w.id, w.work_order_number, w.title, w.description, w.equipment_id,
               e.name, w.type, w.status, w.priority, w.assigned_to,
               u.first_name || ' ' || u.last_name, w.assigned_team_id, w.due_date,
               w.started_at, w.completed_at, w.estimated_hours, w.actual_hours,
               w.created_by, w.created_at
        FROM work_orders w
        JOIN equipment e ON w.equipment_id = e.id
        LEFT JOIN users u ON w.assigned_to = u.id
        WHERE w.id = ? AND w.organization_id = ?
        """,
        (wo_id, current_user.org_id)
    )
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    
    return WorkOrderResponse(
        id=row[0], work_order_number=row[1], title=row[2], description=row[3],
        equipment_id=row[4], equipment_name=row[5], type=row[6], status=row[7],
        priority=row[8], assigned_to=row[9], assigned_to_name=row[10],
        assigned_team_id=row[11], due_date=str(row[12]) if row[12] else None,
        started_at=str(row[13]) if row[13] else None, completed_at=str(row[14]) if row[14] else None,
        estimated_hours=row[15], actual_hours=row[16], created_by=row[17], created_at=str(row[18])
    )


@router.put(
    "/{wo_id}/status",
    response_model=WorkOrderResponse,
    dependencies=[Depends(PermissionChecker(Permission.WORKORDER_UPDATE))]
)
async def update_work_order_status(wo_id: str, request: StatusUpdateRequest, current_user: CurrentUser, db: Db):
    """Update work order status."""
    now = datetime.utcnow()
    updates = ["status = ?", "updated_at = ?"]
    params = [request.status, now]
    
    if request.status == "in_progress":
        updates.append("started_at = COALESCE(started_at, ?)")
        params.append(now)
    elif request.status == "completed":
        updates.append("completed_at = ?")
        params.append(now)
    
    params.extend([wo_id, current_user.org_id])
    db.execute(
        f"UPDATE work_orders SET {', '.join(updates)} WHERE id = ? AND organization_id = ?",
        tuple(params)
    )
    db.commit()
    db.sync()
    
    return await get_work_order(wo_id, current_user, db)


@router.put(
    "/{wo_id}/assign",
    response_model=WorkOrderResponse,
    dependencies=[Depends(PermissionChecker(Permission.WORKORDER_ASSIGN))]
)
async def assign_work_order(wo_id: str, request: AssignRequest, current_user: CurrentUser, db: Db):
    """Assign work order to user or team."""
    db.execute(
        """
        UPDATE work_orders 
        SET assigned_to = ?, assigned_team_id = ?, updated_at = ?
        WHERE id = ? AND organization_id = ?
        """,
        (request.assigned_to, request.assigned_team_id, datetime.utcnow(), wo_id, current_user.org_id)
    )
    db.commit()
    db.sync()
    
    return await get_work_order(wo_id, current_user, db)


@router.post("/{wo_id}/start", response_model=WorkOrderResponse)
async def start_work_order(wo_id: str, current_user: CurrentUser, db: Db):
    """Start working on a work order."""
    return await update_work_order_status(wo_id, StatusUpdateRequest(status="in_progress"), current_user, db)


@router.post(
    "/{wo_id}/complete",
    response_model=WorkOrderResponse,
    dependencies=[Depends(PermissionChecker(Permission.WORKORDER_COMPLETE))]
)
async def complete_work_order(wo_id: str, current_user: CurrentUser, db: Db):
    """Mark work order as complete."""
    return await update_work_order_status(wo_id, StatusUpdateRequest(status="completed"), current_user, db)


@router.get("/{wo_id}/comments", response_model=List[CommentResponse])
async def get_work_order_comments(wo_id: str, current_user: CurrentUser, db: Db):
    """Get work order comments."""
    rows = db.fetch_all(
        """
        SELECT c.id, c.user_id, u.first_name || ' ' || u.last_name, c.comment,
               c.is_internal, c.created_at
        FROM work_order_comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.work_order_id = ?
        ORDER BY c.created_at
        """,
        (wo_id,)
    )
    
    return [
        CommentResponse(
            id=r[0], user_id=r[1], user_name=r[2], comment=r[3],
            is_internal=bool(r[4]), created_at=str(r[5])
        )
        for r in rows
    ]


@router.post("/{wo_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def add_work_order_comment(wo_id: str, request: CommentRequest, current_user: CurrentUser, db: Db):
    """Add a comment to a work order."""
    comment_id = generate_id()
    now = datetime.utcnow()
    
    db.execute(
        """
        INSERT INTO work_order_comments (id, work_order_id, user_id, comment, is_internal, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (comment_id, wo_id, current_user.sub, request.comment, request.is_internal, now, now)
    )
    db.commit()
    db.sync()
    
    return CommentResponse(
        id=comment_id, user_id=current_user.sub, user_name=current_user.email,
        comment=request.comment, is_internal=request.is_internal, created_at=str(now)
    )


@router.get("/{wo_id}/tasks", response_model=List[TaskResponse])
async def get_work_order_tasks(wo_id: str, current_user: CurrentUser, db: Db):
    """Get work order tasks."""
    rows = db.fetch_all(
        """
        SELECT id, task_order, title, description, status, is_required, completed_by, completed_at
        FROM work_order_tasks
        WHERE work_order_id = ?
        ORDER BY task_order
        """,
        (wo_id,)
    )
    
    return [
        TaskResponse(
            id=r[0], task_order=r[1], title=r[2], description=r[3], status=r[4],
            is_required=bool(r[5]), completed_by=r[6], completed_at=str(r[7]) if r[7] else None
        )
        for r in rows
    ]


@router.put("/{wo_id}/tasks/{task_id}", response_model=TaskResponse)
async def update_work_order_task(wo_id: str, task_id: str, request: TaskUpdateRequest, current_user: CurrentUser, db: Db):
    """Update a work order task."""
    now = datetime.utcnow()
    
    completed_by = current_user.sub if request.status == "completed" else None
    completed_at = now if request.status == "completed" else None
    
    db.execute(
        """
        UPDATE work_order_tasks
        SET status = ?, notes = ?, time_spent_minutes = ?, completed_by = ?, completed_at = ?
        WHERE id = ? AND work_order_id = ?
        """,
        (request.status, request.notes, request.time_spent_minutes, completed_by, completed_at, task_id, wo_id)
    )
    db.commit()
    db.sync()
    
    row = db.fetch_one(
        "SELECT id, task_order, title, description, status, is_required, completed_by, completed_at FROM work_order_tasks WHERE id = ?",
        (task_id,)
    )
    
    return TaskResponse(
        id=row[0], task_order=row[1], title=row[2], description=row[3], status=row[4],
        is_required=bool(row[5]), completed_by=row[6], completed_at=str(row[7]) if row[7] else None
    )


@router.post(
    "/{wo_id}/parts",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(Permission.PARTS_USE))]
)
async def add_parts_to_work_order(wo_id: str, request: PartUsageRequest, current_user: CurrentUser, db: Db):
    """Record parts usage for a work order."""
    # Get part info
    part = db.fetch_one(
        "SELECT unit_cost, quantity_in_stock FROM parts_inventory WHERE id = ?",
        (request.part_id,)
    )
    if not part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")
    
    if part[1] < request.quantity_used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient stock")
    
    usage_id = generate_id()
    now = datetime.utcnow()
    
    # Record usage
    db.execute(
        """
        INSERT INTO parts_usage (id, work_order_id, part_id, quantity_used, unit_cost_at_time, used_by, used_at, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (usage_id, wo_id, request.part_id, request.quantity_used, part[0], current_user.sub, now, request.notes)
    )
    
    # Update stock
    db.execute(
        "UPDATE parts_inventory SET quantity_in_stock = quantity_in_stock - ?, updated_at = ? WHERE id = ?",
        (request.quantity_used, now, request.part_id)
    )
    
    db.commit()
    db.sync()
    
    return {"message": "Parts usage recorded", "usage_id": usage_id}


@router.put(
    "/{wo_id}",
    response_model=WorkOrderResponse,
    dependencies=[Depends(PermissionChecker(Permission.WORKORDER_UPDATE))]
)
async def update_work_order(wo_id: str, request: WorkOrderUpdateRequest, current_user: CurrentUser, db: Db):
    """Update work order."""
    updates = []
    params = []
    
    for field in ["title", "description", "priority", "due_date", "estimated_hours"]:
        value = getattr(request, field, None)
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(value)
    
    if updates:
        updates.append("updated_at = ?")
        params.extend([datetime.utcnow(), wo_id, current_user.org_id])
        db.execute(
            f"UPDATE work_orders SET {', '.join(updates)} WHERE id = ? AND organization_id = ?",
            tuple(params)
        )
        db.commit()
        db.sync()
    
    return await get_work_order(wo_id, current_user, db)


@router.delete(
    "/{wo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(Permission.WORKORDER_DELETE))]
)
async def delete_work_order(wo_id: str, current_user: CurrentUser, db: Db):
    """Cancel/delete a work order."""
    db.execute(
        "UPDATE work_orders SET status = 'cancelled', updated_at = ? WHERE id = ? AND organization_id = ?",
        (datetime.utcnow(), wo_id, current_user.org_id)
    )
    db.commit()
    db.sync()
