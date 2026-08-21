import json
import urllib.error
import urllib.request

from keboola.component.exceptions import UserException

API_BASE_URL = "https://api.github.com"
API_VERSION = "2022-11-28"
USER_AGENT = "keboola-custom-python-component"
PAGE_SIZE = 100
REQUEST_TIMEOUT = 30
# a user access token never reaches anywhere near this many pages, it is a runaway guard only
MAX_PAGES = 50


class GitHubApi:
    """Read-only client for the endpoints needed to list the repositories the app may read."""

    def __init__(self, token: str, base_url: str = API_BASE_URL):
        self.token = token
        self.base_url = base_url.rstrip("/")

    def list_installation_repositories(self) -> list[dict]:
        """Repositories of every app installation visible to the authorizing user, as dropdown options.

        The value is the clone URL, so that selecting a repository fills in the same thing the other
        authentication methods expect to be typed in by hand.
        """
        options = []
        for installation in self._get_all("/user/installations", "installations"):
            path = f"/user/installations/{installation['id']}/repositories"
            for repository in self._get_all(path, "repositories"):
                options.append({"value": repository["clone_url"], "label": repository["full_name"]})

        return options

    def _get_all(self, path: str, items_key: str) -> list[dict]:
        items: list[dict] = []
        for page in range(1, MAX_PAGES + 1):
            payload = self._get(f"{path}?per_page={PAGE_SIZE}&page={page}")
            page_items = payload.get(items_key, [])
            items.extend(page_items)
            if not page_items or len(items) >= payload.get("total_count", 0):
                break

        return items

    def _get(self, path: str) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": API_VERSION,
                # GitHub rejects requests without a User-Agent
                "User-Agent": USER_AGENT,
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                return json.load(response)
        except urllib.error.HTTPError as err:
            raise UserException(self._explain_http_error(err.code, err.reason)) from err
        except urllib.error.URLError as err:
            raise UserException(f"Could not reach the GitHub API: {err.reason}") from err

    @staticmethod
    def _explain_http_error(code: int, reason: str) -> str:
        if code == 401:
            return (
                "The GitHub authorization is no longer valid. Please authorize the component again in the "
                "Authorization section of the configuration."
            )
        if code == 403:
            return "The GitHub API refused the request. The authorization may not have the required permissions."

        return f"The GitHub API returned an unexpected error: HTTP {code} {reason}"
