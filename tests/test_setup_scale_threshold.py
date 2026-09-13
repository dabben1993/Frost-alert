from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from frost_alert.adapters.json_config_store import JsonConfigStore
from frost_alert.domain.scale_threshold import InvalidSetupInput, resolve_scale_and_threshold
from frost_alert.entrypoints.setup import main

ROOT = Path(__file__).resolve().parents[1]


class RecordingConfigStore:
    def __init__(self) -> None:
        self.writes: list[tuple[str, float]] = []

    def write_scale_and_threshold(self, scale: str, threshold_c: float) -> None:
        self.writes.append((scale, threshold_c))


@pytest.fixture(autouse=True)
def block_live_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unit tests must not open a network connection")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def _feed(*answers: str):
    remaining = iter(answers)

    def fake_input(_prompt: str = "") -> str:
        return next(remaining)

    return fake_input


def _read_user_json(root: Path) -> dict[str, object]:
    return json.loads((root / "config" / "user.json").read_text(encoding="utf-8"))


def test_matrix_celsius_defaults_empty_scale_and_threshold() -> None:
    result = resolve_scale_and_threshold("", "")
    assert result.scale == "C"
    assert result.threshold_c == 3


def test_matrix_celsius_defaults_cli_writes_via_fake_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = RecordingConfigStore()
    monkeypatch.setattr("builtins.input", _feed("", ""))
    assert main(["setup"], config_store=store) == 0
    assert store.writes == [("C", 3)]


def test_matrix_fahrenheit_32_converts_to_threshold_c_0() -> None:
    result = resolve_scale_and_threshold("F", "32")
    assert result.scale == "F"
    assert result.threshold_c == 0


def test_matrix_fahrenheit_32_cli_writes_converted_celsius(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = RecordingConfigStore()
    monkeypatch.setattr("builtins.input", _feed("F", "32"))
    assert main(["setup"], config_store=store) == 0
    assert store.writes == [("F", 0)]


def test_matrix_rerun_overwrites_scale_and_threshold_in_json_file(tmp_path: Path) -> None:
    store = JsonConfigStore(tmp_path)
    store.write_scale_and_threshold("C", 3)
    store.write_scale_and_threshold("F", 0)
    assert _read_user_json(tmp_path) == {"scale": "F", "threshold_c": 0}


def test_matrix_rerun_cli_updates_existing_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store = JsonConfigStore(tmp_path)
    store.write_scale_and_threshold("C", 3)
    monkeypatch.setattr("builtins.input", _feed("F", "32"))
    assert main(["setup"], config_store=store) == 0
    assert _read_user_json(tmp_path) == {"scale": "F", "threshold_c": 0}


def test_matrix_bad_scale_does_not_write(monkeypatch: pytest.MonkeyPatch) -> None:
    store = RecordingConfigStore()
    monkeypatch.setattr("builtins.input", _feed("K", "3"))
    assert main(["setup"], config_store=store) != 0
    assert store.writes == []


def test_matrix_bad_scale_leaves_existing_file_untouched(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "config" / "user.json"
    path.parent.mkdir()
    original = '{"scale": "C", "threshold_c": 3}\n'
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr("builtins.input", _feed("K", "3"))
    assert main(["setup"], config_store=JsonConfigStore(tmp_path)) != 0
    assert path.read_text(encoding="utf-8") == original
    captured = capsys.readouterr()
    message = captured.err + captured.out
    assert "C" in message and "F" in message


def test_matrix_non_numeric_threshold_does_not_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = RecordingConfigStore()
    monkeypatch.setattr("builtins.input", _feed("C", "warm"))
    assert main(["setup"], config_store=store) != 0
    assert store.writes == []


def test_matrix_non_numeric_threshold_leaves_existing_file_untouched(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "config" / "user.json"
    path.parent.mkdir()
    original = '{"scale": "C", "threshold_c": 3}\n'
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr("builtins.input", _feed("C", "warm"))
    assert main(["setup"], config_store=JsonConfigStore(tmp_path)) != 0
    assert path.read_text(encoding="utf-8") == original
    captured = capsys.readouterr()
    assert "number" in (captured.err + captured.out).lower()


def test_matrix_fahrenheit_empty_threshold_does_not_write(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    store = RecordingConfigStore()
    monkeypatch.setattr("builtins.input", _feed("F", ""))
    assert main(["setup"], config_store=store) != 0
    assert store.writes == []
    captured = capsys.readouterr()
    assert "number" in (captured.err + captured.out).lower()


def test_fahrenheit_37_4_converts_to_threshold_c_3() -> None:
    result = resolve_scale_and_threshold("F", "37.4")
    assert result.scale == "F"
    assert result.threshold_c == 3


def test_scale_is_stored_uppercase_and_case_insensitive() -> None:
    assert resolve_scale_and_threshold("c", "4").scale == "C"
    assert resolve_scale_and_threshold("f", "32").scale == "F"


def test_json_adapter_writes_only_scale_and_threshold_under_root(tmp_path: Path) -> None:
    JsonConfigStore(tmp_path).write_scale_and_threshold("C", 3)
    path = tmp_path / "config" / "user.json"
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert payload == {"scale": "C", "threshold_c": 3}
    assert set(payload) == {"scale", "threshold_c"}
    assert '"scale": "C"' in text
    assert '"threshold_c": 3' in text


def test_json_adapter_creates_config_directory(tmp_path: Path) -> None:
    assert not (tmp_path / "config").exists()
    JsonConfigStore(tmp_path).write_scale_and_threshold("C", 3)
    assert (tmp_path / "config" / "user.json").is_file()


def test_usage_when_argv_is_not_setup(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    store = RecordingConfigStore()

    def boom(_prompt: str = "") -> str:
        raise AssertionError("must not prompt when argv is not setup")

    monkeypatch.setattr("builtins.input", boom)
    assert main([], config_store=store) != 0
    assert main(["check"], config_store=store) != 0
    assert main(["setup", "--scale", "C"], config_store=store) != 0
    assert store.writes == []
    captured = capsys.readouterr()
    assert "Usage: frost-alert setup" in captured.err + captured.out


def test_main_reads_setup_from_sys_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    store = RecordingConfigStore()
    monkeypatch.setattr("sys.argv", ["frost-alert", "setup"])
    monkeypatch.setattr("builtins.input", _feed("", ""))
    assert main(config_store=store) == 0
    assert store.writes == [("C", 3)]


def test_main_default_store_writes_user_json_under_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", _feed("", ""))
    assert main(["setup"]) == 0
    assert _read_user_json(tmp_path) == {"scale": "C", "threshold_c": 3}


def test_cli_does_not_apply_fahrenheit_conversion_formula() -> None:
    source = (ROOT / "src" / "frost_alert" / "entrypoints" / "setup.py").read_text(
        encoding="utf-8"
    )
    assert "* 5 / 9" not in source
    assert "*5/9" not in source
    assert "- 32" not in source
    assert "-32" not in source
