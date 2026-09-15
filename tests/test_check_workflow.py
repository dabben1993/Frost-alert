from __future__ import annotations

import re
import socket
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "check.yml"
SECRET_EXPR = re.compile(r"\$\{\{\s*secrets\.([A-Z0-9_]+)\s*\}\}")
TOKEN_LIKE = re.compile(
    r"(?:"
    r"\d{8,}:[A-Za-z0-9_-]{20,}"
    r"|ghp_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|https?://hc-ping\.com/\S+"
    r"|TELEGRAM_CHAT_ID:\s*-?\d+"
    r")"
)
WINDOW_LABEL = re.compile(
    r"(?:window(?:s)?\s*[:=]\s*(?:24|12|6)|~?(?:24|12|6)\s*h\b)",
    re.IGNORECASE,
)
REQUIRED_SECRETS = (
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "HEALTHCHECKS_PING_URL",
)


@pytest.fixture(autouse=True)
def block_live_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unit tests must not open a network connection")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _unquoted(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _noncomment_lines(text: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        stripped = raw.lstrip(" ")
        if not stripped or stripped.startswith("#"):
            continue
        lines.append((len(raw) - len(stripped), stripped))
    return lines


def _active_text(text: str) -> str:
    return "\n".join(content for _indent, content in _noncomment_lines(text))


def _key_span(
    lines: list[tuple[int, str]], key: str, lo: int = 0, hi: int | None = None
) -> tuple[int, int]:
    hi = len(lines) if hi is None else hi
    prefix = f"{key}:"
    for i in range(lo, hi):
        indent, content = lines[i]
        if content == prefix or content.startswith(f"{prefix} "):
            j = i + 1
            while j < hi and lines[j][0] > indent:
                j += 1
            return i + 1, j
    raise AssertionError(f"missing {key!r}")


def _job_check_lines(text: str) -> list[tuple[int, str]]:
    lines = _noncomment_lines(text)
    jobs_lo, jobs_hi = _key_span(lines, "jobs")
    check_lo, check_hi = _key_span(lines, "check", jobs_lo, jobs_hi)
    body = lines[check_lo:check_hi]
    assert body, "job check is empty"
    return body


def _direct_child_span(job_lines: list[tuple[int, str]], key: str) -> tuple[int, int]:
    child_indent = min(indent for indent, _ in job_lines)
    prefix = f"{key}:"
    for i, (indent, content) in enumerate(job_lines):
        if indent != child_indent:
            continue
        if content == prefix or content.startswith(f"{prefix} "):
            j = i + 1
            while j < len(job_lines) and job_lines[j][0] > indent:
                j += 1
            return i + 1, j
    raise AssertionError(f"job check missing {key!r}")


def _mapping_after(text: str, heading: str) -> dict[str, str]:
    lines = _noncomment_lines(text)
    key = heading.rstrip(":")
    start, end = _key_span(lines, key)
    mapping: dict[str, str] = {}
    for _indent, content in lines[start:end]:
        match = re.match(r"([\w-]+):\s*(.+)$", content)
        if match:
            mapping[match.group(1)] = _unquoted(match.group(2))
    return mapping


def _uses_with(text: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    current: str | None = None
    in_with = False
    with_indent = 0
    for indent, content in _noncomment_lines(text):
        uses = re.match(r"(?:-\s+)?uses:\s*(.+)$", content)
        if uses:
            current = _unquoted(uses.group(1))
            result[current] = {}
            in_with = False
            continue
        if current is not None and content == "with:":
            in_with = True
            with_indent = indent
            continue
        if in_with:
            if indent <= with_indent:
                in_with = False
            else:
                kv = re.match(r"([\w-]+):\s*(.+)$", content)
                if kv:
                    result[current][kv.group(1)] = _unquoted(kv.group(2))
    return result


def _job_env(text: str) -> dict[str, str]:
    job_lines = _job_check_lines(text)
    start, end = _direct_child_span(job_lines, "env")
    env: dict[str, str] = {}
    for _indent, content in job_lines[start:end]:
        match = re.match(r"([\w-]+):\s*(.+)$", content)
        if match:
            env[match.group(1)] = _unquoted(match.group(2))
    assert env, "job check env mapping is missing"
    return env


def _job_run_commands(text: str) -> list[str]:
    job_lines = _job_check_lines(text)
    start, end = _direct_child_span(job_lines, "steps")
    commands: list[str] = []
    for _indent, content in job_lines[start:end]:
        match = re.match(r"(?:-\s+)?run:\s*(.+)$", content)
        if match:
            commands.append(_unquoted(match.group(1)))
    return commands


def _assert_sync_before_check(commands: list[str]) -> None:
    sync_at = commands.index("uv sync --frozen")
    check_at = commands.index("uv run frost-alert check")
    assert sync_at < check_at


def test_scheduled_job_pins_runner_and_invokes_check() -> None:
    text = _workflow_text()
    active = _active_text(text)
    assert re.search(r'cron:\s*["\']0 \*/6 \* \* \*["\']', active)
    assert re.search(r"(?m)^workflow_dispatch:\s*$", active)
    concurrency = _mapping_after(text, "concurrency:")
    assert concurrency["group"] == "${{ github.workflow }}"
    assert concurrency["cancel-in-progress"] == "true"
    job_lines = _job_check_lines(text)
    assert any(content == "runs-on: ubuntu-latest" for _indent, content in job_lines)
    uses = _uses_with(text)
    assert "actions/checkout@v7" in uses
    assert uses["actions/setup-python@v7"]["python-version"] == "3.13"
    assert uses["astral-sh/setup-uv@v10.0.1"]["version"] == "0.12"
    _assert_sync_before_check(_job_run_commands(text))


def test_secrets_mapped_from_github_secrets_only() -> None:
    text = _workflow_text()
    env = _job_env(text)
    for name in REQUIRED_SECRETS:
        expr = env[name]
        match = SECRET_EXPR.fullmatch(expr)
        assert match is not None, f"{name} is not a secrets expression: {expr!r}"
        assert match.group(1) == name
    stripped = SECRET_EXPR.sub("", text)
    token = TOKEN_LIKE.search(stripped)
    assert token is None, f"secret-like value committed: {token.group(0)!r}"


def test_contents_write_commits_state_without_curl() -> None:
    text = _workflow_text()
    permissions = _mapping_after(text, "permissions:")
    assert permissions["contents"] == "write"
    active = _active_text(text)
    assert "git add data/state.json" in active
    assert re.search(
        r"""git\s+commit\s+-m\s+['\"]chore: persist frost-alert state['\"]""",
        active,
    )
    assert re.search(r"\bgit\s+push\b", active)
    assert "github-actions[bot]" in active
    assert re.search(r"\bcurl\b", active) is None
    assert "[skip ci]" not in active
    assert "git add config/user.json" not in active
    check_at = active.find("uv run frost-alert check")
    add_at = active.find("git add data/state.json")
    assert 0 <= check_at < add_at


def test_late_run_still_invokes_check_without_naming_windows() -> None:
    text = _workflow_text()
    _assert_sync_before_check(_job_run_commands(text))
    label = WINDOW_LABEL.search(_active_text(text))
    assert label is None, f"workflow names a remaining-time window: {label.group(0)!r}"
