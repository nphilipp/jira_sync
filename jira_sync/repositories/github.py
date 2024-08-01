"""
Module for communicating with the GitHub REST API.

See https://docs.github.com/en/rest?apiVersion=2022-11-28
"""

from typing import Any, ClassVar

from requests import Response
from requests.utils import parse_header_links

from .base import Issue, IssueStatus, Repository


class GitHubRepository(Repository):
    """Wrapper class around the GitHub REST API for a single repository."""

    type = "github"
    API_VERSION: ClassVar[str] = "2022-11-28"

    def get_next_page(
        self,
        *,
        endpoint: str | None = None,
        response: Response | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> dict[str, Any] | None:
        if response:
            if "link" not in response.headers:
                return None

            for link in parse_header_links(response.headers["link"]):
                if link["rel"] == "next":
                    url = link["url"]
                    break
            else:
                return None
        else:
            if endpoint:
                endpoint = "/" + endpoint.lstrip("/")
            else:
                endpoint = ""

            url = f"{self.instance_api_url}/repos/{self.repo}{endpoint}"

        _headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.API_VERSION,
        }

        if self.token:
            _headers["Authorization"] = f"Bearer {self.token}"

        if headers:
            _headers |= headers

        kwargs["headers"] = _headers

        return self.sanitize_requests_params(kwargs | {"url": url})

    def normalize_issue(self, api_result: dict[str, Any]) -> Issue:
        full_url = api_result["html_url"]
        title = api_result["title"]
        content = api_result["body"]
        _assignee = api_result["assignee"]
        _state = api_result["state"].lower()
        _labels = [
            label["name"] if isinstance(label, dict) else label for label in api_result["labels"]
        ]

        if _assignee:
            assignee = _assignee["login"]
        else:
            assignee = None

        if _state != "closed":
            if self.blocked_label and self.blocked_label in _labels:
                status = IssueStatus.blocked
            else:
                if not _assignee:
                    status = IssueStatus.new
                else:
                    status = IssueStatus.assigned
        else:
            status = IssueStatus.closed

        return Issue(
            repository=self,
            full_url=full_url,
            title=title,
            content=content,
            assignee=assignee,
            status=status,
        )

    def get_issue_params(self) -> dict[str, Any]:
        if not self.label:
            return {}
        return {"params": {"labels": self.label}}
