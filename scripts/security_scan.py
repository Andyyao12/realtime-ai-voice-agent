from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "node_modules",
    "playwright-report",
    "test-results",
}
EXCLUDED_FILES = {Path(__file__).resolve()}
TEXT_SUFFIXES = {
    "",
    ".css",
    ".example",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

SOURCE_MARKERS = ("e" + "talk", "kuvo" + "ai")
PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "JWT": re.compile(r"eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}"),
    "provider key": re.compile(r"\b(?:sk|sess|lkapi)-[A-Za-z0-9_-]{20,}\b"),
    "cloud credential": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "absolute local path": re.compile(
        r"\b[A-Za-z]:\\(?:Users|Projects|" + "kuvo" + r"ai)\\", re.IGNORECASE
    ),
    "private address": re.compile(
        r"\b(?:10\.(?:\d{1,3}\.){2}\d{1,3}|192\.168\.(?:\d{1,3}\.)\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.(?:\d{1,3}\.)\d{1,3})\b"
    ),
}


def iter_text_files() -> list[Path]:
    files: list[Path] = []
    for directory, child_directories, filenames in os.walk(ROOT):
        child_directories[:] = [name for name in child_directories if name not in EXCLUDED_PARTS]
        for filename in filenames:
            path = Path(directory) / filename
            if path.resolve() in EXCLUDED_FILES:
                continue
            if path.suffix.lower() in TEXT_SUFFIXES or path.name in {
                "Dockerfile",
                "Makefile",
                "Caddyfile",
            }:
                files.append(path)
    return files


def scan_text(label: str, text: str) -> list[str]:
    findings: list[str] = []
    lowered = text.casefold()
    for marker in SOURCE_MARKERS:
        if marker in lowered:
            findings.append(f"{label}: source-project marker")
    for name, pattern in PATTERNS.items():
        if pattern.search(text):
            findings.append(f"{label}: {name}")
    return findings


def history_text() -> str:
    if not (ROOT / ".git").exists():
        return ""
    result = subprocess.run(
        ["git", "log", "--all", "--format=fuller", "-p", "--no-ext-diff", "--text"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout


def main() -> int:
    findings: list[str] = []
    for path in iter_text_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        findings.extend(scan_text(str(path.relative_to(ROOT)), text))
    history = history_text()
    if history:
        findings.extend(scan_text("git history", history))
    if findings:
        print("Security scan failed:")
        for finding in sorted(set(findings)):
            print(f"- {finding}")
        return 1
    print(
        f"Security scan passed: {len(iter_text_files())} files and available Git history checked."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
