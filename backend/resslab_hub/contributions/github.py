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

    @staticmethod
    def _pull_dict(pull) -> dict:
        return {
            "number": pull.number,
            "html_url": pull.html_url,
            "author": pull.user.login if pull.user else "",
            "author_type": pull.user.type if pull.user else "",
            "title": pull.title,
            "state": pull.state,
            "draft": bool(pull.draft),
            "head_ref": pull.head.ref,
            "head_sha": pull.head.sha,
            "base_ref": pull.base.ref,
            "created_at": str(pull.created_at),
            "updated_at": str(pull.updated_at),
            "body": pull.body or "",
        }

    async def list_open_pulls(self) -> List[dict]:
        """Open PRs into the base branch, newest first (one page, 100 max)."""
        response = await self._gh.rest.pulls.async_list(
            self.owner,
            self.repo,
            state="open",
            base=self.base_branch,
            sort="created",
            direction="desc",
            per_page=100,
        )
        return [self._pull_dict(pull) for pull in response.parsed_data]

    async def get_pull(self, number: int) -> dict:
        """One PR by number (any state)."""
        response = await self._gh.rest.pulls.async_get(self.owner, self.repo, number)
        return self._pull_dict(response.parsed_data)

    async def list_pull_files(self, number: int) -> List[dict]:
        """Changed files of a PR: path + status, paginated up to 300 files."""
        files: List[dict] = []
        for page in range(1, 4):
            response = await self._gh.rest.pulls.async_list_files(
                self.owner, self.repo, number, per_page=100, page=page
            )
            batch = response.parsed_data
            files.extend(
                {"path": file.filename, "status": file.status} for file in batch
            )
            if len(batch) < 100:
                break
        return files

    @staticmethod
    def _comment_dict(comment) -> dict:
        # `IssueComment.body` is `Missing[str] | None` — githubkit answers its
        # UNSET sentinel for a comment posted with no body, which is neither a
        # str nor None, so guard on the type rather than on falsiness.
        body = comment.body if isinstance(comment.body, str) else ""
        return {
            "id": comment.id,
            "author": comment.user.login if comment.user else "",
            "author_type": comment.user.type if comment.user else "",
            "body": body,
            "html_url": comment.html_url,
            "created_at": str(comment.created_at),
            "updated_at": str(comment.updated_at),
        }

    async def list_issue_comments(self, number: int) -> List[dict]:
        """Conversation comments on a PR, oldest first (one page, 100 max).

        Review comments (inline, anchored to a diff hunk) are a different
        resource and are deliberately left out: this feeds the review screen's
        discussion panel, and line-anchored remarks only read next to the diff.
        """
        response = await self._gh.rest.issues.async_list_comments(
            self.owner, self.repo, number, per_page=100
        )
        return [self._comment_dict(comment) for comment in response.parsed_data]

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
