from typing import Any, Dict, List, Optional
import json
import re
from datetime import date, datetime
import requests

from agents.config.jira_config import (
    JIRA_BASE_URL,
    JIRA_EMAIL,
    JIRA_API_TOKEN,
    JIRA_PROJECT_KEY,
    JIRA_ISSUE_TYPE_NAME,
    JIRA_ISSUE_TYPE_ID,
    JIRA_CF_PRODUCT,
    JIRA_CF_REQUESTED_FOR,
    JIRA_CF_LOCATION,
    JIRA_CF_APPROVER,
    JIRA_CF_INTENT,
    JIRA_DEBUG,
    JIRA_USE_SERVICE_DESK,
    JIRA_SERVICE_DESK_ID,
    JIRA_REQUEST_TYPE_ID_MAP,  # optional JSON, not required
)

# Your static request type name -> id mapping
DEFAULT_REQUEST_TYPE_NAME_TO_ID = {
    "get it help": "7",
    "onboard new employees": "16",
    "request a new account": "11",
    "request admin access": "9",
    "request new hardware": "17",
    "request new software": "12",
}

def _to_adf(text: Optional[str]) -> Dict[str, Any]:
    return {
        "type": "doc",
        "version": 1,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text or ""}]}],
    }

def _norm_name(s: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (s or "").lower()))

def _infer_request_type_name(summary: str, description: Optional[str], labels: Optional[List[str]], custom_fields: Optional[Dict[str, Any]]) -> str:
    name = str((custom_fields or {}).get("request_type_name") or "").strip()
    if name:
        return name
    text = f"{summary} {description or ''} {' '.join(labels or [])}".lower()
    if any(k in text for k in ["onboard", "new hire", "on-boarding", "onboarding"]):
        return "Onboard new employees"
    if any(k in text for k in ["admin access", "elevated", "privileged", "local admin"]):
        return "Request admin access"
    if any(k in text for k in ["new account", "create account", "account provision", "account request"]):
        return "Request a new account"
    if any(k in text for k in ["laptop", "monitor", "dock", "docking", "headset", "keyboard", "mouse", "hardware", "device"]):
        return "Request new hardware"
    if any(k in text for k in ["software", "install", "license", "subscription", "app access"]):
        return "Request new software"
    return "Get IT help"

class JiraService:
    def __init__(self, base_url: Optional[str] = None, email: Optional[str] = None, api_token: Optional[str] = None, project_key: Optional[str] = None):
        self.base_url = (base_url or JIRA_BASE_URL or "").rstrip("/")
        self.email = email or JIRA_EMAIL
        self.api_token = api_token or JIRA_API_TOKEN
        self.project_key = project_key or JIRA_PROJECT_KEY

        missing = [k for k, v in {
            "JIRA_BASE_URL": self.base_url, "JIRA_EMAIL": self.email, "JIRA_API_TOKEN": self.api_token, "JIRA_PROJECT_KEY": self.project_key,
        }.items() if not v]
        if missing:
            raise ValueError(f"Missing Jira config: {', '.join(missing)}. Ensure these are set in .env")

        self.cf_map: Dict[str, str] = {}
        if JIRA_CF_PRODUCT:        self.cf_map["product"] = JIRA_CF_PRODUCT
        if JIRA_CF_REQUESTED_FOR:  self.cf_map["requested_for"] = JIRA_CF_REQUESTED_FOR
        if JIRA_CF_LOCATION:       self.cf_map["location"] = JIRA_CF_LOCATION
        if JIRA_CF_APPROVER:       self.cf_map["approver"] = JIRA_CF_APPROVER
        if JIRA_CF_INTENT:         self.cf_map["intent"] = JIRA_CF_INTENT

        self._createmeta_cache: Optional[Dict[str, Any]] = None

        # Service Desk dynamic settings
        self.use_sd = (JIRA_USE_SERVICE_DESK or "0") == "1"
        self.service_desk_id = JIRA_SERVICE_DESK_ID
        try:
            self.request_type_map = json.loads(JIRA_REQUEST_TYPE_ID_MAP) if JIRA_REQUEST_TYPE_ID_MAP else {}
        except Exception:
            self.request_type_map = {}

    def _headers(self) -> Dict[str, str]:
        return {"Accept": "application/json", "Content-Type": "application/json"}

    def _auth(self):
        return (self.email, self.api_token)

    def _get_createmeta(self) -> Dict[str, Any]:
        if self._createmeta_cache:
            return self._createmeta_cache
        url = f"{self.base_url}/rest/api/3/issue/createmeta?projectKeys={self.project_key}&expand=projects.issuetypes.fields"
        resp = requests.get(url, auth=self._auth(), headers=self._headers(), timeout=30)
        if JIRA_DEBUG == "1" and not resp.ok:
            try:
                print("CreateMeta:", json.dumps(resp.json(), indent=2))
            except Exception:
                print("CreateMeta Text:", resp.text)
        resp.raise_for_status()
        self._createmeta_cache = resp.json()
        return self._createmeta_cache

    def _resolve_issue_type(self, preferred_name: Optional[str]) -> Dict[str, str]:
        if JIRA_ISSUE_TYPE_ID:
            return {"id": JIRA_ISSUE_TYPE_ID}

        meta = self._get_createmeta()
        projects = meta.get("projects", [])
        if not projects:
            raise ValueError(f"No createmeta for project {self.project_key}")
        issuettypes = projects[0].get("issuetypes", []) or []

        def find(name: str) -> Optional[Dict[str, Any]]:
            for it in issuettypes:
                if str(it.get("name", "")).lower() == name.lower():
                    return it
            return None

        for name in [preferred_name, JIRA_ISSUE_TYPE_NAME]:
            if name:
                it = find(name)
                if it:
                    return {"id": it["id"]}

        for name in ["Task", "Incident", "Service request with approvals", "Service request"]:
            it = find(name)
            if it:
                return {"id": it["id"]}

        if issuettypes:
            return {"id": issuettypes[0]["id"]}

        raise ValueError("Unable to resolve a valid issue type for this project.")

    def _get_request_types(self, service_desk_id: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/servicedeskapi/servicedesk/{service_desk_id}/requesttype"
        resp = requests.get(url, auth=self._auth(), headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json() or {}
        return data.get("values", []) or []

    def _get_request_types_map(self, service_desk_id: str) -> Dict[str, str]:
        m: Dict[str, str] = {}
        for rt in self._get_request_types(service_desk_id):
            name = str(rt.get("name", ""))
            if name:
                m[_norm_name(name)] = str(rt.get("id"))
        return m

    def _pick_request_type_id(self, summary: str, description: Optional[str], labels: Optional[List[str]], custom_fields: Optional[Dict[str, Any]]) -> Optional[str]:
        # 1) Explicit override
        rt_id = (custom_fields or {}).get("request_type_id")
        if rt_id:
            return str(rt_id)
        rt_name = (custom_fields or {}).get("request_type_name")
        if rt_name and self.service_desk_id:
            live = self._get_request_types_map(self.service_desk_id)
            nid = live.get(_norm_name(rt_name))
            if nid:
                return nid

        # 2) Infer by heuristics
        name = _infer_request_type_name(summary, description, labels, custom_fields)
        norm = _norm_name(name)

        # 3) Prefer your static table
        if norm in DEFAULT_REQUEST_TYPE_NAME_TO_ID:
            return DEFAULT_REQUEST_TYPE_NAME_TO_ID[norm]

        # 4) Optional env JSON map
        if norm in self.request_type_map:
            return str(self.request_type_map[norm])

        # 5) Live map from Jira
        if self.service_desk_id:
            live = self._get_request_types_map(self.service_desk_id)
            if norm in live:
                return live[norm]

        return None

    def _fallback_request_type_id(self) -> Optional[str]:
        # Ensure we still create a customer request with a safe default
        return DEFAULT_REQUEST_TYPE_NAME_TO_ID.get("get it help")

    def _create_customer_request(self, summary: str, description: Optional[str], request_type_id: str, service_desk_id: str) -> str:
        url = f"{self.base_url}/rest/servicedeskapi/request"
        payload = {
            "serviceDeskId": str(service_desk_id),
            "requestTypeId": str(request_type_id),
            "requestFieldValues": {
                "summary": summary[:254],
                "description": description or summary,
            },
        }
        headers = {**self._headers(), "X-ExperimentalApi": "opt-in"}
        if JIRA_DEBUG == "1":
            print("Create Customer Request Payload:", json.dumps(payload, indent=2))
        resp = requests.post(url, json=payload, auth=self._auth(), headers=headers, timeout=30)
        if JIRA_DEBUG == "1" and not resp.ok:
            try:
                print("Create Customer Request Error:", resp.status_code, json.dumps(resp.json(), indent=2))
            except Exception:
                print("Create Customer Request Error Text:", resp.text)
        resp.raise_for_status()
        data = resp.json()
        return data.get("issueKey") or data.get("key") or str(data.get("requestId"))

    def create_ticket(self, summary: str, description: Optional[str] = None, issue_type: str = "Service Request", priority: Optional[str] = None, labels: Optional[List[str]] = None, custom_fields: Optional[Dict[str, Any]] = None) -> str:
        # Always create via Service Desk when enabled so "Request Type" is set
        if self.use_sd and self.service_desk_id:
            rt_id = self._pick_request_type_id(summary, description, labels, custom_fields) or self._fallback_request_type_id()
            if not rt_id:
                raise ValueError("Unable to resolve a Service Desk requestTypeId. Provide custom_fields.request_type_name or configure the static name->id map.")
            if JIRA_DEBUG == "1":
                print(f"Using Service Desk requestTypeId={rt_id}")
            return self._create_customer_request(summary, description or summary, rt_id, self.service_desk_id)

        # Fallback to core API (will NOT set Request Type)
        issuetype_obj = self._resolve_issue_type(issue_type)
        fields: Dict[str, Any] = {
            "project": {"key": self.project_key},
            "summary": summary[:254],
            "issuetype": issuetype_obj,
            "description": _to_adf(description or summary),
        }
        if priority:
            fields["priority"] = {"name": priority}
        if labels:
            lbls = [l for l in labels if l]
            if lbls:
                fields["labels"] = lbls

        if custom_fields and custom_fields.get("due_date"):
            due_norm = _normalize_due_date(custom_fields.get("due_date"))
            if due_norm:
                fields["duedate"] = due_norm
            elif JIRA_DEBUG == "1":
                print(f"Skipping invalid due_date: {custom_fields.get('due_date')!r}")

        if custom_fields:
            for logical_name, value in custom_fields.items():
                if value in (None, "", []):
                    continue
                cf_id = self.cf_map.get(logical_name)
                if cf_id:
                    fields[cf_id] = value

        payload = {"fields": fields}
        if JIRA_DEBUG == "1":
            print("Create Issue Payload:", json.dumps(payload, indent=2))

        resp = requests.post(
            f"{self.base_url}/rest/api/3/issue",
            json=payload,
            auth=self._auth(),
            headers=self._headers(),
            timeout=30,
        )
        if JIRA_DEBUG == "1" and not resp.ok:
            try:
                print("Create Issue Error:", resp.status_code, json.dumps(resp.json(), indent=2))
            except Exception:
                print("Create Issue Error Text:", resp.text)

        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            try:
                details = resp.json()
            except Exception:
                details = resp.text
            raise requests.HTTPError(f"Jira issue create failed: {e} | details={details}") from e

        return resp.json()["key"]

    def get_issue_status(self, issue_id_or_key: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/3/issue/{issue_id_or_key}?fields=status"
        resp = requests.get(url, auth=self._auth(), headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        fields = data.get("fields", {}) or {}
        status = fields.get("status", {}) or {}
        return {
            "key": data.get("key", issue_id_or_key),
            "status": status.get("name"),
            "statusCategory": (status.get("statusCategory") or {}).get("name"),
        }

    # Back-compat
    def get_request_status(self, issue_id_or_key: str) -> Dict[str, Any]:
        return self.get_issue_status(issue_id_or_key)