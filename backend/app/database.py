"""
GearGuard Backend - Database Connection Module
Handles Turso/LibSQL database connections.
"""
import sqlite3
from typing import Optional, Any, List, Tuple
from contextlib import contextmanager
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class Database:
    """
    Database connection manager for Turso/LibSQL.
    Uses embedded replica pattern for better performance.
    """
    
    def __init__(self):
        self._connection: Optional[Any] = None
    
    def connect(self) -> Any:
        """
        Establish database connection using embedded replica.
        Returns the connection object.
        """
        if self._connection is None:
            try:
                import libsql
                
                # Connect using embedded replica pattern
                self._connection = libsql.connect(
                    settings.LOCAL_DB_PATH,
                    sync_url=settings.TURSO_DATABASE_URL,
                    auth_token=settings.TURSO_AUTH_TOKEN
                )
                self._connection.sync()
                logger.info("Connected to Turso database with embedded replica")
            except ImportError:
                # Fallback to local SQLite
                logger.warning("libsql not found, using local SQLite")
                self._connection = sqlite3.connect(settings.LOCAL_DB_PATH)
            except Exception as e:
                logger.error(f"Failed to connect to Turso: {e}")
                # Fallback to local SQLite
                self._connection = sqlite3.connect(settings.LOCAL_DB_PATH)
                logger.warning("Connected to local SQLite database")
        
        return self._connection
    
    def execute(self, query: str, params: Tuple = ()) -> Any:
        """Execute a single query."""
        conn = self.connect()
        try:
            result = conn.execute(query, params)
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}")
            raise
    
    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Tuple]:
        """Execute query and fetch one result."""
        result = self.execute(query, params)
        return result.fetchone()
    
    def fetch_all(self, query: str, params: Tuple = ()) -> List[Tuple]:
        """Execute query and fetch all results."""
        result = self.execute(query, params)
        return result.fetchall()
    
    def commit(self) -> None:
        """Commit current transaction."""
        if self._connection:
            self._connection.commit()
    
    def rollback(self) -> None:
        """Rollback current transaction."""
        if self._connection and hasattr(self._connection, 'rollback'):
            self._connection.rollback()
    
    def sync(self) -> None:
        """Sync local replica with remote Turso database."""
        if self._connection and hasattr(self._connection, 'sync'):
            try:
                self._connection.sync()
                logger.debug("Database synced with remote")
            except Exception as e:
                logger.warning(f"Sync warning: {e}")
    
    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            if hasattr(self._connection, 'close'):
                self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        try:
            yield self
            self.commit()
        except Exception:
            self.rollback()
            raise
    
    def run_migrations(self, migrations_dir: str = "migrations") -> None:
        """Run SQL migration files from the migrations directory."""
        from pathlib import Path
        
        migrations_path = Path(migrations_dir)
        if not migrations_path.exists():
            logger.warning(f"Migrations directory not found: {migrations_dir}")
            return
        
        # Get all .sql files sorted by name
        sql_files = sorted(migrations_path.glob("*.sql"))
        
        for sql_file in sql_files:
            logger.info(f"Running migration: {sql_file.name}")
            try:
                with open(sql_file, "r", encoding="utf-8") as f:
                    sql_content = f.read()
                
                # Execute each statement separately
                statements = sql_content.split(";")
                for statement in statements:
                    statement = statement.strip()
                    if statement and not statement.startswith("--"):
                        try:
                            self.execute(statement)
                        except Exception as stmt_error:
                            logger.warning(f"Statement failed (may be OK): {stmt_error}")
                
                self.commit()
                logger.info(f"Migration completed: {sql_file.name}")
            except Exception as e:
                logger.error(f"Migration failed for {sql_file.name}: {e}")
                raise
        
        logger.info("All migrations completed successfully")


# Singleton database instance
_db_instance: Optional[Database] = None


def get_database() -> Database:
    """Get the singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def init_database() -> Database:
    """Initialize database connection."""
    db = get_database()
    db.connect()
    return db


def close_database() -> None:
    """Close database connection."""
    global _db_instance
    if _db_instance:
        _db_instance.close()
        _db_instance = None
