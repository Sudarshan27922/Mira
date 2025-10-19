import json
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import requests
try:
    from dateutil import parser as date_parser
except Exception:
    date_parser = None

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
)

def _to_adf(text: str) -> Dict[str, Any]:
    return {
        "type": "doc",
        "version": 1,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text or ""}]}],
    }

def _normalize_due_date(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date().strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, str):
        s = value.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return s
        try:
            d = datetime.fromisoformat(s)
            return d.date().strftime("%Y-%m-%d")
        except Exception:
            pass
        if date_parser:
            try:
                d = date_parser.parse(s, dayfirst=False, fuzzy=True)
                return d.date().strftime("%Y-%m-%d")
            except Exception:
                return None
    return None

class JiraService:
    def __init__(
        self,
        base_url: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
        project_key: Optional[str] = None,
    ):
        self.base_url = (base_url or JIRA_BASE_URL or "").rstrip("/")
        self.email = email or JIRA_EMAIL
        self.api_token = api_token or JIRA_API_TOKEN
        self.project_key = project_key or JIRA_PROJECT_KEY

        missing = [k for k, v in {
            "JIRA_BASE_URL": self.base_url,
            "JIRA_EMAIL": self.email,
            "JIRA_API_TOKEN": self.api_token,
            "JIRA_PROJECT_KEY": self.project_key,
        }.items() if not v]
        if missing:
            raise ValueError(f"Missing Jira config: {', '.join(missing)}. Set them in .env")

        self.cf_map: Dict[str, str] = {}
        if JIRA_CF_PRODUCT:        self.cf_map["product"] = JIRA_CF_PRODUCT
        if JIRA_CF_REQUESTED_FOR:  self.cf_map["requested_for"] = JIRA_CF_REQUESTED_FOR
        if JIRA_CF_LOCATION:       self.cf_map["location"] = JIRA_CF_LOCATION
        if JIRA_CF_APPROVER:       self.cf_map["approver"] = JIRA_CF_APPROVER
        if JIRA_CF_INTENT:         self.cf_map["intent"] = JIRA_CF_INTENT

        self._createmeta_cache: Optional[Dict[str, Any]] = None

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

    def create_ticket(
        self,
        summary: str,
        description: Optional[str] = None,
        issue_type: str = "Service Request",
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not summary or not summary.strip():
            raise ValueError("summary is required")

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