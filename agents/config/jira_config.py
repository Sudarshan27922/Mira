import os
from dataclasses import dataclass
from typing import Optional
import requests
from requests.auth import HTTPBasicAuth

@dataclass
class JiraSettings:
    base_url: str
    email: str
    api_token: str
    service_desk_id: Optional[str] = None
    request_type_id: Optional[str] = None
    default_requester_email: Optional[str] = None

    @staticmethod
    def from_env() -> "JiraSettings":
        return JiraSettings(
            base_url=os.getenv("JIRA_CLOUD_BASE_URL", "").rstrip("/"),
            email=os.getenv("JIRA_EMAIL", ""),
            api_token=os.getenv("JIRA_API_TOKEN", ""),
            service_desk_id=os.getenv("JIRA_SERVICE_DESK_ID", None),
            request_type_id=os.getenv("JIRA_REQUEST_TYPE_ID", None),
            default_requester_email=os.getenv("JIRA_DEFAULT_REQUESTER_EMAIL", None),
        )

def build_jira_session(settings: JiraSettings) -> requests.Session:
    if not settings.base_url or not settings.email or not settings.api_token:
        raise ValueError("Missing Jira credentials. Set JIRA_CLOUD_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN.")
    s = requests.Session()
    s.auth = HTTPBasicAuth(settings.email, settings.api_token)
    s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
    return s