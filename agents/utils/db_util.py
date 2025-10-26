import os
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from datetime import datetime

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

def create_leave_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new leave request in the database.
    
    Args:
        request_data: Dict containing leave request details:
            - request_id: Unique request identifier
            - employee_email: Employee email
            - supervisor_email: Supervisor email (manager_email from employee table)
            - leave_type: Type of leave (Annual, Sick, etc.)
            - start_date: Start date in YYYY-MM-DD format
            - end_date: End date in YYYY-MM-DD format
            - reason: Reason for leave
            - employee_space: Employee's Google Chat space ID
            - status: Initial status (default: PENDING)
    
    Returns:
        Dict with request_id and status
    """
    try:
        engine = _get_engine()
        
        with engine.connect() as conn:
            request_id = request_data.get("request_id")
            if not request_id:
                raise ValueError("request_id is required")
            
            # Check if request_id already exists
            result = conn.execute(
                text("""
                    SELECT request_id FROM public.leave_requests 
                    WHERE request_id = :request_id 
                    LIMIT 1
                """),
                {"request_id": request_id}
            )
            
            if result.fetchone():
                # Update existing request
                conn.execute(
                    text("""
                        UPDATE public.leave_requests 
                        SET employee_email = :employee_email,
                            supervisor_email = :supervisor_email,
                            leave_type = :leave_type,
                            start_date = :start_date,
                            end_date = :end_date,
                            reason = :reason,
                            employee_space = :employee_space,
                            status = :status,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE request_id = :request_id
                    """),
                    {
                        "request_id": request_id,
                        "employee_email": request_data.get("employee_email"),
                        "supervisor_email": request_data.get("supervisor_email"),
                        "leave_type": request_data.get("leave_type"),
                        "start_date": request_data.get("start_date"),
                        "end_date": request_data.get("end_date"),
                        "reason": request_data.get("reason"),
                        "employee_space": request_data.get("employee_space"),
                        "status": request_data.get("status", "PENDING")
                    }
                )
                conn.commit()
                return {"request_id": request_id, "status": "UPDATED"}
            else:
                # Insert new request
                conn.execute(
                    text("""
                        INSERT INTO public.leave_requests 
                        (request_id, employee_email, supervisor_email, leave_type, 
                         start_date, end_date, reason, employee_space, status, created_at, updated_at)
                        VALUES (:request_id, :employee_email, :supervisor_email, :leave_type,
                                :start_date, :end_date, :reason, :employee_space, :status, 
                                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """),
                    {
                        "request_id": request_id,
                        "employee_email": request_data.get("employee_email"),
                        "supervisor_email": request_data.get("supervisor_email"),
                        "leave_type": request_data.get("leave_type"),
                        "start_date": request_data.get("start_date"),
                        "end_date": request_data.get("end_date"),
                        "reason": request_data.get("reason"),
                        "employee_space": request_data.get("employee_space"),
                        "status": request_data.get("status", "PENDING")
                    }
                )
                conn.commit()
                return {"request_id": request_id, "status": "CREATED"}
                
    except Exception as e:
        print(f"Error creating leave request: {e}")
        raise

def get_leave_request(request_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a leave request by request_id.
    
    Args:
        request_id: Unique request identifier
        
    Returns:
        Dict with leave request details or None if not found
    """
    try:
        engine = _get_engine()
        
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT request_id, employee_email, supervisor_email, leave_type,
                           start_date, end_date, reason, employee_space, status,
                           created_at, updated_at, approved_at, decision_note
                    FROM public.leave_requests 
                    WHERE request_id = :request_id 
                    LIMIT 1
                """),
                {"request_id": request_id}
            )
            
            row = result.fetchone()
            
            if row:
                return {
                    "request_id": row.request_id,
                    "employee_email": row.employee_email,
                    "supervisor_email": row.supervisor_email,
                    "leave_type": row.leave_type,
                    "start_date": str(row.start_date) if row.start_date else None,
                    "end_date": str(row.end_date) if row.end_date else None,
                    "reason": row.reason,
                    "employee_space": row.employee_space,
                    "status": row.status,
                    "created_at": str(row.created_at) if row.created_at else None,
                    "updated_at": str(row.updated_at) if row.updated_at else None,
                    "approved_at": str(row.approved_at) if row.approved_at else None,
                    "decision_note": row.decision_note
                }
            
            return None
            
    except Exception as e:
        print(f"Error retrieving leave request: {e}")
        return None

def update_leave_request_status(request_id: str, new_status: str, decision_note: str = None) -> bool:
    """
    Update leave request status (APPROVED, DECLINED, CANCELLED).
    
    Args:
        request_id: Unique request identifier
        new_status: New status (APPROVED, DECLINED, CANCELLED)
        decision_note: Optional note from supervisor
        
    Returns:
        True if successful, False otherwise
    """
    try:
        engine = _get_engine()
        
        with engine.connect() as conn:
            update_params = {
                "request_id": request_id,
                "status": new_status,
                "updated_at": datetime.now()
            }
            
            update_query = """
                UPDATE public.leave_requests 
                SET status = :status,
                    updated_at = :updated_at
            """
            
            if new_status == "APPROVED":
                update_query += ", approved_at = CURRENT_TIMESTAMP"
            
            if decision_note:
                update_query += ", decision_note = :decision_note"
                update_params["decision_note"] = decision_note
            
            update_query += " WHERE request_id = :request_id"
            
            result = conn.execute(text(update_query), update_params)
            conn.commit()
            
            return result.rowcount > 0
            
    except Exception as e:
        print(f"Error updating leave request status: {e}")
        return False
