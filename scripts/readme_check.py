from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
REQUIRED_SECTIONS = {
    "## Architecture",
    "## Demo",
    "## Run locally",
    "## Full public deployment",
    "## Environment variables",
    "## Security model",
    "## Validation",
    "## Limitations",
    "## Troubleshooting",
}
REQUIRED_COMMANDS = {
    "uv sync --dev",
    "uv run pytest",
    "corepack pnpm build",
    "docker compose --env-file .env.example config --quiet",
}
REQUIRED_STATEMENTS = {
    "Core realtime voice functionality has been validated.",
    "Optional Anam avatar integration is included.",
    "Public RTC avatar-track validation is tracked separately.",
    "Recorded prototype demo",
    "docs/AVATAR_VALIDATION.md",
}


def local_links(markdown: str) -> list[str]:
    links = re.findall(r"!?(?:\[[^]]*\])\(([^)]+)\)", markdown)
    return [
        unquote(link.split("#", 1)[0])
        for link in links
        if link and not urlparse(link).scheme and not link.startswith("#")
    ]


def main() -> int:
    markdown = README.read_text(encoding="utf-8")
    errors: list[str] = []
    for section in sorted(REQUIRED_SECTIONS):
        if section not in markdown:
            errors.append(f"missing section: {section}")
    for command in sorted(REQUIRED_COMMANDS):
        if command not in markdown:
            errors.append(f"missing validation command: {command}")
    for statement in sorted(REQUIRED_STATEMENTS):
        if statement not in markdown:
            errors.append(f"missing release statement: {statement}")
    if markdown.count("```mermaid") != 1:
        errors.append("README must contain exactly one Mermaid architecture block")
    for link in local_links(markdown):
        if not (ROOT / link).exists():
            errors.append(f"broken local link: {link}")
    if errors:
        print("README check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"README check passed: {len(local_links(markdown))} local links verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
