"""
GearGuard Backend - API v1 Router
Main router that includes all endpoint modules.
"""
from fastapi import APIRouter

from . import auth
from . import users
from . import organizations
from . import locations
from . import equipment
from . import categories
from . import schedules
from . import workorders
from . import teams
from . import parts
from . import checklists
from . import notifications
from . import reports
from . import dashboards
from . import audit

# Create the main API router
api_router = APIRouter()

# Include all sub-routers with their prefixes and tags
api_router.include_router(
    auth.router, 
    prefix="/auth", 
    tags=["Authentication"]
)

api_router.include_router(
    users.router, 
    prefix="/users", 
    tags=["Users"]
)

api_router.include_router(
    organizations.router, 
    prefix="/organizations", 
    tags=["Organizations"]
)

api_router.include_router(
    locations.router, 
    prefix="/locations", 
    tags=["Locations"]
)

api_router.include_router(
    equipment.router, 
    prefix="/equipment", 
    tags=["Equipment"]
)

api_router.include_router(
    categories.router, 
    prefix="/categories", 
    tags=["Categories"]
)

api_router.include_router(
    schedules.router, 
    prefix="/schedules", 
    tags=["Maintenance Schedules"]
)

api_router.include_router(
    workorders.router, 
    prefix="/workorders", 
    tags=["Work Orders"]
)

api_router.include_router(
    teams.router, 
    prefix="/teams", 
    tags=["Teams"]
)

api_router.include_router(
    parts.router, 
    prefix="/parts", 
    tags=["Parts & Inventory"]
)

api_router.include_router(
    checklists.router, 
    prefix="/checklists", 
    tags=["Checklists"]
)

api_router.include_router(
    notifications.router, 
    prefix="/notifications", 
    tags=["Notifications"]
)

api_router.include_router(
    reports.router, 
    prefix="/reports", 
    tags=["Reports & Analytics"]
)

api_router.include_router(
    dashboards.router, 
    prefix="/dashboards", 
    tags=["Dashboards"]
)

api_router.include_router(
    audit.router, 
    prefix="/audit-logs", 
    tags=["Audit Logs"]
)
