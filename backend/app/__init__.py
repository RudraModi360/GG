"""GearGuard Backend Application Package"""
from app.config import settings
from app.database import get_database, init_database, close_database

__version__ = "1.0.0"
__all__ = ["settings", "get_database", "init_database", "close_database"]
