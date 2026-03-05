import logging
import pyodbc
from datetime import datetime, timezone
from config import Config

logger = logging.getLogger(__name__)


def get_connection():
    """
    Returns a pyodbc connection to Azure SQL Database.
    Connection string format (set via env var):
      Driver={ODBC Driver 18 for SQL Server};Server=tcp:<server>.database.windows.net,1433;
      Database=<db>;Uid=<user>;Pwd=<password>;Encrypt=yes;TrustServerCertificate=no;
    """
    return pyodbc.connect(Config.AZURE_SQL_CONNECTION_STRING)


def init_db():
    """Create the file_uploads table if it doesn't exist."""
    ddl = """
    IF NOT EXISTS (
        SELECT * FROM sysobjects WHERE name='file_uploads' AND xtype='U'
    )
    CREATE TABLE file_uploads (
        id          INT IDENTITY(1,1) PRIMARY KEY,
        filename    NVARCHAR(255)     NOT NULL,
        blob_url    NVARCHAR(1024)    NOT NULL,
        size_bytes  BIGINT            NOT NULL,
        content_type NVARCHAR(128),
        uploaded_at DATETIME2         NOT NULL DEFAULT SYSUTCDATETIME()
    );
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(ddl)
        conn.commit()
    logger.info("Database initialised — table 'file_uploads' is ready.")


def insert_file_record(filename: str, blob_url: str, size_bytes: int, content_type: str) -> int:
    """Insert a file metadata record and return the new row id."""
    sql = """
    INSERT INTO file_uploads (filename, blob_url, size_bytes, content_type, uploaded_at)
    OUTPUT INSERTED.id
    VALUES (?, ?, ?, ?, ?)
    """
    uploaded_at = datetime.now(timezone.utc)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, filename, blob_url, size_bytes, content_type, uploaded_at)
        row_id = cursor.fetchone()[0]
        conn.commit()
    logger.info(f"Inserted file record id={row_id} for '{filename}'")
    return row_id


def get_all_files() -> list[dict]:
    """Return all file metadata records, newest first."""
    sql = """
    SELECT id, filename, blob_url, size_bytes, content_type, uploaded_at
    FROM file_uploads
    ORDER BY uploaded_at DESC
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    return [
        {col: (val.isoformat() if isinstance(val, datetime) else val)
         for col, val in zip(columns, row)}
        for row in rows
    ]


def delete_file_record(file_id: int) -> bool:
    """Delete a file record by id. Returns True if a row was deleted."""
    sql = "DELETE FROM file_uploads WHERE id = ?"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, file_id)
        deleted = cursor.rowcount > 0
        conn.commit()
    if deleted:
        logger.info(f"Deleted file record id={file_id}")
    return deleted
