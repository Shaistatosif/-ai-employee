"""
Database connection management for Neon PostgreSQL.

Provides connection pooling and basic query helpers for audit logging.
"""

import json
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, Optional

from .config import settings

logger = logging.getLogger(__name__)

# Database connection (lazy loaded)
_connection = None


def get_connection():
    """Get database connection (lazy initialization)."""
    global _connection

    if not settings.is_database_configured():
        logger.warning("Database not configured. Set NEON_DATABASE_URL in .env")
        return None

    if _connection is None:
        try:
            import psycopg2
            _connection = psycopg2.connect(settings.neon_database_url)
            logger.info("Connected to Neon PostgreSQL")
        except ImportError:
            logger.error("psycopg2 not installed. Run: pip install psycopg2-binary")
            return None
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return None

    return _connection


@contextmanager
def get_cursor() -> Generator:
    """Context manager for database cursor."""
    conn = get_connection()
    if conn is None:
        yield None
        return

    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        cursor.close()


def log_action(
    action_type: str,
    target: Optional[str] = None,
    parameters: Optional[dict] = None,
    approval_status: Optional[str] = None,
    approved_by: Optional[str] = None,
    result: Optional[str] = None,
    error_message: Optional[str] = None,
    actor: str = "claude_code",
) -> Optional[int]:
    """
    Log an action to the database.

    Args:
        action_type: Type of action (e.g., 'email_send', 'file_create')
        target: Target of the action (e.g., email address, file path)
        parameters: Additional parameters as dict
        approval_status: 'pending', 'approved', 'rejected', 'auto_approved'
        approved_by: Who approved (if applicable)
        result: 'success', 'failure', 'skipped'
        error_message: Error details if failed
        actor: Who performed the action

    Returns:
        The ID of the inserted log entry, or None if database not available
    """
    with get_cursor() as cursor:
        if cursor is None:
            # Database not available, log to file instead
            _log_to_file(action_type, target, parameters, result, error_message)
            return None

        try:
            cursor.execute(
                """
                INSERT INTO actions
                (action_type, actor, target, parameters, approval_status,
                 approved_by, result, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    action_type,
                    actor,
                    target,
                    json.dumps(parameters) if parameters else None,
                    approval_status,
                    approved_by,
                    result,
                    error_message,
                ),
            )
            result_id = cursor.fetchone()[0]
            logger.debug(f"Logged action {action_type} with ID {result_id}")
            return result_id
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
            _log_to_file(action_type, target, parameters, result, error_message)
            return None


def _log_to_file(
    action_type: str,
    target: Optional[str],
    parameters: Optional[dict],
    result: Optional[str],
    error_message: Optional[str],
) -> None:
    """Fallback: Log to local file when database unavailable."""
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = settings.logs_path / f"{today}_actions.md"

    timestamp = datetime.now().isoformat()
    log_entry = f"""
## {timestamp}
- **Action**: {action_type}
- **Target**: {target or 'N/A'}
- **Parameters**: {json.dumps(parameters) if parameters else 'N/A'}
- **Result**: {result or 'pending'}
- **Error**: {error_message or 'None'}

---
"""
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)

    logger.info(f"Logged action to file: {log_file}")


def init_database() -> bool:
    """
    Initialize database tables if they don't exist.

    Returns:
        True if successful, False otherwise
    """
    with get_cursor() as cursor:
        if cursor is None:
            return False

        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    action_type VARCHAR(50) NOT NULL,
                    actor VARCHAR(50) DEFAULT 'claude_code',
                    target TEXT,
                    parameters JSONB,
                    approval_status VARCHAR(20),
                    approved_by VARCHAR(50),
                    result VARCHAR(20),
                    error_message TEXT
                );

                CREATE TABLE IF NOT EXISTS emails (
                    id SERIAL PRIMARY KEY,
                    message_id VARCHAR(255) UNIQUE,
                    from_address TEXT,
                    to_address TEXT,
                    subject TEXT,
                    received_at TIMESTAMPTZ,
                    processed_at TIMESTAMPTZ,
                    action_taken TEXT,
                    priority VARCHAR(20)
                );

                CREATE TABLE IF NOT EXISTS business_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_date DATE,
                    revenue DECIMAL(10,2),
                    tasks_completed INT,
                    emails_processed INT,
                    bottlenecks JSONB
                );

                CREATE TABLE IF NOT EXISTS subscriptions (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    amount DECIMAL(10,2),
                    last_transaction_date DATE,
                    last_login_date DATE,
                    status VARCHAR(20) DEFAULT 'active'
                );

                CREATE INDEX IF NOT EXISTS idx_actions_timestamp
                ON actions(timestamp);

                CREATE INDEX IF NOT EXISTS idx_actions_type
                ON actions(action_type);
            """)
            logger.info("Database tables initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
