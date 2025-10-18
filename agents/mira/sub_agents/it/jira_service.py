from typing import Any, Dict, Optional
from agents.config.jira_config import JiraSettings, build_jira_session

class JiraService:
    def __init__(self, settings: Optional[JiraSettings] = None):
        self.settings = settings or JiraSettings.from_env()
        self.session = build_jira_session(self.settings)
        self.base = self.settings.base_url

    def create_customer_request(
        self,
        summary: str,
        description: str,
        requester_email: Optional[str] = None,
        service_desk_id: Optional[str] = None,
        request_type_id: Optional[str] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        sd_id = service_desk_id or self.settings.service_desk_id
        rt_id = request_type_id or self.settings.request_type_id
        raise_on_behalf = requester_email or self.settings.default_requester_email

        if not sd_id or not rt_id:
            raise ValueError("Missing service desk or request type ID. Set JIRA_SERVICE_DESK_ID and JIRA_REQUEST_TYPE_ID.")
        if not raise_on_behalf:
            raise ValueError("Requester email missing. Provide requester_email or set JIRA_DEFAULT_REQUESTER_EMAIL.")

        payload: Dict[str, Any] = {
            "serviceDeskId": str(sd_id),
            "requestTypeId": str(rt_id),
            "requestFieldValues": {
                "summary": summary,
                "description": description,
            },
            "raiseOnBehalfOf": raise_on_behalf,
        }
        if extra_fields:
            payload["requestFieldValues"].update(extra_fields)

        url = f"{self.base}/rest/servicedeskapi/request"
        resp = self.session.post(url, json=payload)
        if not resp.ok:
            raise RuntimeError(f"Jira create request failed: {resp.status_code} {resp.text}")

        data = resp.json()
        # Typical keys: issueId, issueKey, _links.web (customer portal URL)
        return {
            "issueId": data.get("issueId"),
            "issueKey": data.get("issueKey"),
            "web": (data.get("_links") or {}).get("web"),
            "self": (data.get("_links") or {}).get("self"),
        }

    def get_request_status(self, issue_id_or_key: str) -> Dict[str, Any]:
        url = f"{self.base}/rest/servicedeskapi/request/{issue_id_or_key}"
        resp = self.session.get(url)
        if not resp.ok:
            raise RuntimeError(f"Jira get status failed: {resp.status_code} {resp.text}")
        data = resp.json()
        # status name lives under currentStatus.status
        status_name = ((data.get("currentStatus") or {}).get("status") or {}).get("name")
        return {
            "issueId": data.get("issueId"),
            "issueKey": data.get("issueKey"),
            "status": status_name,
            "summary": ((data.get("requestFieldValues") or [{}])[0] or {}).get("value"),
            "web": (data.get("_links") or {}).get("web"),
        }