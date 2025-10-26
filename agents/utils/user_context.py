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

def get_user_context_from_db(email: str, chatspace: str = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve user context from the employee database.
    
    Args:
        email: Employee email address
        chatspace: Optional chat space name for fallback lookup
        
    Returns:
        Dict with user information or None if not found
    """
    try:
        engine = _get_engine()
        
        with engine.connect() as conn:
            # First try to find by email
            result = conn.execute(
                text("""
                    SELECT emp_name, emp_email, designation, emp_type, business_unit, 
                           is_resigning, resignation_date, manager_email, chat_id
                    FROM public.employee 
                    WHERE emp_email = :email 
                    LIMIT 1
                """),
                {"email": email}
            )
            
            row = result.fetchone()
            
            # If not found by email and chatspace provided, try to find by chatspace
            if not row and chatspace:
                # Note: This assumes there's a way to map chatspace to employee
                # For now, we'll just return None if email lookup fails
                # In the future, you might add a chatspace column to employee table
                pass
            
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
                    "chat_id": row.chat_id if hasattr(row, 'chat_id') else None
                }
            
            return None
            
    except Exception as e:
        print(f"Error retrieving user context: {e}")
        return None

def get_supervisor_info(supervisor_email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve supervisor information including chat_id.
    
    Args:
        supervisor_email: Supervisor's email address (manager_email from employee table)
        
    Returns:
        Dict with supervisor information including chat_id, or None if not found
    """
    try:
        engine = _get_engine()
        
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT emp_email, chat_id, emp_name
                    FROM public.employee 
                    WHERE emp_email = :email 
                    LIMIT 1
                """),
                {"email": supervisor_email}
            )
            
            row = result.fetchone()
            
            if row:
                return {
                    "supervisor_email": row.emp_email,
                    "chat_id": row.chat_id if hasattr(row, 'chat_id') else None,
                    "supervisor_name": row.emp_name if hasattr(row, 'emp_name') else None
                }
            
            return None
            
    except Exception as e:
        print(f"Error retrieving supervisor info: {e}")
        return None

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
