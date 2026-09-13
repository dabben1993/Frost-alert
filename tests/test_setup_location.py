from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pytest

from frost_alert.adapters.json_config_store import JsonConfigStore
from frost_alert.entrypoints.setup import main

USER_SEVEN_KEYS = {
    "place_name",
    "lat",
    "lon",
    "elevation_m",
    "timezone",
    "threshold_c",
    "scale",
}

BERLIN_PAYLOAD = {
    "name": "Berlin",
    "latitude": 52.52437,
    "longitude": 13.41053,
    "elevation": 74,
    "timezone": "Europe/Berlin",
    "admin1": "Land Berlin",
    "country": "Germany",
}


@dataclass(frozen=True)
class FakePlace:
    place_name: str
    lat: float
    lon: float
    elevation_m: float
    timezone: str
    admin1: str | None = None
    country: str | None = None


BERLIN = FakePlace(
    place_name="Berlin",
    lat=52.52437,
    lon=13.41053,
    elevation_m=74,
    timezone="Europe/Berlin",
    admin1="Land Berlin",
    country="Germany",
)

POSTAL_PLACE = FakePlace(
    place_name="Mitte",
    lat=52.53177,
    lon=13.38721,
    elevation_m=38,
    timezone="Europe/Berlin",
    admin1="Land Berlin",
    country="Germany",
)

COORDS_PLACE = FakePlace(
    place_name="Kreuzberg",
    lat=52.49973,
    lon=13.40338,
    elevation_m=32,
    timezone="Europe/Berlin",
    admin1="Land Berlin",
    country="Germany",
)

RERUN_PLACE = FakePlace(
    place_name="Hamburg",
    lat=53.55073,
    lon=9.99302,
    elevation_m=6,
    timezone="Europe/Berlin",
    admin1="Hamburg",
    country="Germany",
)


class FakeGeocoder:
    def __init__(
        self,
        places: dict[str, FakePlace] | None = None,
        *,
        error: BaseException | None = None,
    ) -> None:
        self.places = places or {}
        self.error = error
        self.queries: list[str] = []

    def geocode(self, name: str) -> FakePlace | None:
        self.queries.append(name)
        if self.error is not None:
            raise self.error
        return self.places.get(name)


class RecordingConfigStore:
    def __init__(self) -> None:
        self.writes: list[dict[str, object]] = []

    def write(
        self,
        *,
        place_name: str,
        lat: float,
        lon: float,
        elevation_m: float,
        timezone: str,
        threshold_c: float,
        scale: str,
    ) -> None:
        self.writes.append(
            {
                "place_name": place_name,
                "lat": lat,
                "lon": lon,
                "elevation_m": elevation_m,
                "timezone": timezone,
                "threshold_c": threshold_c,
                "scale": scale,
            }
        )


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


def _seven_keys_from(place: FakePlace, *, scale: str, threshold_c: float) -> dict[str, object]:
    return {
        "place_name": place.place_name,
        "lat": place.lat,
        "lon": place.lon,
        "elevation_m": place.elevation_m,
        "timezone": place.timezone,
        "threshold_c": threshold_c,
        "scale": scale,
    }


def _run_setup(
    monkeypatch: pytest.MonkeyPatch,
    *answers: str,
    store: RecordingConfigStore | JsonConfigStore,
    geocoder: FakeGeocoder,
) -> int:
    monkeypatch.setattr("builtins.input", _feed(*answers))
    return main(["setup"], config_store=store, geocoder=geocoder)


def _assert_seven_keys(payload: dict[str, object]) -> None:
    assert set(payload) == USER_SEVEN_KEYS


def test_matrix_city_confirm_writes_seven_keys_from_geocoder(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    store = RecordingConfigStore()
    geocoder = FakeGeocoder({"Berlin": BERLIN})
    assert _run_setup(monkeypatch, "C", "3", "Berlin", "y", store=store, geocoder=geocoder) == 0
    assert geocoder.queries == ["Berlin"]
    assert store.writes == [_seven_keys_from(BERLIN, scale="C", threshold_c=3)]
    _assert_seven_keys(store.writes[0])
    shown = capsys.readouterr().out
    assert "Berlin, Land Berlin, Germany" in shown


def test_matrix_city_confirm_json_file_matches_geocoder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store = JsonConfigStore(tmp_path)
    geocoder = FakeGeocoder({"Berlin": BERLIN})
    assert _run_setup(monkeypatch, "C", "3", "Berlin", "Y", store=store, geocoder=geocoder) == 0
    payload = _read_user_json(tmp_path)
    assert payload == _seven_keys_from(BERLIN, scale="C", threshold_c=3)
    _assert_seven_keys(payload)
    assert not (tmp_path / "data" / "state.json").exists()


def test_main_default_geocoder_is_open_meteo(monkeypatch: pytest.MonkeyPatch) -> None:
    store = RecordingConfigStore()
    fake = FakeGeocoder({"Berlin": BERLIN})
    monkeypatch.setattr("frost_alert.entrypoints.setup.OpenMeteoGeocoder", lambda: fake)
    monkeypatch.setattr("builtins.input", _feed("C", "3", "Berlin", ""))
    assert main(["setup"], config_store=store) == 0
    assert fake.queries == ["Berlin"]


def test_matrix_postal_confirm_writes_seven_keys_from_that_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = RecordingConfigStore()
    geocoder = FakeGeocoder({"10115": POSTAL_PLACE})
    assert _run_setup(monkeypatch, "C", "3", "10115", "y", store=store, geocoder=geocoder) == 0
    assert geocoder.queries == ["10115"]
    assert store.writes == [_seven_keys_from(POSTAL_PLACE, scale="C", threshold_c=3)]
    assert store.writes[0]["place_name"] == "Mitte"


def test_matrix_coordinates_sent_unchanged_to_name_and_keys_from_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    typed = "52.52,13.41"
    store = RecordingConfigStore()
    geocoder = FakeGeocoder({typed: COORDS_PLACE})
    assert _run_setup(monkeypatch, "C", "3", typed, "y", store=store, geocoder=geocoder) == 0
    assert geocoder.queries == [typed]
    assert store.writes == [_seven_keys_from(COORDS_PLACE, scale="C", threshold_c=3)]
    assert store.writes[0]["lat"] == COORDS_PLACE.lat
    assert store.writes[0]["lon"] == COORDS_PLACE.lon
    assert store.writes[0]["lat"] != 52.52


def test_matrix_empty_confirm_is_yes_and_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    store = RecordingConfigStore()
    geocoder = FakeGeocoder({"Berlin": BERLIN})
    assert _run_setup(monkeypatch, "C", "3", "Berlin", "", store=store, geocoder=geocoder) == 0
    assert store.writes == [_seven_keys_from(BERLIN, scale="C", threshold_c=3)]


def test_matrix_no_match_empty_results_explains_and_does_not_write(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    store = RecordingConfigStore()
    geocoder = FakeGeocoder({})
    assert _run_setup(monkeypatch, "C", "3", "Nowhere", store=store, geocoder=geocoder) != 0
    assert geocoder.queries == ["Nowhere"]
    assert store.writes == []
    captured = capsys.readouterr()
    assert "match" in (captured.err + captured.out).lower()


def test_matrix_no_match_empty_location_does_not_call_geocoder(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    store = RecordingConfigStore()
    geocoder = FakeGeocoder({"Berlin": BERLIN})
    assert _run_setup(monkeypatch, "C", "3", "", store=store, geocoder=geocoder) != 0
    assert geocoder.queries == []
    assert store.writes == []
    captured = capsys.readouterr()
    assert "match" in (captured.err + captured.out).lower()


def test_matrix_no_match_whitespace_location_does_not_call_geocoder(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    store = RecordingConfigStore()
    geocoder = FakeGeocoder({"Berlin": BERLIN})
    assert _run_setup(monkeypatch, "C", "3", "   ", store=store, geocoder=geocoder) != 0
    assert geocoder.queries == []
    assert store.writes == []
    captured = capsys.readouterr()
    assert "match" in (captured.err + captured.out).lower()


def test_matrix_shown_place_omits_missing_admin1_and_country(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    place = FakePlace(
        place_name="Oslo",
        lat=59.91273,
        lon=10.74609,
        elevation_m=26,
        timezone="Europe/Oslo",
        admin1=None,
    )
    store = RecordingConfigStore()
    geocoder = FakeGeocoder({"Oslo": place})
    assert _run_setup(monkeypatch, "C", "3", "Oslo", "", store=store, geocoder=geocoder) == 0
    shown = capsys.readouterr().out
    assert "Oslo" in shown
    assert "None" not in shown
    assert "Oslo," not in shown


def test_matrix_no_match_leaves_existing_file_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "config" / "user.json"
    path.parent.mkdir()
    original = '{"scale": "C", "threshold_c": 3}\n'
    path.write_text(original, encoding="utf-8")
    geocoder = FakeGeocoder({})
    assert (
        _run_setup(
            monkeypatch,
            "C",
            "3",
            "Nowhere",
            store=JsonConfigStore(tmp_path),
            geocoder=geocoder,
        )
        != 0
    )
    assert path.read_text(encoding="utf-8") == original


def test_matrix_reject_does_not_write(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    store = RecordingConfigStore()
    geocoder = FakeGeocoder({"Berlin": BERLIN})
    assert _run_setup(monkeypatch, "C", "3", "Berlin", "n", store=store, geocoder=geocoder) != 0
    assert store.writes == []
    captured = capsys.readouterr()
    assert "reject" in (captured.err + captured.out).lower()


def test_matrix_reject_uppercase_n_leaves_existing_file_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "config" / "user.json"
    path.parent.mkdir()
    original = json.dumps(_seven_keys_from(BERLIN, scale="C", threshold_c=3), indent=2) + "\n"
    path.write_text(original, encoding="utf-8")
    geocoder = FakeGeocoder({"Berlin": BERLIN})
    assert (
        _run_setup(
            monkeypatch,
            "C",
            "3",
            "Berlin",
            "N",
            store=JsonConfigStore(tmp_path),
            geocoder=geocoder,
        )
        != 0
    )
    assert path.read_text(encoding="utf-8") == original
    captured = capsys.readouterr()
    assert "reject" in (captured.err + captured.out).lower()


def test_matrix_geocoder_failure_same_as_no_match(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    store = RecordingConfigStore()
    geocoder = FakeGeocoder({"Berlin": BERLIN}, error=OSError("geocoder down"))
    assert _run_setup(monkeypatch, "C", "3", "Berlin", store=store, geocoder=geocoder) != 0
    assert store.writes == []
    captured = capsys.readouterr()
    message = captured.err + captured.out
    assert "match" in message.lower()
    assert "52.52437" not in message
    assert "Europe/Berlin" not in message


def test_matrix_geocoder_failure_leaves_existing_file_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "config" / "user.json"
    path.parent.mkdir()
    original = '{"scale": "C", "threshold_c": 3}\n'
    path.write_text(original, encoding="utf-8")
    geocoder = FakeGeocoder(error=OSError("malformed"))
    assert (
        _run_setup(
            monkeypatch,
            "C",
            "3",
            "Berlin",
            store=JsonConfigStore(tmp_path),
            geocoder=geocoder,
        )
        != 0
    )
    assert path.read_text(encoding="utf-8") == original


def test_matrix_bad_scale_does_not_geocode_or_write(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    store = RecordingConfigStore()
    geocoder = FakeGeocoder({"Berlin": BERLIN})
    assert _run_setup(monkeypatch, "K", "3", store=store, geocoder=geocoder) != 0
    assert geocoder.queries == []
    assert store.writes == []
    captured = capsys.readouterr()
    message = captured.err + captured.out
    assert "C" in message and "F" in message


def test_matrix_bad_threshold_does_not_geocode_or_write(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    store = RecordingConfigStore()
    geocoder = FakeGeocoder({"Berlin": BERLIN})
    assert _run_setup(monkeypatch, "C", "warm", store=store, geocoder=geocoder) != 0
    assert geocoder.queries == []
    assert store.writes == []
    captured = capsys.readouterr()
    assert "number" in (captured.err + captured.out).lower()


def test_matrix_rerun_replaces_file_with_new_seven_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store = JsonConfigStore(tmp_path)
    store.write(**_seven_keys_from(BERLIN, scale="C", threshold_c=3))
    geocoder = FakeGeocoder({"Hamburg": RERUN_PLACE})
    assert _run_setup(monkeypatch, "F", "32", "Hamburg", "", store=store, geocoder=geocoder) == 0
    payload = _read_user_json(tmp_path)
    assert payload == _seven_keys_from(RERUN_PLACE, scale="F", threshold_c=0)
    _assert_seven_keys(payload)


def test_json_adapter_writes_exactly_seven_keys(tmp_path: Path) -> None:
    JsonConfigStore(tmp_path).write(**_seven_keys_from(BERLIN, scale="C", threshold_c=3))
    path = tmp_path / "config" / "user.json"
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert payload == _seven_keys_from(BERLIN, scale="C", threshold_c=3)
    _assert_seven_keys(payload)
    assert '"place_name": "Berlin"' in text
    assert '"lat": 52.52437' in text
    assert '"lon": 13.41053' in text
    assert '"elevation_m": 74' in text
    assert '"timezone": "Europe/Berlin"' in text
    assert '"threshold_c": 3' in text
    assert '"scale": "C"' in text


class _FakeHTTPResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeHTTPResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_open_meteo_maps_berlin_golden(monkeypatch: pytest.MonkeyPatch) -> None:
    from frost_alert.adapters.open_meteo_geocoder import OpenMeteoGeocoder

    captured: dict[str, object] = {}

    def fake_urlopen(req: urllib.request.Request, timeout: float | None = None) -> _FakeHTTPResponse:
        captured["url"] = req.full_url
        captured["user_agent"] = req.get_header("User-agent")
        captured["timeout"] = timeout
        body = json.dumps({"results": [BERLIN_PAYLOAD]}).encode("utf-8")
        return _FakeHTTPResponse(body)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    place = OpenMeteoGeocoder().geocode("Berlin")
    assert place is not None
    assert place.place_name == "Berlin"
    assert place.lat == 52.52437
    assert place.lon == 13.41053
    assert place.elevation_m == 74
    assert place.timezone == "Europe/Berlin"
    assert place.admin1 == BERLIN_PAYLOAD["admin1"]
    assert place.country == BERLIN_PAYLOAD["country"]
    assert captured["user_agent"] == "Frost-alert (https://github.com/dabben1993/Frost-alert)"
    assert captured["timeout"] == 15


def test_open_meteo_sends_name_count_without_country_or_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from frost_alert.adapters.open_meteo_geocoder import OpenMeteoGeocoder

    captured: dict[str, str] = {}

    def fake_urlopen(req: urllib.request.Request, timeout: float | None = None) -> _FakeHTTPResponse:
        captured["url"] = req.full_url
        return _FakeHTTPResponse(json.dumps({"results": [BERLIN_PAYLOAD]}).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    OpenMeteoGeocoder().geocode("52.52,13.41")
    parsed = urllib.parse.urlparse(captured["url"])
    assert parsed.scheme == "https"
    assert parsed.netloc == "geocoding-api.open-meteo.com"
    assert parsed.path == "/v1/search"
    query = urllib.parse.parse_qs(parsed.query)
    assert query["name"] == ["52.52,13.41"]
    assert query["count"] == ["1"]
    assert "countryCode" not in query
    assert "models" not in query


def test_open_meteo_http_error_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    from frost_alert.adapters.open_meteo_geocoder import OpenMeteoGeocoder

    def fake_urlopen(req: urllib.request.Request, timeout: float | None = None) -> _FakeHTTPResponse:
        raise urllib.error.HTTPError(req.full_url, 500, "server error", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert OpenMeteoGeocoder().geocode("Berlin") is None


def test_open_meteo_malformed_json_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    from frost_alert.adapters.open_meteo_geocoder import OpenMeteoGeocoder

    def fake_urlopen(req: urllib.request.Request, timeout: float | None = None) -> _FakeHTTPResponse:
        return _FakeHTTPResponse(b"not-json")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert OpenMeteoGeocoder().geocode("Berlin") is None


def test_open_meteo_empty_results_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    from frost_alert.adapters.open_meteo_geocoder import OpenMeteoGeocoder

    def fake_urlopen(req: urllib.request.Request, timeout: float | None = None) -> _FakeHTTPResponse:
        return _FakeHTTPResponse(b'{"results": []}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert OpenMeteoGeocoder().geocode("Berlin") is None


def test_open_meteo_missing_elevation_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    from frost_alert.adapters.open_meteo_geocoder import OpenMeteoGeocoder

    payload = {key: value for key, value in BERLIN_PAYLOAD.items() if key != "elevation"}

    def fake_urlopen(req: urllib.request.Request, timeout: float | None = None) -> _FakeHTTPResponse:
        return _FakeHTTPResponse(json.dumps({"results": [payload]}).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert OpenMeteoGeocoder().geocode("Berlin") is None


def test_open_meteo_missing_timezone_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    from frost_alert.adapters.open_meteo_geocoder import OpenMeteoGeocoder

    payload = {key: value for key, value in BERLIN_PAYLOAD.items() if key != "timezone"}

    def fake_urlopen(req: urllib.request.Request, timeout: float | None = None) -> _FakeHTTPResponse:
        return _FakeHTTPResponse(json.dumps({"results": [payload]}).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert OpenMeteoGeocoder().geocode("Berlin") is None
