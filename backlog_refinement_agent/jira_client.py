# backlog_refinement_agent/jira_client.py
from typing import List, Dict, Any, Optional
import requests
from requests.auth import HTTPBasicAuth
from .config import settings
import json
import pandas as pd
from .refinement import extract_full_description

def post_comment_to_jira(issue_key: str, comment_lines: list[str], reporter_name: str = "", account_id: str = "") -> None: 
    """
    Posts a comment to the given Jira issue with optional user mention using accountId.

    :param issue_key: The Jira ticket ID (e.g., DEV-1234)
    :param comment_lines: List of lines to include in the comment
    :param reporter_name: Display name of the user (for @mention text only)
    :param account_id: Jira accountId of the user (used for actual tagging)
    """

    content_blocks = []

    # Add @mention block if reporter's account ID is available
    if account_id:
        content_blocks.append({
            "type": "paragraph",
            "content": [
                {
                    "type": "mention",
                    "attrs": {
                        "id": account_id,
                        "text": f"@{reporter_name}" if reporter_name else "@reporter"
                    }
                },
                {"type": "text", "text": ", Please review the following issues identified during backlog refinement:"}
            ]
        })

    # Add main comment content
    for line in comment_lines:
        content_blocks.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": line}]
        })

    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": content_blocks
        }
    }

    url = f"{settings.jira.base_url}/rest/api/3/issue/{issue_key}/comment"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    auth = HTTPBasicAuth(settings.jira.email, settings.jira.api_token)

    response = requests.post(url, headers=headers, json=payload, auth=auth)

    if response.status_code == 201:
        print(f"Comment posted to Jira ticket: {issue_key}")
    else:
        print(f"Failed to post comment to {issue_key}")
        print(f"Status: {response.status_code}")
        print("Response:", response.text)


    
def fetch_issues_from_jira(
    project_key: Optional[str] = None,
    max_results: Optional[int] = None,
) -> pd.DataFrame:


    project_key = project_key or settings.jira.project_key
    max_results =max_results or settings.jira.max_results

    if not project_key:
        raise ValueError("JIRA_PROJECT_KEY is not set in .env")
 
    jql_query = (
        f"project = {project_key} AND issuetype = Story "
        f"AND Sprint is EMPTY ORDER BY created DESC"
    )

    url = f"{settings.jira.base_url}/rest/api/3/search/jql"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    auth = HTTPBasicAuth(settings.jira.email, settings.jira.api_token)

    payload = {
        "jql": jql_query,
        "maxResults": max_results,
        "fields": [
            "summary",
            "description",
            "fixVersions",
            "components",
            "reporter",
        ],
        "fieldsByKeys": False,
    }

    response = requests.post(url, headers=headers, auth=auth, json=payload)
    
    if response.status_code != 200:
        raise Exception(
            f"Failed to fetch issues: {response.status_code} - {response.text}"
        )

    data = response.json()
    total = data.get("total")
    
    parsed_issues = []

    # For the new endpoint, issues are still under "issues"x
    for issue in data.get("issues", []):
        fields = issue.get("fields", {})

        issue_id = issue.get("key")
        summary = fields.get("summary", "") or ""
        description_block = fields.get("description")
        description = (
            extract_full_description(description_block) if description_block else ""
        )

        fix_versions = fields.get("fixVersions") or []
        components = fields.get("components") or []
        reporter = fields.get("reporter") or {}

        fix_version_names = [fv.get("name") for fv in fix_versions if fv.get("name")]
        component_names = [c.get("name") for c in components if c.get("name")]

        reporter_display_name = reporter.get("displayName", "")
        reporter_account_id = reporter.get("accountId", "")

        row = {
            "id": issue_id,
            "summary": summary,
            "description": description,
            "fixVersions": ", ".join(fix_version_names) if fix_version_names else "",
            "components": ", ".join(component_names) if component_names else "",
            "reporter": reporter_display_name,
            "account_id": reporter_account_id,
        }

        present_fields = [k for k, v in row.items() if v not in ("", None)]
        row["present_fields"] = present_fields

        parsed_issues.append(row)

    df = pd.DataFrame(parsed_issues)
    return df