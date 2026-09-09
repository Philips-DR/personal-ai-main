"""Exporter — bundle all generated docs into a markdown file or zip."""

import io
import logging
import zipfile

logger = logging.getLogger(__name__)

DOC_ORDER = [
    ("README.md", "readme"),
    ("ARCHITECTURE.md", "architecture"),
    ("MODULE_DOCS.md", "module_docs"),
    ("WORKFLOWS.md", "workflow"),
    ("API_REFERENCE.md", "api_reference"),
    ("SETUP_GUIDE.md", "setup_guide"),
]


def bundle_markdown(docs: dict[str, str], repo_name: str) -> str:
    """Combine all docs into a single markdown string."""
    parts = [f"# {repo_name} — Documentation Bundle\n"]
    for filename, key in DOC_ORDER:
        content = docs.get(key, "")
        if content:
            parts.append(f"---\n\n# {filename}\n\n{content}\n\n")
    return "\n".join(parts)


def bundle_zip(docs: dict[str, str], repo_name: str) -> bytes:
    """Bundle all docs into a ZIP archive."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, key in DOC_ORDER:
            content = docs.get(key, "")
            if content:
                zf.writestr(f"{repo_name}/{filename}", content)
    return buffer.getvalue()
