from __future__ import annotations

import json
import os
import socket
from datetime import UTC, datetime, timezone
from pathlib import Path

import pytest

from frost_alert.adapters.json_config_store import JsonConfigStore
from frost_alert.adapters.json_state_store import JsonStateStore
from frost_alert.adapters.system_clock import SystemClock
from frost_alert.domain.classify import Classification, ForecastHour
from frost_alert.entrypoints.check import main as check_main
from frost_alert.entrypoints.cli import main as cli_main
from frost_alert.entrypoints.setup import main as setup_main

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "TEST_TOKEN"
CHAT_ID = "12345"
PLACE = "Stockholm"
ZONE = "Europe/Stockholm"
LAT = 59.33
LON = 18.07
THRESHOLD_C = 3
GOLDEN_NOW = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
GOLDEN_HOUR = datetime(2026, 1, 16, 6, 0, tzinfo=UTC)
YESTERDAY = "2026-01-15"
TODAY = "2026-01-16"
USER_SEVEN_KEYS = {
    "place_name",
    "lat",
    "lon",
    "elevation_m",
    "timezone",
    "threshold_c",
    "scale",
}


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FakeForecast:
    def __init__(
        self,
        series: list[ForecastHour] | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._series = [] if series is None else series
        self._error = error
        self.calls: list[tuple[float, float]] = []

    def fetch(self, *, lat: float, lon: float) -> list[ForecastHour]:
        self.calls.append((lat, lon))
        if self._error is not None:
            raise self._error
        return list(self._series)


class RecordingNotifier:
    def __init__(self, error: BaseException | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self._error = error

    def send_frost_alert(
        self,
        *,
        classification: Classification,
        place_name: str,
        threshold_c: int | float,
        scale: str,
        timezone: str,
    ) -> None:
        self.calls.append(
            {
                "classification": classification,
                "place_name": place_name,
                "threshold_c": threshold_c,
                "scale": scale,
                "timezone": timezone,
            }
        )
        if self._error is not None:
            raise self._error


class FakeAckInbox:
    def __init__(
        self,
        *,
        intents: list[str] | None = None,
        new_offset: int | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._intents = [] if intents is None else intents
        self._new_offset = new_offset
        self._error = error
        self.polls: list[int] = []

    def poll(self, *, telegram_offset: int) -> tuple[list[str], int]:
        self.polls.append(telegram_offset)
        if self._error is not None:
            raise self._error
        offset = telegram_offset if self._new_offset is None else self._new_offset
        return list(self._intents), offset


class RecordingWatchdog:
    def __init__(self, error: BaseException | None = None) -> None:
        self.pings = 0
        self._error = error

    def ping(self) -> None:
        self.pings += 1
        if self._error is not None:
            raise self._error


@pytest.fixture(autouse=True)
def block_live_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unit tests must not open a network connection")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def _user_doc() -> dict[str, object]:
    return {
        "place_name": PLACE,
        "lat": LAT,
        "lon": LON,
        "elevation_m": 28,
        "timezone": ZONE,
        "threshold_c": THRESHOLD_C,
        "scale": "C",
    }


def _risk_hour() -> ForecastHour:
    return ForecastHour(t=GOLDEN_HOUR, temp_c=2)


def _warm_hour() -> ForecastHour:
    return ForecastHour(t=GOLDEN_HOUR, temp_c=8)


def _set_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", CHAT_ID)


def _clear_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)


def _write_user(tmp_path: Path) -> JsonConfigStore:
    store = JsonConfigStore(tmp_path)
    store.write(**_user_doc())
    return store


def _run_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    forecast: FakeForecast,
    notifier: RecordingNotifier,
    inbox: FakeAckInbox,
    clock: FakeClock | None = None,
    season: str = "monitoring",
    event_date: str | None = None,
    alerted_windows: list[int] | None = None,
    telegram_offset: int = 0,
    write_state: bool = False,
    set_secrets: bool = True,
    write_config: bool = True,
    watchdog: RecordingWatchdog | None = None,
) -> tuple[int, dict[str, object] | None]:
    if set_secrets:
        _set_secrets(monkeypatch)
    else:
        _clear_secrets(monkeypatch)
    config_store = JsonConfigStore(tmp_path)
    if write_config:
        config_store.write(**_user_doc())
    state_store = JsonStateStore(tmp_path)
    if write_state:
        state_store.write(
            season=season,
            event_date=event_date,
            alerted_windows=[] if alerted_windows is None else alerted_windows,
            telegram_offset=telegram_offset,
        )
    dog = RecordingWatchdog() if watchdog is None else watchdog
    code = check_main(
        ["check"],
        config_store=config_store,
        state_store=state_store,
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        clock=FakeClock(GOLDEN_NOW) if clock is None else clock,
        watchdog=dog,
    )
    path = tmp_path / "data" / "state.json"
    payload = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    return code, payload


def test_json_config_store_load_returns_seven_keys(tmp_path: Path) -> None:
    store = _write_user(tmp_path)
    payload = store.load()
    assert set(payload) == USER_SEVEN_KEYS
    assert payload == _user_doc()


def test_json_config_store_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        JsonConfigStore(tmp_path).load()


def test_system_clock_now_is_utc_aware() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timezone.utc.utcoffset(now)


def test_matrix_monitoring_send(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    forecast = FakeForecast(series=[_risk_hour()])
    notifier = RecordingNotifier()
    inbox = FakeAckInbox(intents=[], new_offset=0)
    watchdog = RecordingWatchdog()
    code, payload = _run_check(
        tmp_path,
        monkeypatch,
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        watchdog=watchdog,
    )
    assert code == 0
    assert forecast.calls == [(LAT, LON)]
    assert len(notifier.calls) == 1
    sent = notifier.calls[0]
    assert sent["place_name"] == PLACE
    assert sent["threshold_c"] == THRESHOLD_C
    assert sent["scale"] == "C"
    assert sent["timezone"] == ZONE
    assert inbox.polls == [0]
    assert payload is not None
    assert payload["season"] == "monitoring"
    assert payload["event_date"] == TODAY
    assert payload["alerted_windows"] == [24]
    assert payload["telegram_offset"] == 0
    assert (tmp_path / "data" / "state.json").is_file()
    assert watchdog.pings == 1


def test_matrix_already_marked_skips_send(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    forecast = FakeForecast(series=[_risk_hour()])
    notifier = RecordingNotifier()
    inbox = FakeAckInbox(intents=[], new_offset=4)
    code, payload = _run_check(
        tmp_path,
        monkeypatch,
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        event_date=TODAY,
        alerted_windows=[24],
        telegram_offset=4,
        write_state=True,
    )
    assert code == 0
    assert forecast.calls == [(LAT, LON)]
    assert notifier.calls == []
    assert inbox.polls == [4]
    assert payload is not None
    assert payload["event_date"] == TODAY
    assert payload["alerted_windows"] == [24]
    assert payload["telegram_offset"] == 4


def test_matrix_absent_risk_skips_send(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    forecast = FakeForecast(series=[_warm_hour()])
    notifier = RecordingNotifier()
    inbox = FakeAckInbox(intents=[], new_offset=2)
    code, payload = _run_check(
        tmp_path,
        monkeypatch,
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        event_date=TODAY,
        alerted_windows=[24],
        telegram_offset=2,
        write_state=True,
    )
    assert code == 0
    assert forecast.calls == [(LAT, LON)]
    assert notifier.calls == []
    assert inbox.polls == [2]
    assert payload is not None
    assert payload["event_date"] == TODAY
    assert payload["alerted_windows"] == [24]


def test_matrix_suspended_polls_and_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    forecast = FakeForecast(series=[_risk_hour()])
    notifier = RecordingNotifier()
    inbox = FakeAckInbox(intents=["out"], new_offset=11)
    code, payload = _run_check(
        tmp_path,
        monkeypatch,
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        season="suspended",
        event_date=TODAY,
        alerted_windows=[24, 12],
        telegram_offset=5,
        write_state=True,
    )
    assert code == 0
    assert forecast.calls == []
    assert notifier.calls == []
    assert inbox.polls == [5]
    assert payload is not None
    assert payload["season"] == "monitoring"
    assert payload["event_date"] is None
    assert payload["alerted_windows"] == []
    assert payload["telegram_offset"] == 11


def test_matrix_new_event_resets_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    forecast = FakeForecast(series=[_risk_hour()])
    notifier = RecordingNotifier()
    inbox = FakeAckInbox(intents=[], new_offset=0)
    code, payload = _run_check(
        tmp_path,
        monkeypatch,
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        event_date=YESTERDAY,
        alerted_windows=[24, 12, 6],
        write_state=True,
    )
    assert code == 0
    assert len(notifier.calls) == 1
    assert payload is not None
    assert payload["event_date"] == TODAY
    assert payload["alerted_windows"] == [24]


def test_matrix_notifier_raise_still_polls_and_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    forecast = FakeForecast(series=[_risk_hour()])
    notifier = RecordingNotifier(error=RuntimeError("send failed"))
    inbox = FakeAckInbox(intents=[], new_offset=9)
    watchdog = RecordingWatchdog()
    code, payload = _run_check(
        tmp_path,
        monkeypatch,
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        telegram_offset=8,
        write_state=True,
        watchdog=watchdog,
    )
    assert code == 0
    assert len(notifier.calls) == 1
    assert inbox.polls == [8]
    assert payload is not None
    assert payload["alerted_windows"] == []
    assert payload["event_date"] == TODAY
    assert payload["telegram_offset"] == 9
    assert watchdog.pings == 1


def test_matrix_forecast_raise_no_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    forecast = FakeForecast(error=RuntimeError("forecast failed"))
    notifier = RecordingNotifier()
    inbox = FakeAckInbox()
    watchdog = RecordingWatchdog()
    code, payload = _run_check(
        tmp_path,
        monkeypatch,
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        watchdog=watchdog,
    )
    assert code != 0
    assert notifier.calls == []
    assert inbox.polls == []
    assert payload is None
    assert not (tmp_path / "data" / "state.json").exists()
    assert watchdog.pings == 0


def test_matrix_poll_raise_no_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    forecast = FakeForecast(series=[_risk_hour()])
    notifier = RecordingNotifier()
    inbox = FakeAckInbox(error=RuntimeError("poll failed"))
    code, payload = _run_check(
        tmp_path,
        monkeypatch,
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
    )
    assert code != 0
    assert len(notifier.calls) == 1
    assert inbox.polls == [0]
    assert payload is None
    assert not (tmp_path / "data" / "state.json").exists()


def test_matrix_missing_config_no_telegram_no_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    forecast = FakeForecast(series=[_risk_hour()])
    notifier = RecordingNotifier()
    inbox = FakeAckInbox()
    code, payload = _run_check(
        tmp_path,
        monkeypatch,
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        write_config=False,
    )
    assert code != 0
    assert forecast.calls == []
    assert notifier.calls == []
    assert inbox.polls == []
    assert payload is None
    assert not (tmp_path / "data" / "state.json").exists()


def test_matrix_missing_secrets_no_telegram_no_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    forecast = FakeForecast(series=[_risk_hour()])
    notifier = RecordingNotifier()
    inbox = FakeAckInbox()
    code, payload = _run_check(
        tmp_path,
        monkeypatch,
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        set_secrets=False,
    )
    assert code != 0
    assert forecast.calls == []
    assert notifier.calls == []
    assert inbox.polls == []
    assert payload is None
    assert not (tmp_path / "data" / "state.json").exists()
    assert "TELEGRAM_BOT_TOKEN" not in os.environ
    assert "TELEGRAM_CHAT_ID" not in os.environ


def test_matrix_missing_token_no_telegram_no_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", CHAT_ID)
    JsonConfigStore(tmp_path).write(**_user_doc())
    forecast = FakeForecast(series=[_risk_hour()])
    notifier = RecordingNotifier()
    inbox = FakeAckInbox()
    code = check_main(
        ["check"],
        config_store=JsonConfigStore(tmp_path),
        state_store=JsonStateStore(tmp_path),
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        clock=FakeClock(GOLDEN_NOW),
    )
    assert code != 0
    assert forecast.calls == []
    assert notifier.calls == []
    assert inbox.polls == []
    assert not (tmp_path / "data" / "state.json").exists()


def test_matrix_missing_chat_id_no_telegram_no_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    JsonConfigStore(tmp_path).write(**_user_doc())
    forecast = FakeForecast(series=[_risk_hour()])
    notifier = RecordingNotifier()
    inbox = FakeAckInbox()
    code = check_main(
        ["check"],
        config_store=JsonConfigStore(tmp_path),
        state_store=JsonStateStore(tmp_path),
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        clock=FakeClock(GOLDEN_NOW),
    )
    assert code != 0
    assert forecast.calls == []
    assert notifier.calls == []
    assert inbox.polls == []
    assert not (tmp_path / "data" / "state.json").exists()


def test_golden_then_in_suspends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_secrets(monkeypatch)
    config_store = _write_user(tmp_path)
    state_store = JsonStateStore(tmp_path)
    forecast = FakeForecast(series=[_risk_hour()])
    clock = FakeClock(GOLDEN_NOW)
    first = check_main(
        ["check"],
        config_store=config_store,
        state_store=state_store,
        forecast=forecast,
        notifier=RecordingNotifier(),
        inbox=FakeAckInbox(intents=[]),
        clock=clock,
    )
    assert first == 0
    payload = json.loads((tmp_path / "data" / "state.json").read_text(encoding="utf-8"))
    assert payload["event_date"] == TODAY
    assert payload["alerted_windows"] == [24]
    second = check_main(
        ["check"],
        config_store=config_store,
        state_store=state_store,
        forecast=forecast,
        notifier=RecordingNotifier(),
        inbox=FakeAckInbox(intents=["in"], new_offset=10),
        clock=clock,
    )
    assert second == 0
    payload = json.loads((tmp_path / "data" / "state.json").read_text(encoding="utf-8"))
    assert payload["season"] == "suspended"
    assert payload["event_date"] == TODAY
    assert payload["alerted_windows"] == [24]
    assert payload["telegram_offset"] == 10


def test_entrypoint_passes_env_secrets_to_constructors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_secrets(monkeypatch)
    config_store = _write_user(tmp_path)
    captured: dict[str, tuple[str, str | int]] = {}

    class CapturingNotifier:
        def __init__(self, *, token: str, chat_id: str | int) -> None:
            captured["notifier"] = (token, chat_id)

        def send_frost_alert(self, **_kwargs: object) -> None:
            return None

    class CapturingInbox:
        def __init__(self, *, token: str, chat_id: str | int) -> None:
            captured["inbox"] = (token, chat_id)

        def poll(self, *, telegram_offset: int) -> tuple[list[str], int]:
            return [], telegram_offset

    monkeypatch.setattr("frost_alert.entrypoints.check.TelegramNotifier", CapturingNotifier)
    monkeypatch.setattr("frost_alert.entrypoints.check.TelegramAckInbox", CapturingInbox)
    code = check_main(
        ["check"],
        config_store=config_store,
        state_store=JsonStateStore(tmp_path),
        forecast=FakeForecast(series=[_warm_hour()]),
        clock=FakeClock(GOLDEN_NOW),
    )
    assert code == 0
    assert captured["notifier"] == (TOKEN, CHAT_ID)
    assert captured["inbox"] == (TOKEN, CHAT_ID)


def test_cli_dispatches_check(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def fake_check(argv: object = None, **_kwargs: object) -> int:
        calls.append(argv)
        return 0

    monkeypatch.setattr("frost_alert.entrypoints.cli.check_main", fake_check)
    assert cli_main(["check"]) == 0
    assert calls == [["check"]]


def test_cli_dispatches_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def fake_setup(argv: object = None, **_kwargs: object) -> int:
        calls.append(argv)
        return 0

    monkeypatch.setattr("frost_alert.entrypoints.cli.setup_main", fake_setup)
    assert cli_main(["setup"]) == 0
    assert calls == [["setup"]]


def test_cli_reads_check_from_sys_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def fake_check(argv: object = None, **_kwargs: object) -> int:
        calls.append(argv)
        return 0

    monkeypatch.setattr("frost_alert.entrypoints.cli.check_main", fake_check)
    monkeypatch.setattr("sys.argv", ["frost-alert", "check"])
    assert cli_main() == 0
    assert calls == [["check"]]


def test_cli_reads_setup_from_sys_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def fake_setup(argv: object = None, **_kwargs: object) -> int:
        calls.append(argv)
        return 0

    monkeypatch.setattr("frost_alert.entrypoints.cli.setup_main", fake_setup)
    monkeypatch.setattr("sys.argv", ["frost-alert", "setup"])
    assert cli_main() == 0
    assert calls == [["setup"]]


def test_cli_unknown_argv_prints_usage(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(*_args: object, **_kwargs: object) -> int:
        raise AssertionError("must not dispatch setup or check")

    monkeypatch.setattr("frost_alert.entrypoints.cli.check_main", boom)
    monkeypatch.setattr("frost_alert.entrypoints.cli.setup_main", boom)
    assert cli_main([]) != 0
    assert cli_main(["nope"]) != 0
    captured = capsys.readouterr()
    message = captured.err + captured.out
    assert message.count("Usage: frost-alert setup|check") >= 2


def test_check_default_stores_load_and_write_under_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _set_secrets(monkeypatch)
    JsonConfigStore().write(**_user_doc())
    forecast = FakeForecast(series=[_risk_hour()])
    notifier = RecordingNotifier()
    inbox = FakeAckInbox()
    code = check_main(
        ["check"],
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        clock=FakeClock(GOLDEN_NOW),
    )
    assert code == 0
    assert forecast.calls == [(LAT, LON)]
    path = tmp_path / "data" / "state.json"
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["event_date"] == TODAY
    assert payload["alerted_windows"] == [24]


def test_corrupt_user_json_no_telegram_no_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_secrets(monkeypatch)
    path = tmp_path / "config" / "user.json"
    path.parent.mkdir()
    path.write_text("not-json", encoding="utf-8")
    forecast = FakeForecast(series=[_risk_hour()])
    notifier = RecordingNotifier()
    inbox = FakeAckInbox()
    code = check_main(
        ["check"],
        config_store=JsonConfigStore(tmp_path),
        state_store=JsonStateStore(tmp_path),
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        clock=FakeClock(GOLDEN_NOW),
    )
    assert code != 0
    assert forecast.calls == []
    assert notifier.calls == []
    assert inbox.polls == []
    assert not (tmp_path / "data" / "state.json").exists()


def test_corrupt_state_json_no_telegram_no_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_secrets(monkeypatch)
    JsonConfigStore(tmp_path).write(**_user_doc())
    state_path = tmp_path / "data" / "state.json"
    state_path.parent.mkdir()
    original = "not-json"
    state_path.write_text(original, encoding="utf-8")
    forecast = FakeForecast(series=[_risk_hour()])
    notifier = RecordingNotifier()
    inbox = FakeAckInbox()
    watchdog = RecordingWatchdog()
    code = check_main(
        ["check"],
        config_store=JsonConfigStore(tmp_path),
        state_store=JsonStateStore(tmp_path),
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        clock=FakeClock(GOLDEN_NOW),
        watchdog=watchdog,
    )
    assert code != 0
    assert forecast.calls == []
    assert notifier.calls == []
    assert inbox.polls == []
    assert state_path.read_text(encoding="utf-8") == original
    assert watchdog.pings == 0


def test_invalid_present_state_no_write_no_ping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_secrets(monkeypatch)
    JsonConfigStore(tmp_path).write(**_user_doc())
    state_path = tmp_path / "data" / "state.json"
    state_path.parent.mkdir()
    original = json.dumps({"season": "monitoring"})
    state_path.write_text(original, encoding="utf-8")
    forecast = FakeForecast(series=[_risk_hour()])
    notifier = RecordingNotifier()
    inbox = FakeAckInbox()
    watchdog = RecordingWatchdog()
    code = check_main(
        ["check"],
        config_store=JsonConfigStore(tmp_path),
        state_store=JsonStateStore(tmp_path),
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        clock=FakeClock(GOLDEN_NOW),
        watchdog=watchdog,
    )
    assert code != 0
    assert forecast.calls == []
    assert notifier.calls == []
    assert inbox.polls == []
    assert state_path.read_text(encoding="utf-8") == original
    assert watchdog.pings == 0


def test_ping_transport_error_still_writes_and_exits_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    forecast = FakeForecast(series=[_risk_hour()])
    notifier = RecordingNotifier()
    inbox = FakeAckInbox()
    watchdog = RecordingWatchdog(error=OSError("ping failed"))
    code, payload = _run_check(
        tmp_path,
        monkeypatch,
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        watchdog=watchdog,
    )
    assert code == 0
    assert payload is not None
    assert payload["alerted_windows"] == [24]
    assert watchdog.pings == 1


def test_blank_ping_url_skips_http_still_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HEALTHCHECKS_PING_URL", "   ")

    def boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("blank ping URL must not open HTTP")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    forecast = FakeForecast(series=[_risk_hour()])
    notifier = RecordingNotifier()
    inbox = FakeAckInbox()
    _set_secrets(monkeypatch)
    code = check_main(
        ["check"],
        config_store=_write_user(tmp_path),
        state_store=JsonStateStore(tmp_path),
        forecast=forecast,
        notifier=notifier,
        inbox=inbox,
        clock=FakeClock(GOLDEN_NOW),
    )
    assert code == 0
    assert (tmp_path / "data" / "state.json").is_file()


def test_default_watchdog_pings_env_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ping_url = "https://hc-ping.com/test-uuid"
    monkeypatch.setenv("HEALTHCHECKS_PING_URL", ping_url)
    captured: dict[str, object] = {}

    class _FakeHTTPResponse:
        def __init__(self, body: bytes) -> None:
            self._body = body

        def read(self) -> bytes:
            return self._body

        def __enter__(self) -> _FakeHTTPResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    def fake_urlopen(req: object, timeout: float | None = None) -> _FakeHTTPResponse:
        captured["url"] = getattr(req, "full_url")
        captured["timeout"] = timeout
        return _FakeHTTPResponse(b"OK")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    _set_secrets(monkeypatch)
    code = check_main(
        ["check"],
        config_store=_write_user(tmp_path),
        state_store=JsonStateStore(tmp_path),
        forecast=FakeForecast(series=[_warm_hour()]),
        notifier=RecordingNotifier(),
        inbox=FakeAckInbox(),
        clock=FakeClock(GOLDEN_NOW),
    )
    assert code == 0
    assert captured["url"] == ping_url
    assert captured["timeout"] == 15


def test_setup_still_rejects_check_and_does_not_write_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    def boom(_prompt: str = "") -> str:
        raise AssertionError("must not prompt when argv is not setup")

    monkeypatch.setattr("builtins.input", boom)
    assert setup_main(["check"]) != 0
    captured = capsys.readouterr()
    assert "Usage: frost-alert setup" in captured.err + captured.out
    assert not (tmp_path / "data" / "state.json").exists()
    assert not (tmp_path / "data").exists()


def test_composer_has_no_state_store() -> None:
    source = (ROOT / "src" / "frost_alert" / "check_tick.py").read_text(encoding="utf-8")
    assert "StateStore" not in source
    assert "state.json" not in source
    assert "JsonStateStore" not in source
