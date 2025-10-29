from typing import Dict, Any
from langchain_core.tools import tool

from ..sql.agent import get_sql_agent_executor


@tool
def allocate_resource(resource_type: str, quantity: int, project: str) -> Dict[str, Any]:
    """Allocate a resource to a project. Stub tool."""
    return {"status": "ALLOCATED", "resource_type": resource_type, "quantity": quantity, "project": project}


def _sanitize_user_text(text: str) -> str:
    """Remove technical/internal references from text for end-user display."""
    if not isinstance(text, str):
        return text
    replacements = {
        "SQL agent": "data service",
        "SQL Agent": "data service",
        "tool": "process",
        "tools": "processes",
        "query": "check",
        "Query": "Check",
        "schema": "data",
        "database schema": "data",
        "execute": "run",
        "execution": "processing",
    }
    out = text
    for k, v in replacements.items():
        out = out.replace(k, v)
    return out


@tool("run_sql_agent")
def run_sql_agent(natural_language_request: str) -> str:
    """
    Call the SQL sub-agent with a natural language request to inspect schema and query data.
    The SQL agent will use list_public_tables/describe_table_columns/execute_sql_query tools as needed.
    """
    try:
        executor = get_sql_agent_executor()
        result = executor.invoke({"input": natural_language_request})
        return _sanitize_user_text(result.get("output", ""))
    except Exception as e:
        # Return a non-technical message
        return "I couldn’t retrieve that information right now. Please try again in a moment."


@tool("get_allocation_info")
def get_allocation_info(request: str) -> str:
    """Retrieve allocation info by delegating to the SQL agent with an allocation-focused request.

    Use this when the user asks about allocation percentage, type, role, dates, whether allocated, end_notified, resource details,
    segment, or on-site/off-site location. Automatically asks the SQL agent to look into the allocation table
    and join employee for resource name/email.
    """
    try:
        executor = get_sql_agent_executor()
        nl = (
            "You are checking allocation data. Verify allocation table columns using describe_table_columns if needed. "
            "Answer only from the allocation table and join to employee on allocation.resource_id = employee.id for names/emails. "
            "Respect time filters if provided (current = today between start_date and end_date; or overlap with a range). "
            "Return a concise, non-technical summary. Query to fulfill: " + request
        )
        result = executor.invoke({"input": nl})
        return _sanitize_user_text(result.get("output", ""))
    except Exception:
        return "I couldn’t retrieve the allocation details right now. Please try again shortly."


RM_TOOLS = [allocate_resource, run_sql_agent, get_allocation_info]


@tool("get_project_open_roles_info")
def get_project_open_roles_info(request: str) -> str:
    """Retrieve project open roles and status. Delegates to SQL agent with focused guidance.

    The SQL agent should:
    - Look up project_status and open_roles from the project table by project name (fuzzy match acceptable with LIMIT 1).
    - If status is Completed/Cancelled (case-insensitive), report no openings.
    - Else, interpret open_roles depending on its type (numeric/boolean/json array) and summarize.
    """
    try:
        executor = get_sql_agent_executor()
        nl = (
            "You are fetching project status and open roles. Verify columns with describe_table_columns first. "
            "Query the project table for project_status and open_roles by project name (ILIKE, LIMIT 1). "
            "If status indicates completed or cancelled, respond that no roles are open regardless of open_roles. "
            "Otherwise, summarize availability based on open_roles type (numeric count, boolean, or array length). "
            "Return a short, user-friendly summary. Task: " + request
        )
        result = executor.invoke({"input": nl})
        return _sanitize_user_text(result.get("output", ""))
    except Exception:
        return "I couldn’t retrieve the project’s open roles right now. Please try again shortly."


# Export the new tool
RM_TOOLS.append(get_project_open_roles_info)


@tool("get_available_resources")
def get_available_resources(request: str) -> str:
    """Find available resources matching specific criteria for project staffing.
    
    Use this when the user asks about:
    - Available resources by role, designation, or seniority (e.g., 'Software Engineer', 'Senior Software Engineer', 'BA')
    - Resources with specific tech stack/skills (e.g., 'React', 'Node.js', 'Python')
    - Team composition for new projects
    - Resource availability during a specific time period
    
    The SQL agent should:
    - Query the employee table for resources matching designation, track, competency, or skills
    - Check the allocation table to find who is available during the requested time period
    - Use date overlap logic to exclude unavailable resources
    - Return name, designation, key skills/competencies, and availability status
    - Group results by role/designation for clarity
    """
    try:
        executor = get_sql_agent_executor()
        nl = (
            "You are finding available resources for project staffing. "
            "Steps to follow:\n"
            "1. Verify the employee and allocation table schemas using describe_table_columns.\n"
            "2. From the request, extract: required roles/designations, tech stack/skills, and time period.\n"
            "3. Query the employee table to find resources matching the criteria (check designation, track, competency, primary_skills, or skills columns).\n"
            "4. For each matching employee, check the allocation table to see if they're available during the time period.\n"
            "5. A resource is unavailable if they have any allocation where (allocation.start_date <= requested_end_date AND allocation.end_date >= requested_start_date).\n"
            "6. Return available resources grouped by role, showing: name, email, designation, key skills, and availability status.\n"
            "7. If no exact matches, suggest resources with related skills.\n"
            "8. Present in a clear, user-friendly format.\n"
            "Task: " + request
        )
        result = executor.invoke({"input": nl})
        return _sanitize_user_text(result.get("output", ""))
    except Exception:
        return "I couldn't retrieve the available resources right now. Please try again shortly."


# Export the new tool
RM_TOOLS.append(get_available_resources)



