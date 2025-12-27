#!/usr/bin/env python
"""
GearGuard Backend - Migration Runner Script
Run this manually to execute database migrations.

Usage:
    python run_migrations.py
"""
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from backend/.env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Configuration
DELAY_BETWEEN_STATEMENTS = 2.0  # Seconds between each statement
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 3.0  # Seconds


def run_migrations():
    """Run all SQL migrations with retry logic."""
    import libsql
    
    # Get config from environment
    turso_url = os.getenv("TURSO_DATABASE_URL")
    turso_token = os.getenv("TURSO_AUTH_TOKEN")
    
    if not turso_url or not turso_token:
        print("❌ Error: TURSO_DATABASE_URL and TURSO_AUTH_TOKEN must be set in .env")
        sys.exit(1)
    
    print(f"🔌 Connecting to Turso database...")
    print(f"   URL: {turso_url[:50]}...")
    
    try:
        # Connect using embedded replica pattern
        conn = libsql.connect(
            "local_replica.db",
            sync_url=turso_url,
            auth_token=turso_token
        )
        conn.sync()
        print("✅ Connected to Turso database\n")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        sys.exit(1)
    
    # Find migration files
    migrations_dir = Path(__file__).parent / "migrations"
    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        sys.exit(1)
    
    sql_files = sorted(migrations_dir.glob("*.sql"))
    print(f"📁 Found {len(sql_files)} migration file(s)\n")
    
    for sql_file in sql_files:
        print(f"{'='*60}")
        print(f"📄 Running: {sql_file.name}")
        print(f"{'='*60}\n")
        
        with open(sql_file, "r", encoding="utf-8") as f:
            sql_content = f.read()
        
        # Parse statements
        statements = parse_sql_statements(sql_content)
        
        print(f"   📊 Found {len(statements)} statement(s)")
        print(f"   ⏱️  Delay between statements: {DELAY_BETWEEN_STATEMENTS}s\n")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements, 1):
            result = execute_with_retry(conn, statement, i, len(statements))
            
            if result == "success":
                success_count += 1
            elif result == "skipped":
                skip_count += 1
            else:
                error_count += 1
            
            # Delay between statements
            if i < len(statements):
                time.sleep(DELAY_BETWEEN_STATEMENTS)
        
        # Sync to remote after all statements
        print("\n   🔄 Syncing to remote...")
        try:
            conn.sync()
            print("   ✅ Synced successfully")
        except Exception as e:
            print(f"   ⚠️  Sync warning: {e}")
        
        print(f"\n   {'='*50}")
        print(f"   📊 Results: ✅ {success_count} | ⏭️ {skip_count} | ❌ {error_count}")
        print(f"   {'='*50}")
    
    print(f"\n{'='*60}")
    print("🎉 Migration completed!")
    print(f"{'='*60}\n")


def parse_sql_statements(sql_content: str) -> list:
    """Parse SQL content into individual statements."""
    statements = []
    current_statement = []
    
    for line in sql_content.split('\n'):
        stripped = line.strip()
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith('--'):
            continue
        
        current_statement.append(line)
        
        # Check if statement ends with semicolon
        if stripped.endswith(';'):
            full_statement = '\n'.join(current_statement)
            full_statement = full_statement.strip().rstrip(';').strip()
            if full_statement:
                statements.append(full_statement)
            current_statement = []
    
    return statements


def execute_with_retry(conn, statement: str, index: int, total: int) -> str:
    """Execute a statement with retry logic."""
    retry_delay = INITIAL_RETRY_DELAY
    desc = get_statement_description(statement)
    
    for attempt in range(MAX_RETRIES):
        try:
            conn.execute(statement)
            conn.commit()
            print(f"   ✅ [{index}/{total}] {desc}")
            return "success"
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Already exists - OK to skip
            if "already exists" in error_msg:
                print(f"   ⏭️  [{index}/{total}] {desc} (already exists)")
                return "skipped"
            
            # Rate limited or connection error - retry
            if any(x in error_msg for x in ["505", "rate", "invalid response", "connection"]):
                if attempt < MAX_RETRIES - 1:
                    print(f"   ⏳ [{index}/{total}] Retrying in {retry_delay}s... (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
                    continue
            
            # Real error
            print(f"   ❌ [{index}/{total}] {desc}")
            print(f"       Error: {str(e)[:100]}")
            return "error"
    
    return "error"


def get_statement_description(statement: str) -> str:
    """Get a human-readable description of the statement."""
    import re
    
    upper = statement.upper()
    
    if "CREATE TABLE" in upper:
        match = re.search(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)', statement, re.IGNORECASE)
        return f"Create table: {match.group(1)}" if match else "Create table"
    
    if "CREATE INDEX" in upper:
        match = re.search(r'CREATE INDEX\s+(?:IF NOT EXISTS\s+)?(\w+)', statement, re.IGNORECASE)
        return f"Create index: {match.group(1)}" if match else "Create index"
    
    if "INSERT" in upper:
        match = re.search(r'INSERT\s+(?:OR IGNORE\s+)?INTO\s+(\w+)', statement, re.IGNORECASE)
        return f"Insert into: {match.group(1)}" if match else "Insert data"
    
    return statement.split('\n')[0][:50] + "..."


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🛡️  GearGuard Database Migration Runner")
    print("="*60)
    print(f"\n⚙️  Configuration:")
    print(f"   - Delay between statements: {DELAY_BETWEEN_STATEMENTS}s")
    print(f"   - Max retries: {MAX_RETRIES}")
    print()
    
    run_migrations()
