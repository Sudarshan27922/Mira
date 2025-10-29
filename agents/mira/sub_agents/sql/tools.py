import os
import json
import threading
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from langchain_core.tools import tool

_engine_lock = threading.Lock()
_engine: Optional[Engine] = None

def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                url = os.getenv("DATABASE_URL")
                if not url:
                    raise RuntimeError("DATABASE_URL is not set in environment.")
                _engine = create_engine(
                    url,
                    pool_pre_ping=True,
                )
    return _engine

def _is_read_only_sql(sql: str) -> bool:
    s = sql.strip().lower()
    # Allow only single read-only statement
    if not (s.startswith("select") or s.startswith("with") or s.startswith("explain")):
        return False
    # Disallow multiple statements
    parts = [p for p in s.split(";") if p.strip()]
    return len(parts) <= 1

@tool("execute_sql_query")
def execute_sql_query(sql: str) -> str:
    """
    Execute a read-only SQL query (SELECT/WITH/EXPLAIN) against PostgreSQL and return up to 1000 rows as JSON.
    Input must be a single read-only statement. Do not pass natural language.
    """
    if not _is_read_only_sql(sql):
        return "Only single read-only SQL is allowed. Begin with SELECT/WITH/EXPLAIN and avoid multiple statements."
    try:
        eng = _get_engine()
        with eng.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()
            data: List[Dict[str, Any]] = [dict(r._mapping) for r in rows[:1000]]
        return json.dumps(data, default=str)
    except Exception as e:
        return f"SQL execution failed: {e}"

@tool("list_public_tables")
def list_public_tables() -> dict:
    """List public tables in the configured database."""
    try:
        eng = _get_engine()
        with eng.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema='public'
                    ORDER BY table_name
                    """
                )
            )
            rows = result.fetchall()
            data: List[Dict[str, Any]] = [dict(r._mapping) for r in rows]
        return {"tables": data}
    except Exception as e:
        return {"error": f"Schema inspection failed: {e}"}

@tool("describe_table_columns")
def describe_table_columns(table_name: str) -> str:
    """
    Describe columns for a given table in public schema. Input: table name (with or without 'public.' prefix).
    """
    try:
        # Strip 'public.' prefix if present
        clean_table_name = table_name.replace('public.', '') if table_name.startswith('public.') else table_name
        
        eng = _get_engine()
        with eng.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema='public' AND table_name=:t
                    ORDER BY ordinal_position
                    """
                ),
                {"t": clean_table_name},
            )
            rows = result.fetchall()
            data: List[Dict[str, Any]] = [dict(r._mapping) for r in rows]
        return json.dumps(data, default=str)
    except Exception as e:
        return f"Schema inspection failed: {e}"

SQL_TOOLS = [execute_sql_query, list_public_tables, describe_table_columns]