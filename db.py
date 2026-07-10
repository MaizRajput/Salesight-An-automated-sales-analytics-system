from __future__ import annotations
import os, json, logging
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, inspect, Column, String, Float, Integer, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# Change this env variable to switch databases with zero code changes:
#   PostgreSQL:   DATABASE_URL=postgresql://user:pass@localhost/salesdb
#   SQL Server:   DATABASE_URL=mssql+pyodbc://user:pass@server/db?driver=ODBC+Driver+17+for+SQL+Server
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sales_analytics.db")

_log = logging.getLogger(__name__)

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine        = create_engine(DATABASE_URL, connect_args=_connect_args, echo=False)
SessionLocal  = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base          = declarative_base()


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    session_id        = Column(String(16),  primary_key=True)
    filename          = Column(String(256))
    uploaded_at       = Column(DateTime,    default=datetime.utcnow)
    original_rows     = Column(Integer)
    original_cols     = Column(Integer)
    cleaned_rows      = Column(Integer)
    cleaned_cols      = Column(Integer)
    rows_retained_pct = Column(Float)
    table_name        = Column(String(64))
    warnings          = Column(Text)


def init_db() -> None:
    """Create all tables. Called once on FastAPI startup."""
    Base.metadata.create_all(bind=engine)
    _log.info("DB ready: %s", DATABASE_URL)


def save_cleaned_df(df: pd.DataFrame, session_id: str, filename: str, report: dict) -> str:
    """
    Save the cleaned DataFrame to SQL as table  sales_{session_id}.
    Also saves metadata to upload_sessions table.
    Returns the table name.
    """
    table_name = f"sales_{session_id}"
    df.to_sql(table_name, con=engine, if_exists="replace", index=False, chunksize=5000)
    _log.info("Saved %d rows to SQL table '%s'", len(df), table_name)

    db = SessionLocal()
    try:
        existing = db.get(UploadSession, session_id)
        if existing:
            db.delete(existing)
            db.commit()
        db.add(UploadSession(
            session_id        = session_id,
            filename          = filename,
            uploaded_at       = datetime.utcnow(),
            original_rows     = report["original_shape"][0],
            original_cols     = report["original_shape"][1],
            cleaned_rows      = report["cleaned_shape"][0],
            cleaned_cols      = report["cleaned_shape"][1],
            rows_retained_pct = report["rows_retained_pct"],
            table_name        = table_name,
            warnings          = json.dumps(report.get("warnings", [])),
        ))
        db.commit()
    finally:
        db.close()

    return table_name


def load_session_df(session_id: str) -> pd.DataFrame | None:
    """Load cleaned data from SQL. Returns None if session doesn't exist."""
    table_name = f"sales_{session_id}"
    if table_name not in inspect(engine).get_table_names():
        return None
    return pd.read_sql_table(table_name, con=engine)


def list_sessions() -> list[dict]:
    """Return all upload sessions, newest first."""
    db = SessionLocal()
    try:
        rows = db.query(UploadSession).order_by(UploadSession.uploaded_at.desc()).all()
        return [
            {
                "session_id":        r.session_id,
                "filename":          r.filename,
                "uploaded_at":       r.uploaded_at.isoformat() if r.uploaded_at else None,
                "original_rows":     r.original_rows,
                "cleaned_rows":      r.cleaned_rows,
                "rows_retained_pct": r.rows_retained_pct,
                "table_name":        r.table_name,
            }
            for r in rows
        ]
    finally:
        db.close()


def get_session_meta(session_id: str) -> dict | None:
    """Return metadata for one session, or None if not found."""
    db = SessionLocal()
    try:
        r = db.get(UploadSession, session_id)
        if not r:
            return None
        return {
            "session_id":        r.session_id,
            "filename":          r.filename,
            "uploaded_at":       r.uploaded_at.isoformat() if r.uploaded_at else None,
            "original_rows":     r.original_rows,
            "cleaned_rows":      r.cleaned_rows,
            "rows_retained_pct": r.rows_retained_pct,
            "table_name":        r.table_name,
        }
    finally:
        db.close()