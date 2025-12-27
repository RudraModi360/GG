"""
GearGuard Backend - Reports Endpoints
Reporting and analytics.
"""
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..deps import Db, CurrentUser, PermissionChecker
from ...core.permissions import Permission

router = APIRouter()


class DashboardStats(BaseModel):
    total_equipment: int
    operational_equipment: int
    equipment_in_maintenance: int
    equipment_breakdown: int
    total_work_orders: int
    pending_work_orders: int
    in_progress_work_orders: int
    completed_work_orders: int
    overdue_work_orders: int
    upcoming_maintenance: int
    low_stock_parts: int
    avg_equipment_health: float


class EquipmentHealthItem(BaseModel):
    id: str
    name: str
    status: str
    health_score: int
    last_maintenance: Optional[str]


class WorkOrderSummary(BaseModel):
    period: str
    total: int
    completed: int
    pending: int
    cancelled: int
    avg_completion_time_hours: Optional[float]


@router.get("/dashboard", response_model=DashboardStats, dependencies=[Depends(PermissionChecker(Permission.REPORT_READ))])
async def get_dashboard_stats(current_user: CurrentUser, db: Db):
    """Get dashboard statistics."""
    org_id = current_user.org_id
    now = datetime.utcnow()
    
    # Equipment stats
    eq_total = db.fetch_one("SELECT COUNT(*) FROM equipment WHERE organization_id = ? AND status != 'retired'", (org_id,))
    eq_op = db.fetch_one("SELECT COUNT(*) FROM equipment WHERE organization_id = ? AND status = 'operational'", (org_id,))
    eq_maint = db.fetch_one("SELECT COUNT(*) FROM equipment WHERE organization_id = ? AND status = 'maintenance'", (org_id,))
    eq_break = db.fetch_one("SELECT COUNT(*) FROM equipment WHERE organization_id = ? AND status = 'breakdown'", (org_id,))
    avg_health = db.fetch_one("SELECT AVG(health_score) FROM equipment WHERE organization_id = ? AND status != 'retired'", (org_id,))
    
    # Work order stats
    wo_total = db.fetch_one("SELECT COUNT(*) FROM work_orders WHERE organization_id = ?", (org_id,))
    wo_pend = db.fetch_one("SELECT COUNT(*) FROM work_orders WHERE organization_id = ? AND status = 'pending'", (org_id,))
    wo_prog = db.fetch_one("SELECT COUNT(*) FROM work_orders WHERE organization_id = ? AND status = 'in_progress'", (org_id,))
    wo_comp = db.fetch_one("SELECT COUNT(*) FROM work_orders WHERE organization_id = ? AND status = 'completed'", (org_id,))
    wo_overdue = db.fetch_one("SELECT COUNT(*) FROM work_orders WHERE organization_id = ? AND status IN ('pending', 'in_progress') AND due_date < ?", (org_id, now))
    
    # Maintenance
    upcoming = db.fetch_one("SELECT COUNT(*) FROM maintenance_schedules WHERE organization_id = ? AND is_active = TRUE AND next_due <= ?", (org_id, now + timedelta(days=7)))
    
    # Parts
    low_stock = db.fetch_one("SELECT COUNT(*) FROM parts_inventory WHERE organization_id = ? AND is_active = TRUE AND quantity_in_stock <= minimum_stock_level", (org_id,))
    
    return DashboardStats(
        total_equipment=eq_total[0] if eq_total else 0,
        operational_equipment=eq_op[0] if eq_op else 0,
        equipment_in_maintenance=eq_maint[0] if eq_maint else 0,
        equipment_breakdown=eq_break[0] if eq_break else 0,
        total_work_orders=wo_total[0] if wo_total else 0,
        pending_work_orders=wo_pend[0] if wo_pend else 0,
        in_progress_work_orders=wo_prog[0] if wo_prog else 0,
        completed_work_orders=wo_comp[0] if wo_comp else 0,
        overdue_work_orders=wo_overdue[0] if wo_overdue else 0,
        upcoming_maintenance=upcoming[0] if upcoming else 0,
        low_stock_parts=low_stock[0] if low_stock else 0,
        avg_equipment_health=round(avg_health[0], 1) if avg_health and avg_health[0] else 0
    )


@router.get("/equipment-health", response_model=List[EquipmentHealthItem], dependencies=[Depends(PermissionChecker(Permission.REPORT_READ))])
async def get_equipment_health_report(current_user: CurrentUser, db: Db, status: Optional[str] = Query(None), limit: int = Query(50)):
    """Get equipment health report."""
    if status:
        rows = db.fetch_all(
            "SELECT id, name, status, health_score, last_maintenance_date FROM equipment WHERE organization_id = ? AND status = ? ORDER BY health_score LIMIT ?",
            (current_user.org_id, status, limit)
        )
    else:
        rows = db.fetch_all(
            "SELECT id, name, status, health_score, last_maintenance_date FROM equipment WHERE organization_id = ? AND status != 'retired' ORDER BY health_score LIMIT ?",
            (current_user.org_id, limit)
        )
    return [EquipmentHealthItem(id=r[0], name=r[1], status=r[2], health_score=r[3], last_maintenance=str(r[4]) if r[4] else None) for r in rows]


@router.get("/workorder-summary", response_model=List[WorkOrderSummary], dependencies=[Depends(PermissionChecker(Permission.REPORT_READ))])
async def get_workorder_summary(current_user: CurrentUser, db: Db, period: str = Query("month")):
    """Get work order summary by period."""
    # Simplified - just returns current period totals
    org_id = current_user.org_id
    
    if period == "week":
        start_date = datetime.utcnow() - timedelta(days=7)
    elif period == "year":
        start_date = datetime.utcnow() - timedelta(days=365)
    else:  # month
        start_date = datetime.utcnow() - timedelta(days=30)
    
    total = db.fetch_one("SELECT COUNT(*) FROM work_orders WHERE organization_id = ? AND created_at >= ?", (org_id, start_date))
    completed = db.fetch_one("SELECT COUNT(*) FROM work_orders WHERE organization_id = ? AND created_at >= ? AND status = 'completed'", (org_id, start_date))
    pending = db.fetch_one("SELECT COUNT(*) FROM work_orders WHERE organization_id = ? AND created_at >= ? AND status = 'pending'", (org_id, start_date))
    cancelled = db.fetch_one("SELECT COUNT(*) FROM work_orders WHERE organization_id = ? AND created_at >= ? AND status = 'cancelled'", (org_id, start_date))
    
    return [WorkOrderSummary(
        period=period,
        total=total[0] if total else 0,
        completed=completed[0] if completed else 0,
        pending=pending[0] if pending else 0,
        cancelled=cancelled[0] if cancelled else 0,
        avg_completion_time_hours=None
    )]


@router.get("/maintenance-costs", dependencies=[Depends(PermissionChecker(Permission.REPORT_READ))])
async def get_maintenance_costs(current_user: CurrentUser, db: Db, days: int = Query(30)):
    """Get maintenance cost summary."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    total_cost = db.fetch_one(
        "SELECT SUM(actual_cost) FROM work_orders WHERE organization_id = ? AND created_at >= ? AND actual_cost IS NOT NULL",
        (current_user.org_id, start_date)
    )
    parts_cost = db.fetch_one(
        """SELECT SUM(pu.quantity_used * pu.unit_cost_at_time) FROM parts_usage pu 
        JOIN work_orders w ON pu.work_order_id = w.id WHERE w.organization_id = ? AND pu.used_at >= ?""",
        (current_user.org_id, start_date)
    )
    
    return {
        "period_days": days,
        "total_maintenance_cost": total_cost[0] if total_cost and total_cost[0] else 0,
        "parts_cost": parts_cost[0] if parts_cost and parts_cost[0] else 0
    }
