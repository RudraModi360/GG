"""
GearGuard Backend - Teams Endpoints
Team management operations.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..deps import Db, CurrentUser, PermissionChecker
from ...core import generate_id
from ...core.permissions import Permission

router = APIRouter()


class TeamResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    leader_id: Optional[str]
    leader_name: Optional[str]
    location_id: Optional[str]
    location_name: Optional[str]
    member_count: int
    is_active: bool
    created_at: str


class TeamCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    leader_id: Optional[str] = None
    location_id: Optional[str] = None


class TeamMemberResponse(BaseModel):
    id: str
    user_id: str
    user_name: str
    user_email: str
    role: str
    joined_at: str


class AddMemberRequest(BaseModel):
    user_id: str
    role: str = "member"


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(PermissionChecker(Permission.USER_MANAGE_ROLES))])
async def create_team(request: TeamCreateRequest, current_user: CurrentUser, db: Db):
    """Create a new team."""
    team_id = generate_id()
    now = datetime.utcnow()
    
    db.execute(
        """INSERT INTO teams (id, organization_id, name, description, leader_id, location_id, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (team_id, current_user.org_id, request.name, request.description, request.leader_id, request.location_id, True, now, now)
    )
    
    if request.leader_id:
        db.execute(
            "INSERT INTO team_members (id, team_id, user_id, role, joined_at) VALUES (?, ?, ?, ?, ?)",
            (generate_id(), team_id, request.leader_id, "leader", now)
        )
    
    db.commit()
    db.sync()
    return await get_team(team_id, current_user, db)


@router.get("", response_model=List[TeamResponse])
async def list_teams(current_user: CurrentUser, db: Db):
    """List all teams."""
    rows = db.fetch_all(
        """SELECT t.id, t.name, t.description, t.leader_id, u.first_name || ' ' || u.last_name,
               t.location_id, l.name, (SELECT COUNT(*) FROM team_members WHERE team_id = t.id),
               t.is_active, t.created_at
        FROM teams t LEFT JOIN users u ON t.leader_id = u.id LEFT JOIN locations l ON t.location_id = l.id
        WHERE t.organization_id = ? ORDER BY t.name""", (current_user.org_id,)
    )
    return [TeamResponse(id=r[0], name=r[1], description=r[2], leader_id=r[3], leader_name=r[4],
                         location_id=r[5], location_name=r[6], member_count=r[7], is_active=bool(r[8]), created_at=str(r[9])) for r in rows]


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(team_id: str, current_user: CurrentUser, db: Db):
    """Get team details."""
    row = db.fetch_one(
        """SELECT t.id, t.name, t.description, t.leader_id, u.first_name || ' ' || u.last_name,
               t.location_id, l.name, (SELECT COUNT(*) FROM team_members WHERE team_id = t.id),
               t.is_active, t.created_at
        FROM teams t LEFT JOIN users u ON t.leader_id = u.id LEFT JOIN locations l ON t.location_id = l.id
        WHERE t.id = ? AND t.organization_id = ?""", (team_id, current_user.org_id)
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return TeamResponse(id=row[0], name=row[1], description=row[2], leader_id=row[3], leader_name=row[4],
                        location_id=row[5], location_name=row[6], member_count=row[7], is_active=bool(row[8]), created_at=str(row[9]))


@router.get("/{team_id}/members", response_model=List[TeamMemberResponse])
async def get_team_members(team_id: str, current_user: CurrentUser, db: Db):
    """Get team members."""
    rows = db.fetch_all(
        """SELECT tm.id, tm.user_id, u.first_name || ' ' || u.last_name, u.email, tm.role, tm.joined_at
        FROM team_members tm JOIN users u ON tm.user_id = u.id WHERE tm.team_id = ?""", (team_id,)
    )
    return [TeamMemberResponse(id=r[0], user_id=r[1], user_name=r[2], user_email=r[3], role=r[4], joined_at=str(r[5])) for r in rows]


@router.post("/{team_id}/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(PermissionChecker(Permission.USER_MANAGE_ROLES))])
async def add_team_member(team_id: str, request: AddMemberRequest, current_user: CurrentUser, db: Db):
    """Add member to team."""
    member_id = generate_id()
    now = datetime.utcnow()
    db.execute("INSERT INTO team_members (id, team_id, user_id, role, joined_at) VALUES (?, ?, ?, ?, ?)",
               (member_id, team_id, request.user_id, request.role, now))
    db.commit()
    db.sync()
    
    row = db.fetch_one("SELECT first_name || ' ' || last_name, email FROM users WHERE id = ?", (request.user_id,))
    return TeamMemberResponse(id=member_id, user_id=request.user_id, user_name=row[0], user_email=row[1], role=request.role, joined_at=str(now))


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(PermissionChecker(Permission.USER_MANAGE_ROLES))])
async def remove_team_member(team_id: str, user_id: str, db: Db):
    """Remove member from team."""
    db.execute("DELETE FROM team_members WHERE team_id = ? AND user_id = ?", (team_id, user_id))
    db.commit()
    db.sync()
