"""
Thin async wrapper around githubkit for the contribution data repo.

Isolates the Git Data API surface (blobs -> tree -> commit -> ref -> PR) behind
a small class so the submission flow can be tested against a fake. The GitHub
App credentials are read from settings; `configured()` is the feature flag.

The App is installed on the single data repo with only `contents: write` and
`pull-requests: write`. githubkit caches the installation token in the process
and never exposes it, so nothing here caches or logs credentials.

One `GitHub` object is shared by the whole process (`_github()`), and its httpx
client is kept open between calls: see `_SharedGitHub` below.
"""

import asyncio
import hashlib
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator, Dict, List, Optional

import httpx
from githubkit import AppInstallationAuthStrategy, GitHub
from githubkit.exception import RequestFailed

from resslab_hub.config import settings

# GitHub calls per commit that may run at the same time. One connection pool
# is shared, so this is about not tripping the secondary rate limit, not about
# sockets.
MAX_PARALLEL_CALLS = 8

# No timeout at all is githubkit's default (`httpx.Timeout(None)`), which lets
# a stalled GitHub call hang a worker forever.
REQUEST_TIMEOUT = 30.0


def configured() -> bool:
    """True when every GitHub App credential is present."""
    return all(
        [
            settings.github_app_id,
            settings.github_app_private_key,
            settings.github_app_installation_id,
        ]
    )


def enabled() -> bool:
    """What the frontend reads on `/features`: the switch, and an App behind it.

    `CONTRIBUTIONS_ENABLED` alone decides whether the endpoints answer at all
    (`require_contributions_enabled`). Without the App they still answer, with
    the 503 they always had, but there is nothing to show in the interface.
    """
    return bool(settings.contributions_enabled) and configured()


def describe_error(exc: BaseException) -> str:
    """A failure in words a person can act on.

    githubkit's `RequestFailed` only says "Request failed": GitHub's own
    reason ("Resource not accessible by integration", "A pull request already
    exists ...") is in the response body. Any other error keeps its own text.
    """
    if not isinstance(exc, RequestFailed):
        return str(exc)
    response = exc.response
    try:
        body = response.raw_response.json()
    except ValueError:
        body = None
    reasons = []
    if isinstance(body, dict):
        reasons.append(str(body.get("message") or ""))
        for error in body.get("errors") or []:
            if isinstance(error, dict):
                reasons.append(str(error.get("message") or error.get("code") or ""))
            else:
                reasons.append(str(error))
    reason = "; ".join(r for r in reasons if r) or response.reason_phrase
    return f"GitHub answered {response.status_code}: {reason[:300]}"


@dataclass
class NewFile:
    """One file to commit: repo-relative path + full text content."""

    path: str
    content: str


def blob_sha(content: str) -> str:
    """The git object id of a blob holding `content`.

    Same rule as `git hash-object`: sha1 over "blob <bytes>\\0" + the data.
    Lets us compare a file we are about to send with what GitHub already has,
    and skip the upload when they match.
    """
    data = content.encode("utf-8")
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()  # nosec B324 - git object id


class _SharedGitHub(GitHub):
    """A `GitHub` that keeps one httpx client open for its whole life.

    githubkit builds a client, opens a connection and closes it again around
    *every* call (`get_async_client`), which cost this app a TCP handshake, a
    TLS handshake and a fresh SSL context (the certifi bundle is parsed each
    time, on the event loop) per request. A contribution commit makes tens of
    calls, so that overhead was most of its runtime.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._shared_client: Optional[httpx.AsyncClient] = None

    @asynccontextmanager
    async def get_async_client(self) -> AsyncGenerator[httpx.AsyncClient, None]:
        if self._shared_client is None:
            self._shared_client = self._create_async_client()
        yield self._shared_client

    async def aclose(self) -> None:
        """Close the shared client. Called on app shutdown."""
        client, self._shared_client = self._shared_client, None
        if client is not None:
            await client.aclose()


_shared_github: Optional[_SharedGitHub] = None


def _github() -> _SharedGitHub:
    """The process-wide GitHub App client, built on first use."""
    global _shared_github
    if _shared_github is None:
        _shared_github = _SharedGitHub(
            AppInstallationAuthStrategy(
                app_id=str(settings.github_app_id),
                # Dynaconf reads the PEM from the env with literal "\n".
                private_key=str(settings.github_app_private_key).replace("\\n", "\n"),
                installation_id=int(settings.github_app_installation_id),
            ),
            timeout=REQUEST_TIMEOUT,
        )
    return _shared_github


async def aclose_github() -> None:
    """Release the shared client, if one was ever built."""
    global _shared_github
    client, _shared_github = _shared_github, None
    if client is not None:
        await client.aclose()


class DataRepoClient:
    """Git Data API operations on the configured data repository."""

    def __init__(self) -> None:
        self.owner, self.repo = str(settings.data_repo).split("/", 1)
        self.base_branch: str = str(settings.data_repo_base_branch)
        self._gh = _github()

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
        """Changed files of a PR: path, status and blob sha at the head.

        Paginated up to 300 files. The sha is the head version's git object
        id, which `commit_on_branch` uses to skip re-uploading files that did
        not change.
        """
        files: List[dict] = []
        for page in range(1, 4):
            response = await self._gh.rest.pulls.async_list_files(
                self.owner, self.repo, number, per_page=100, page=page
            )
            batch = response.parsed_data
            files.extend(
                {"path": file.filename, "status": file.status, "sha": file.sha}
                for file in batch
            )
            if len(batch) < 100:
                break
        return files

    async def list_pull_commits(self, number: int) -> List[dict]:
        """Commits of a PR, oldest first (one page, 100 max).

        The message carries the submission's provenance trailers, so this is
        what the curation screen and the ownership check read.
        """
        response = await self._gh.rest.pulls.async_list_commits(
            self.owner, self.repo, number, per_page=100
        )
        commits = []
        for item in response.parsed_data:
            author = item.commit.author
            commits.append(
                {
                    "sha": item.sha,
                    "message": item.commit.message or "",
                    "author_name": getattr(author, "name", "") or "",
                    "author_email": getattr(author, "email", "") or "",
                    "author_date": str(getattr(author, "date", "") or ""),
                }
            )
        return commits

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

    async def list_dir(self, path: str, ref: Optional[str] = None) -> List[str]:
        """File names in a repo folder at `ref`, empty when it does not exist.

        GitHub lists up to 1000 entries this way; the largest curve folder of
        the data repo has about 350.
        """
        try:
            response = await self._gh.rest.repos.async_get_content(
                self.owner, self.repo, path=path, ref=ref or self.base_branch
            )
        except RequestFailed as exc:
            if exc.response.status_code == 404:
                return []
            raise
        entries = response.parsed_data
        if not isinstance(entries, list):
            return []
        return [entry.name for entry in entries if entry.type == "file"]

    async def get_permission(self, login: str) -> str:
        """What a GitHub account may do on the data repo (#248).

        GitHub's base level: ``admin``, ``write`` (maintain counts as write),
        ``read`` or ``none``. An unknown login is a 404, which means ``none``
        here. Needs only the Metadata permission, which every App has.
        """
        repos = self._gh.rest.repos
        try:
            response = await repos.async_get_collaborator_permission_level(
                self.owner, self.repo, login
            )
        except RequestFailed as exc:
            if exc.response.status_code == 404:
                return "none"
            raise
        return str(response.parsed_data.permission or "none")

    async def get_base_sha(self) -> str:
        """Commit sha of the base branch head."""
        response = await self._gh.rest.git.async_get_ref(
            self.owner, self.repo, ref=f"heads/{self.base_branch}"
        )
        return response.parsed_data.object_.sha

    async def _create_commit(
        self,
        parent_sha: str,
        files: List[NewFile],
        deletions: List[str],
        message: str,
        author_name: str,
        author_email: str,
        existing: Optional[Dict[str, str]] = None,
    ) -> str:
        """One commit on top of `parent_sha`, without moving any ref.

        The contributor is the author, the App's bot the committer. A tree
        entry with a null sha is how the Git Data API spells "delete".

        `existing` maps a repo path to the blob sha already at `parent_sha`.
        A file whose content hashes to the same sha needs no upload and no
        tree entry: it is already in `base_tree`. An edit that only touches
        one row of the CSV then sends one blob instead of the whole batch.
        """
        git = self._gh.rest.git
        at_parent = existing or {}
        changed = [
            file for file in files if at_parent.get(file.path) != blob_sha(file.content)
        ]

        limit = asyncio.Semaphore(MAX_PARALLEL_CALLS)

        async def upload(file: NewFile) -> dict:
            async with limit:
                blob = await git.async_create_blob(
                    self.owner, self.repo, content=file.content, encoding="utf-8"
                )
            return {
                "path": file.path,
                "mode": "100644",
                "type": "blob",
                "sha": blob.parsed_data.sha,
            }

        tree_entries: List[dict] = list(
            await asyncio.gather(*(upload(file) for file in changed))
        )
        for rel in deletions:
            tree_entries.append(
                {"path": rel, "mode": "100644", "type": "blob", "sha": None}
            )
        if not tree_entries:
            # Nothing to write. GitHub rejects an empty tree, and an empty
            # commit is not worth making: answer the parent, and the callers
            # leave the ref where it is.
            return parent_sha
        tree = await git.async_create_tree(
            self.owner, self.repo, base_tree=parent_sha, tree=tree_entries
        )
        commit = await git.async_create_commit(
            self.owner,
            self.repo,
            message=message,
            tree=tree.parsed_data.sha,
            parents=[parent_sha],
            author={"name": author_name, "email": author_email},
        )
        return commit.parsed_data.sha

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

        Returns the commit sha.
        """
        commit_sha = await self._create_commit(
            base_sha, files, [], message, author_name, author_email
        )
        await self._gh.rest.git.async_create_ref(
            self.owner, self.repo, ref=f"refs/heads/{branch}", sha=commit_sha
        )
        return commit_sha

    async def commit_on_branch(
        self,
        branch: str,
        head_sha: str,
        files: List[NewFile],
        deletions: List[str],
        message: str,
        author_name: str,
        author_email: str,
        existing: Optional[Dict[str, str]] = None,
    ) -> str:
        """Add one commit on top of `head_sha` on `branch`; returns its sha.

        Not forced: GitHub refuses the ref update when the branch moved since
        `head_sha` was read, which is the wanted answer. `existing` is the
        path -> blob sha map of the branch head, so unchanged files are not
        uploaded again.
        """
        commit_sha = await self._create_commit(
            head_sha,
            files,
            deletions,
            message,
            author_name,
            author_email,
            existing=existing,
        )
        if commit_sha == head_sha:  # nothing changed: leave the branch alone
            return head_sha
        await self._gh.rest.git.async_update_ref(
            self.owner,
            self.repo,
            ref=f"heads/{branch}",
            data={"sha": commit_sha, "force": False},
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

    async def update_pull_body(self, number: int, body: str) -> None:
        """Rewrite a pull request's description."""
        await self._gh.rest.pulls.async_update(self.owner, self.repo, number, body=body)

    async def delete_branch(self, branch: str) -> None:
        """Best-effort cleanup of a branch whose PR could not be opened."""
        try:
            await self._gh.rest.git.async_delete_ref(
                self.owner, self.repo, ref=f"heads/{branch}"
            )
        except Exception:
            pass
