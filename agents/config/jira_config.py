import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # optional

def _load_env():
    if load_dotenv:
        here = Path(__file__).resolve()
        for parent in [here.parent, *here.parents]:
            env_path = parent / ".env"
            if env_path.exists():
                load_dotenv(dotenv_path=env_path, override=False)
                break

_load_env()

def _norm_url(value: str | None) -> str | None:
    if not value:
        return None
    return value.rstrip("/")

# Core Jira (issue API)
JIRA_BASE_URL = _norm_url(
    os.getenv("JIRA_BASE_URL")
    or os.getenv("JIRA_CLOUD_BASE_URL")
    or os.getenv("JIRA_DOMAIN")
)
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN") or os.getenv("JIRA_API_KEY")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

# Issue type controls
JIRA_ISSUE_TYPE_NAME = os.getenv("JIRA_ISSUE_TYPE_NAME", "Service Request")
JIRA_ISSUE_TYPE_ID = os.getenv("JIRA_ISSUE_TYPE_ID")  # optional

# Service Desk (portal) controls — all optional
JIRA_USE_SERVICE_DESK = os.getenv("JIRA_USE_SERVICE_DESK", "0")
JIRA_SERVICE_DESK_ID = os.getenv("JIRA_SERVICE_DESK_ID")
JIRA_REQUEST_TYPE_ID = os.getenv("JIRA_REQUEST_TYPE_ID")  # optional, not required
JIRA_REQUEST_TYPE_ID_HARDWARE = os.getenv("JIRA_REQUEST_TYPE_ID_HARDWARE")
JIRA_REQUEST_TYPE_ID_MAP = os.getenv("JIRA_REQUEST_TYPE_ID_MAP")  # optional JSON

# Optional custom fields
JIRA_CF_PRODUCT = os.getenv("JIRA_CF_PRODUCT")
JIRA_CF_REQUESTED_FOR = os.getenv("JIRA_CF_REQUESTED_FOR")
JIRA_CF_LOCATION = os.getenv("JIRA_CF_LOCATION")
JIRA_CF_APPROVER = os.getenv("JIRA_CF_APPROVER")
JIRA_CF_INTENT = os.getenv("JIRA_CF_INTENT")

JIRA_DEBUG = os.getenv("JIRA_DEBUG", "0")

__all__ = [
    "JIRA_BASE_URL",
    "JIRA_EMAIL",
    "JIRA_API_TOKEN",
    "JIRA_PROJECT_KEY",
    "JIRA_ISSUE_TYPE_NAME",
    "JIRA_ISSUE_TYPE_ID",
    "JIRA_USE_SERVICE_DESK",
    "JIRA_SERVICE_DESK_ID",
    "JIRA_REQUEST_TYPE_ID",
    "JIRA_REQUEST_TYPE_ID_HARDWARE",
    "JIRA_REQUEST_TYPE_ID_MAP",
    "JIRA_CF_PRODUCT",
    "JIRA_CF_REQUESTED_FOR",
    "JIRA_CF_LOCATION",
    "JIRA_CF_APPROVER",
    "JIRA_CF_INTENT",
    "JIRA_DEBUG",
]