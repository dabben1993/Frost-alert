from __future__ import annotations

import ast
import importlib
import re
import socket
from pathlib import Path
from typing import Protocol, get_args, get_origin

import pytest

import frost_alert
from frost_alert import adapters, domain, entrypoints, ports
from frost_alert.ports import (
    AckInbox,
    Clock,
    ConfigStore,
    ForecastSource,
    Notifier,
    StateStore,
    Watchdog,
)

ROOT = Path(__file__).resolve().parents[1]
PORT_NAMES = (
    "ForecastSource",
    "Notifier",
    "AckInbox",
    "Watchdog",
    "ConfigStore",
    "StateStore",
    "Clock",
)
PORT_TYPES = (
    ForecastSource,
    Notifier,
    AckInbox,
    Watchdog,
    ConfigStore,
    StateStore,
    Clock,
)
BANNED_DEP_RE = re.compile(
    r"\b(?:requests|httpx|flask|django|fastapi|starlette)\b",
    re.IGNORECASE,
)
FORBIDDEN_DOMAIN_PREFIXES = (
    "frost_alert.adapters",
    "urllib",
    "http.client",
    "http",
)


class FakeForecastSource:
    pass


class FakeNotifier:
    pass


class FakeAckInbox:
    pass


class FakeWatchdog:
    pass


class FakeConfigStore:
    pass


class FakeStateStore:
    pass


class FakeClock:
    pass


PORT_FAKES = {
    ForecastSource: FakeForecastSource,
    Notifier: FakeNotifier,
    AckInbox: FakeAckInbox,
    Watchdog: FakeWatchdog,
    ConfigStore: FakeConfigStore,
    StateStore: FakeStateStore,
    Clock: FakeClock,
}


@pytest.fixture(autouse=True)
def block_live_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unit tests must not open a network connection")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def test_frost_alert_is_importable() -> None:
    assert frost_alert.__name__ == "frost_alert"
    assert Path(ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.13"


def test_layout_subpackages_import() -> None:
    assert domain.__name__ == "frost_alert.domain"
    assert ports.__name__ == "frost_alert.ports"
    assert adapters.__name__ == "frost_alert.adapters"
    assert entrypoints.__name__ == "frost_alert.entrypoints"
    for name in ("domain", "ports", "adapters", "entrypoints"):
        assert importlib.import_module(f"frost_alert.{name}").__name__ == f"frost_alert.{name}"


def test_seven_ports_are_defined_protocols() -> None:
    for name, port in zip(PORT_NAMES, PORT_TYPES, strict=True):
        assert getattr(ports, name) is port
        assert issubclass(port, Protocol)
        assert get_origin(port) is None
        assert get_args(port) == ()


def _package_of(path: Path) -> str:
    rel = path.resolve().relative_to((ROOT / "src").resolve())
    return ".".join(rel.with_suffix("").parts[:-1])


def _resolve_from_module(module: str | None, level: int, package: str) -> str:
    if level == 0:
        return module or ""
    bits = package.rsplit(".", level - 1)
    if len(bits) < level:
        return module or ""
    base = bits[0]
    return f"{base}.{module}" if module else base


def _imported_modules(path: Path, source: str | None = None) -> list[str]:
    tree = ast.parse(
        path.read_text(encoding="utf-8") if source is None else source,
        filename=str(path),
    )
    package = _package_of(path)
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_from_module(node.module, node.level, package)
            if not node.names:
                if base:
                    names.append(base)
                continue
            for alias in node.names:
                if alias.name == "*" or not base:
                    names.append(base or alias.name)
                else:
                    names.append(f"{base}.{alias.name}")
    return names


def _is_forbidden_domain_import(imported: str) -> bool:
    return any(
        imported == prefix or imported.startswith(f"{prefix}.")
        for prefix in FORBIDDEN_DOMAIN_PREFIXES
    )


def test_domain_has_no_adapters_or_stdlib_http_imports() -> None:
    domain_root = ROOT / "src" / "frost_alert" / "domain"
    py_files = list(domain_root.rglob("*.py"))
    assert py_files, "domain package is missing"
    for path in py_files:
        for imported in _imported_modules(path):
            assert not _is_forbidden_domain_import(imported), (
                f"{path} imports forbidden module {imported}"
            )


def test_imported_modules_resolves_relative_adapters_and_http() -> None:
    path = ROOT / "src" / "frost_alert" / "domain" / "__init__.py"
    names = set(
        _imported_modules(
            path,
            "from .. import adapters\nfrom ..adapters import x\nimport http\nfrom http import client\n",
        )
    )
    assert "frost_alert.adapters" in names
    assert "frost_alert.adapters.x" in names
    assert "http" in names
    assert "http.client" in names
    assert all(_is_forbidden_domain_import(name) for name in names)


def test_fake_ports_cover_all_ports_without_network() -> None:
    assert set(PORT_FAKES) == set(PORT_TYPES)
    for fake_cls in PORT_FAKES.values():
        assert fake_cls() is not None


def test_banned_http_and_web_framework_deps_absent() -> None:
    for filename in ("pyproject.toml", "uv.lock"):
        text = (ROOT / filename).read_text(encoding="utf-8")
        match = BANNED_DEP_RE.search(text)
        assert match is None, f"{filename} lists banned dependency {match.group(0)!r}"
