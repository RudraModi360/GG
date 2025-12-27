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
    Includes robust reconnection logic for handling connection drops.
    """
    
    # Connection error patterns that indicate we should reconnect
    CONNECTION_ERROR_PATTERNS = [
        'connection',
        'forcibly closed', 
        'os error 10054',
        'os error 10053',
        'hrana',
        'stream error',
        'http error',
        'network',
        'timeout',
        'reset by peer',
        'broken pipe',
        'connection refused',
        'eof',
        'closed'
    ]
    
    def __init__(self):
        self._connection: Optional[Any] = None
        self._is_http_client = False
        self._last_health_check: float = 0
        self._health_check_interval: float = 30.0  # seconds
        self._connection_attempts: int = 0
        self._max_connection_attempts: int = 5
    
    def _is_connection_error(self, error: Exception) -> bool:
        """Check if the error is a connection-related error that warrants reconnection."""
        error_str = str(error).lower()
        return any(pattern in error_str for pattern in self.CONNECTION_ERROR_PATTERNS)
    
    def _check_connection_health(self) -> bool:
        """
        Check if the current connection is healthy.
        Returns True if healthy, False if needs reconnection.
        """
        import time
        
        if self._connection is None:
            return False
        
        # Skip health check if we checked recently
        current_time = time.time()
        if current_time - self._last_health_check < self._health_check_interval:
            return True
        
        try:
            # Simple health check query
            self._connection.execute("SELECT 1")
            self._last_health_check = current_time
            return True
        except Exception as e:
            logger.warning(f"Connection health check failed: {e}")
            return False
    
    def connect(self, force_reconnect: bool = False) -> Any:
        """
        Establish database connection.
        Uses HTTP client for serverless, embedded replica for local dev.
        Returns the connection object.
        
        Args:
            force_reconnect: If True, close existing connection and reconnect
        """
        import time
        
        if force_reconnect and self._connection is not None:
            logger.info("Forcing reconnection to database...")
            try:
                if hasattr(self._connection, 'close'):
                    self._connection.close()
            except Exception as e:
                logger.debug(f"Error closing connection during force reconnect: {e}")
            self._connection = None
            self._connection_attempts = 0
        
        if self._connection is None:
            self._connection_attempts += 1
            
            if self._connection_attempts > self._max_connection_attempts:
                logger.error(f"Max connection attempts ({self._max_connection_attempts}) exceeded")
                # Reset counter after a delay
                time.sleep(5)
                self._connection_attempts = 1
            
            # Try HTTP client first (works in serverless environments)
            try:
                import libsql_client
                
                # Check if we have Turso URL (indicates remote database)
                if settings.TURSO_DATABASE_URL and settings.TURSO_AUTH_TOKEN:
                    self._connection = libsql_client.create_client_sync(
                        url=settings.TURSO_DATABASE_URL,
                        auth_token=settings.TURSO_AUTH_TOKEN
                    )
                    self._is_http_client = True
                    self._connection_attempts = 0
                    self._last_health_check = time.time()
                    logger.info("Connected to Turso database via HTTP client")
                    return self._connection
            except ImportError:
                logger.debug("libsql_client not available, trying embedded replica")
            except Exception as e:
                logger.warning(f"HTTP client connection failed: {e}")
            
            # Try embedded replica (for local development)
            try:
                import libsql
                
                self._connection = libsql.connect(
                    settings.LOCAL_DB_PATH,
                    sync_url=settings.TURSO_DATABASE_URL,
                    auth_token=settings.TURSO_AUTH_TOKEN
                )
                self._connection.sync()
                self._connection_attempts = 0
                self._last_health_check = time.time()
                logger.info("Connected to Turso database with embedded replica")
            except ImportError:
                # Fallback to local SQLite
                logger.warning("libsql not found, using local SQLite")
                self._connection = sqlite3.connect(settings.LOCAL_DB_PATH)
                self._connection_attempts = 0
            except Exception as e:
                logger.error(f"Failed to connect to Turso: {e}")
                # Fallback to local SQLite
                self._connection = sqlite3.connect(settings.LOCAL_DB_PATH)
                self._connection_attempts = 0
                logger.warning("Connected to local SQLite database")
        
        return self._connection
    
    def _reconnect(self) -> Any:
        """Force reconnection to the database."""
        logger.info("Reconnecting to database...")
        return self.connect(force_reconnect=True)
    
    def execute(self, query: str, params: Tuple = (), retries: int = 3) -> Any:
        """
        Execute a single query with robust retry logic for connection drops.
        Automatically reconnects when connection errors are detected.
        """
        import time
        
        last_error = None
        for attempt in range(retries):
            try:
                # Get connection (will reconnect if needed)
                conn = self.connect()
                
                # Execute query
                result = conn.execute(query, params)
                return result
                
            except Exception as e:
                last_error = e
                
                # Check if this is a connection error
                if self._is_connection_error(e):
                    logger.warning(
                        f"Connection error on attempt {attempt + 1}/{retries}: {e}"
                    )
                    
                    # Force reconnection on next attempt
                    self._connection = None
                    
                    if attempt < retries - 1:
                        # Exponential backoff with jitter
                        import random
                        base_delay = 0.5 * (2 ** attempt)
                        jitter = random.uniform(0, 0.5)
                        delay = base_delay + jitter
                        logger.info(f"Retrying in {delay:.2f}s...")
                        time.sleep(delay)
                    continue
                else:
                    # Non-connection error, don't retry
                    logger.error(f"Query execution failed: {e}\nQuery: {query}")
                    raise
        
        # All retries exhausted
        logger.error(f"All {retries} retry attempts failed for query: {query}")
        raise last_error or Exception("Database connection failed after retries")
    
    def execute_with_reconnect(self, query: str, params: Tuple = ()) -> Any:
        """
        Execute a query with aggressive reconnection.
        Use this for critical operations that must succeed.
        """
        try:
            return self.execute(query, params, retries=5)
        except Exception as e:
            # Last resort: force full reconnect and try once more
            logger.warning(f"All retries failed, attempting full reconnect...")
            self._reconnect()
            return self.connect().execute(query, params)
    
    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Tuple]:
        """Execute query and fetch one result."""
        result = self.execute(query, params)
        return result.fetchone()
    
    def fetch_all(self, query: str, params: Tuple = ()) -> List[Tuple]:
        """Execute query and fetch all results."""
        result = self.execute(query, params)
        return result.fetchall()
    
    def commit(self) -> None:
        """Commit current transaction with reconnection support."""
        if self._connection:
            try:
                self._connection.commit()
            except Exception as e:
                if self._is_connection_error(e):
                    logger.warning(f"Commit failed due to connection error: {e}")
                    # Connection lost during commit - data may be lost
                    self._connection = None
                raise
    
    def rollback(self) -> None:
        """Rollback current transaction."""
        if self._connection and hasattr(self._connection, 'rollback'):
            try:
                self._connection.rollback()
            except Exception as e:
                logger.warning(f"Rollback failed: {e}")
                if self._is_connection_error(e):
                    self._connection = None
    
    def sync(self) -> None:
        """Sync local replica with remote Turso database."""
        if self._connection and hasattr(self._connection, 'sync'):
            try:
                self._connection.sync()
                logger.debug("Database synced with remote")
            except Exception as e:
                logger.warning(f"Sync warning: {e}")
                if self._is_connection_error(e):
                    # Try to reconnect and sync again
                    try:
                        self._reconnect()
                        if hasattr(self._connection, 'sync'):
                            self._connection.sync()
                            logger.info("Sync succeeded after reconnection")
                    except Exception as retry_error:
                        logger.error(f"Sync failed after reconnection: {retry_error}")
    
    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            try:
                if hasattr(self._connection, 'close'):
                    self._connection.close()
            except Exception as e:
                logger.debug(f"Error closing connection: {e}")
            finally:
                self._connection = None
                self._connection_attempts = 0
                logger.info("Database connection closed")
    
    def ensure_connected(self) -> bool:
        """
        Ensure database is connected and healthy.
        Returns True if connected, raises exception if cannot connect.
        """
        if not self._check_connection_health():
            self._reconnect()
        return True
    
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
