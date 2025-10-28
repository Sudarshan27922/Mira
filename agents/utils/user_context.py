import os
import json
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Global engine instance
_engine: Optional[Engine] = None

def _get_engine() -> Engine:
    """Get or create database engine"""
    global _engine
    if _engine is None:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL is not set in environment.")
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine

def get_user_context_from_db(email: Optional[str] = None, chat_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve user context from the employee database by email or chat_id.

    Args:
        email: Employee email address (preferred lookup)
        chat_id: Google Chat space ID (e.g., "spaces/AAAA...") as a fallback/secondary key

    Returns:
        Dict with user information or None if not found
    """
    if not email and not chat_id:
        raise ValueError("Either email or chat_id must be provided")

    try:
        engine = _get_engine()

        with engine.connect() as conn:
            row = None

            if email:
                result = conn.execute(
                    text(
                        """
                        SELECT emp_name, emp_email, designation, emp_type, business_unit,
                               is_resigning, resignation_date, manager_email, chat_id
                        FROM public.employee
                        WHERE emp_email = :email
                        LIMIT 1
                        """
                    ),
                    {"email": email},
                )
                row = result.fetchone()

            # Fallback: lookup by chat_id if not found by email
            if not row and chat_id:
                result = conn.execute(
                    text(
                        """
                        SELECT emp_name, emp_email, designation, emp_type, business_unit,
                               is_resigning, resignation_date, manager_email, chat_id
                        FROM public.employee
                        WHERE chat_id = :chat_id
                        LIMIT 1
                        """
                    ),
                    {"chat_id": chat_id},
                )
                row = result.fetchone()

            if row:
                return {
                    "emp_name": row.emp_name,
                    "emp_email": row.emp_email,
                    "designation": row.designation,
                    "emp_type": row.emp_type,
                    "business_unit": row.business_unit,
                    "is_resigning": row.is_resigning,
                    "resignation_date": str(row.resignation_date) if row.resignation_date else None,
                    "manager_email": row.manager_email,
                    "chat_id": getattr(row, "chat_id", None),
                }

            return None

    except Exception as e:
        print(f"Error retrieving user context: {e}")
        return None


def set_user_chat_id(email: str, chat_id: str) -> bool:
    """
    Set the user's chat_id if it's currently null/empty.

    Args:
        email: Employee email (primary key for update)
        chat_id: Google Chat space name/id to persist

    Returns:
        True if a row was updated, False otherwise.
    """
    try:
        engine = _get_engine()
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE public.employee
                    SET chat_id = :chat_id
                    WHERE emp_email = :email
                      AND (chat_id IS NULL OR chat_id = '')
                    """
                ),
                {"email": email, "chat_id": chat_id},
            )
            return result.rowcount > 0
    except Exception as e:
        print(f"Error setting user chat_id: {e}")
        return False

def format_user_context_for_prompt(user_context: Dict[str, Any]) -> str:
    """
    Format user context for injection into agent prompts.
    
    Args:
        user_context: User context dictionary
        
    Returns:
        Formatted string for prompt injection
    """
    if not user_context:
        return ""
    
    context_parts = []
    if user_context.get("emp_name"):
        context_parts.append(f"Name: {user_context['emp_name']}")
    if user_context.get("emp_email"):
        context_parts.append(f"Email: {user_context['emp_email']}")
    if user_context.get("designation"):
        context_parts.append(f"Designation: {user_context['designation']}")
    if user_context.get("emp_type"):
        context_parts.append(f"Employee Type: {user_context['emp_type']}")
    if user_context.get("business_unit"):
        context_parts.append(f"Business Unit: {user_context['business_unit']}")
    if user_context.get("manager_email"):
        context_parts.append(f"Manager Email: {user_context['manager_email']}")
    
    if context_parts:
        return f"User context: {', '.join(context_parts)}"
    
    return ""
