"""GitHub repo fetcher — fetch tree and selectively download key files."""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# File patterns to prioritize when selecting key files
PRIORITY_PATTERNS = [
    "README", "readme", "package.json", "pyproject.toml", "Cargo.toml",
    "main.", "index.", "app.", "server.", "setup.py", "Makefile",
    "docker-compose", "Dockerfile", ".env.example", "config.",
]

# File patterns to skip
SKIP_PATTERNS = [
    "node_modules", ".git/", "__pycache__", ".venv", "dist/", "build/",
    ".next/", ".cache/", "coverage/", ".DS_Store", "package-lock.json",
    "yarn.lock", "pnpm-lock.yaml",
]


def _headers(token: str | None = None) -> dict:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def _parse_repo_url(url: str) -> tuple[str, str]:
    """Extract owner and repo from a GitHub URL."""
    url = url.rstrip("/")
    parts = url.split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return parts[-2], parts[-1].replace(".git", "")


async def fetch_repo_tree(repo_url: str, token: str | None = None) -> dict:
    """Fetch the full file tree of a GitHub repository."""
    owner, repo = _parse_repo_url(repo_url)
    auth_token = token or settings.github_token

    async with httpx.AsyncClient() as client:
        # Get default branch
        repo_info = await client.get(
            f"{settings.github_api_base_url}/repos/{owner}/{repo}",
            headers=_headers(auth_token),
        )
        repo_info.raise_for_status()
        default_branch = repo_info.json().get("default_branch", "main")

        # Get tree recursively
        tree_resp = await client.get(
            f"{settings.github_api_base_url}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1",
            headers=_headers(auth_token),
        )
        tree_resp.raise_for_status()

    tree_data = tree_resp.json()
    files = [
        item for item in tree_data.get("tree", [])
        if item["type"] == "blob" and not any(skip in item["path"] for skip in SKIP_PATTERNS)
    ]

    logger.info("Fetched repo tree: %d files in %s/%s", len(files), owner, repo)
    return {
        "owner": owner,
        "repo": repo,
        "branch": default_branch,
        "files": files,
    }


async def fetch_file_contents(repo_url: str, file_paths: list[str], token: str | None = None) -> dict[str, str]:
    """Fetch contents of specific files from a GitHub repo."""
    owner, repo = _parse_repo_url(repo_url)
    auth_token = token or settings.github_token
    contents = {}

    async with httpx.AsyncClient() as client:
        for path in file_paths:
            try:
                resp = await client.get(
                    f"{settings.github_api_base_url}/repos/{owner}/{repo}/contents/{path}",
                    headers=_headers(auth_token),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("encoding") == "base64":
                        import base64
                        contents[path] = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                    else:
                        contents[path] = data.get("content", "")
            except Exception as e:
                logger.warning("Failed to fetch %s: %s", path, e)

    logger.info("Fetched %d/%d files from %s/%s", len(contents), len(file_paths), owner, repo)
    return contents


def select_key_files(files: list[dict], max_files: int | None = None) -> list[str]:
    """Select the most important files from a repo tree."""
    limit = max_files if max_files is not None else settings.github_max_key_files
    priority = []
    secondary = []
    rest = []

    for f in files:
        path = f["path"]
        if any(p in path for p in PRIORITY_PATTERNS):
            priority.append(path)
        elif path.endswith((".py", ".ts", ".tsx", ".js", ".go", ".rs", ".java")):
            secondary.append(path)
        else:
            rest.append(path)

    selected = priority[:limit]
    remaining = limit - len(selected)
    if remaining > 0:
        selected.extend(secondary[:remaining])
    remaining = limit - len(selected)
    if remaining > 0:
        selected.extend(rest[:remaining])

    return selected
