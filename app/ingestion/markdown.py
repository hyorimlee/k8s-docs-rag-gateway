from __future__ import annotations

from pathlib import Path


def read_markdown(path: Path, *, strip_frontmatter: bool = True) -> str:
    content = path.read_text(encoding="utf-8")
    if strip_frontmatter:
        return strip_yaml_frontmatter(content)
    return content


def strip_yaml_frontmatter(content: str) -> str:
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return content

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "".join(lines[index + 1 :]).lstrip("\n")

    return content
