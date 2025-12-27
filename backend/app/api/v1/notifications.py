"""
GearGuard Backend - Notifications Endpoints
User notification management.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..deps import Db, CurrentUser

router = APIRouter()


class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    message: str
    reference_type: Optional[str]
    reference_id: Optional[str]
    priority: str
    is_read: bool
    action_url: Optional[str]
    created_at: str


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(current_user: CurrentUser, db: Db, 
                             unread_only: bool = Query(False), limit: int = Query(50)):
    """Get user notifications."""
    if unread_only:
        rows = db.fetch_all(
            """SELECT id, type, title, message, reference_type, reference_id, priority, is_read, action_url, created_at
            FROM notifications WHERE user_id = ? AND is_read = FALSE ORDER BY created_at DESC LIMIT ?""",
            (current_user.sub, limit)
        )
    else:
        rows = db.fetch_all(
            """SELECT id, type, title, message, reference_type, reference_id, priority, is_read, action_url, created_at
            FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT ?""",
            (current_user.sub, limit)
        )
    return [NotificationResponse(
        id=r[0], type=r[1], title=r[2], message=r[3], reference_type=r[4],
        reference_id=r[5], priority=r[6], is_read=bool(r[7]), action_url=r[8], created_at=str(r[9])
    ) for r in rows]


@router.put("/{notification_id}/read", response_model=dict)
async def mark_notification_read(notification_id: str, current_user: CurrentUser, db: Db):
    """Mark notification as read."""
    db.execute("UPDATE notifications SET is_read = TRUE, read_at = ? WHERE id = ? AND user_id = ?",
               (datetime.utcnow(), notification_id, current_user.sub))
    db.commit()
    db.sync()
    return {"message": "Marked as read"}


@router.put("/read-all", response_model=dict)
async def mark_all_read(current_user: CurrentUser, db: Db):
    """Mark all notifications as read."""
    db.execute("UPDATE notifications SET is_read = TRUE, read_at = ? WHERE user_id = ? AND is_read = FALSE",
               (datetime.utcnow(), current_user.sub))
    db.commit()
    db.sync()
    return {"message": "All marked as read"}


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(notification_id: str, current_user: CurrentUser, db: Db):
    """Delete a notification."""
    db.execute("DELETE FROM notifications WHERE id = ? AND user_id = ?", (notification_id, current_user.sub))
    db.commit()
    db.sync()


@router.get("/count", response_model=dict)
async def get_unread_count(current_user: CurrentUser, db: Db):
    """Get count of unread notifications."""
    count = db.fetch_one("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = FALSE", (current_user.sub,))
    return {"unread_count": count[0] if count else 0}
