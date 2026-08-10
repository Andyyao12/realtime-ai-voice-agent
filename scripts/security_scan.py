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
MEDIA_SUFFIXES = {".gif", ".ico", ".jpeg", ".jpg", ".mp4", ".png", ".webm"}
DATABASE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
FORBIDDEN_TRACKED_NAMES = {
    ".env",
    ".env.local",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
}
ALLOWED_EMAIL_DOMAINS = {"example.com", "example.test"}

SOURCE_MARKERS = ("e" + "talk", "kuvo" + "ai")
PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "JWT": re.compile(r"eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}"),
    "provider key": re.compile(r"\b(?:sk|sess|lkapi)-[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "cloud credential": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "credential in URL": re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]{8,}@", re.IGNORECASE),
    "absolute local path": re.compile(
        r"\b[A-Za-z]:\\(?:Users|Projects|" + "kuvo" + r"ai)\\", re.IGNORECASE
    ),
    "private address": re.compile(
        r"\b(?:10\.(?:\d{1,3}\.){2}\d{1,3}|192\.168\.(?:\d{1,3}\.)\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.(?:\d{1,3}\.)\d{1,3})\b"
    ),
    "internal domain": re.compile(
        r"\b(?:https?|wss?)://[^\s/]+\.(?:corp|internal|lan|local)(?::\d+)?\b",
        re.IGNORECASE,
    ),
}
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})\b", re.IGNORECASE)
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?m)^[ \t]*(?:OPENAI_API_KEY|ANAM_API_KEY|LIVEKIT_API_SECRET|API_SECRET|"
    r"CLIENT_SECRET|ACCESS_TOKEN|AUTH_TOKEN|PASSWORD)[ \t]*[:=][ \t]*['\"]?"
    r"([^\s#'\"]{8,})"
)
PLACEHOLDER_SECRET_PREFIXES = ("${", "devkey", "example", "replace-", "secret", "test-", "your-")


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


def iter_media_files() -> list[Path]:
    files: list[Path] = []
    for directory, child_directories, filenames in os.walk(ROOT):
        child_directories[:] = [name for name in child_directories if name not in EXCLUDED_PARTS]
        for filename in filenames:
            path = Path(directory) / filename
            if path.suffix.lower() in MEDIA_SUFFIXES:
                files.append(path)
    return files


def tracked_paths() -> list[Path]:
    if not (ROOT / ".git").exists():
        return []
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / value.decode("utf-8") for value in result.stdout.split(b"\0") if value]


def scan_text(label: str, text: str, *, scan_emails: bool = True) -> list[str]:
    findings: list[str] = []
    lowered = text.casefold()
    for marker in SOURCE_MARKERS:
        if marker in lowered:
            findings.append(f"{label}: source-project marker")
    for name, pattern in PATTERNS.items():
        if pattern.search(text):
            findings.append(f"{label}: {name}")
    for secret_match in SECRET_ASSIGNMENT_PATTERN.finditer(text):
        value = secret_match.group(1).casefold()
        if not value.startswith(PLACEHOLDER_SECRET_PREFIXES):
            findings.append(f"{label}: populated secret assignment")
    if scan_emails:
        for email_match in EMAIL_PATTERN.finditer(text):
            if email_match.group(1).casefold() not in ALLOWED_EMAIL_DOMAINS:
                findings.append(f"{label}: non-example email address")
    return findings


def printable_metadata(path: Path) -> str:
    data = path.read_bytes()
    strings = re.findall(rb"[\x20-\x7e]{8,}", data)
    return "\n".join(value.decode("ascii", errors="ignore") for value in strings)


def scan_tracked_files(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        lowered_name = path.name.casefold()
        if lowered_name in FORBIDDEN_TRACKED_NAMES:
            findings.append(f"{path.relative_to(ROOT)}: forbidden credential filename")
        if path.suffix.casefold() in DATABASE_SUFFIXES:
            findings.append(f"{path.relative_to(ROOT)}: tracked database file")
        if path.suffix.casefold() in {".key", ".pem", ".p12", ".pfx"}:
            findings.append(f"{path.relative_to(ROOT)}: tracked credential container")
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
    text_files = iter_text_files()
    media_files = iter_media_files()
    repository_files = tracked_paths()
    for path in text_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        findings.extend(
            scan_text(
                str(path.relative_to(ROOT)),
                text,
                scan_emails=path.name not in {"pnpm-lock.yaml", "uv.lock"},
            )
        )
    for path in media_files:
        findings.extend(scan_text(f"{path.relative_to(ROOT)} metadata", printable_metadata(path)))
    findings.extend(scan_tracked_files(repository_files))
    history = history_text()
    if history:
        findings.extend(scan_text("git history", history, scan_emails=False))
    if findings:
        print("Security scan failed:")
        for finding in sorted(set(findings)):
            print(f"- {finding}")
        return 1
    print(
        "Security scan passed: "
        f"{len(text_files)} text files, {len(media_files)} media files, "
        f"{len(repository_files)} tracked paths, and available Git history checked."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
