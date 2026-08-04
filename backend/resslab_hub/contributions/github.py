"""
Thin async wrapper around githubkit for the contribution data repo.

Isolates the Git Data API surface (blobs -> tree -> commit -> ref -> PR) behind
a small class so the submission flow can be tested against a fake. The GitHub
App credentials are read from settings; `configured()` is the feature flag.

The App is installed on the single data repo with only `contents: write` and
`pull-requests: write`. githubkit refreshes the installation token per request
and never exposes it, so nothing here caches or logs credentials.
"""

from dataclasses import dataclass
from typing import List, Optional

from githubkit import AppInstallationAuthStrategy, GitHub

from resslab_hub.config import settings


def configured() -> bool:
    """True when every GitHub App credential is present."""
    return all(
        [
            settings.github_app_id,
            settings.github_app_private_key,
            settings.github_app_installation_id,
        ]
    )


@dataclass
class NewFile:
    """One file to commit: repo-relative path + full text content."""

    path: str
    content: str


class DataRepoClient:
    """Git Data API operations on the configured data repository."""

    def __init__(self) -> None:
        self.owner, self.repo = str(settings.data_repo).split("/", 1)
        self.base_branch: str = str(settings.data_repo_base_branch)
        self._gh = GitHub(
            AppInstallationAuthStrategy(
                app_id=str(settings.github_app_id),
                # Dynaconf reads the PEM from the env with literal "\n".
                private_key=str(settings.github_app_private_key).replace("\\n", "\n"),
                installation_id=int(settings.github_app_installation_id),
            )
        )

    async def get_file_text(self, path: str, ref: Optional[str] = None) -> str:
        """Text content of a repo file at `ref` (default: the base branch)."""
        response = await self._gh.rest.repos.async_get_content(
            self.owner,
            self.repo,
            path=path,
            ref=ref or self.base_branch,
            headers={"Accept": "application/vnd.github.raw+json"},
        )
        return response.content.decode("utf-8")

    async def get_base_sha(self) -> str:
        """Commit sha of the base branch head."""
        response = await self._gh.rest.git.async_get_ref(
            self.owner, self.repo, ref=f"heads/{self.base_branch}"
        )
        return response.parsed_data.object_.sha

    async def commit_files(
        self,
        branch: str,
        base_sha: str,
        files: List[NewFile],
        message: str,
        author_name: str,
        author_email: str,
    ) -> str:
        """Create `branch` off `base_sha` with one commit adding `files`.

        The contributor is the commit author; the committer defaults to the
        App's bot identity. Returns the commit sha.
        """
        git = self._gh.rest.git
        tree_entries = []
        for file in files:
            blob = await git.async_create_blob(
                self.owner, self.repo, content=file.content, encoding="utf-8"
            )
            tree_entries.append(
                {
                    "path": file.path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob.parsed_data.sha,
                }
            )
        tree = await git.async_create_tree(
            self.owner, self.repo, base_tree=base_sha, tree=tree_entries
        )
        commit = await git.async_create_commit(
            self.owner,
            self.repo,
            message=message,
            tree=tree.parsed_data.sha,
            parents=[base_sha],
            author={"name": author_name, "email": author_email},
        )
        commit_sha = commit.parsed_data.sha
        await git.async_create_ref(
            self.owner, self.repo, ref=f"refs/heads/{branch}", sha=commit_sha
        )
        return commit_sha

    async def create_pull_request(self, branch: str, title: str, body: str) -> dict:
        """Open a PR from `branch` into the base branch."""
        response = await self._gh.rest.pulls.async_create(
            self.owner,
            self.repo,
            title=title,
            head=branch,
            base=self.base_branch,
            body=body,
        )
        pull = response.parsed_data
        return {"url": pull.html_url, "number": pull.number}

    async def delete_branch(self, branch: str) -> None:
        """Best-effort cleanup of a branch whose PR could not be opened."""
        try:
            await self._gh.rest.git.async_delete_ref(
                self.owner, self.repo, ref=f"heads/{branch}"
            )
        except Exception:
            pass
