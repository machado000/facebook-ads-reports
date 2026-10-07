"""Tests for MetaAdsReport.get_pixel_stats and get_pixel_event_hosts (no network)."""
from datetime import date, datetime
from typing import Any

import pytest

from facebook_ads_reports import (
    APIError,
    AuthenticationError,
    MetaAdsReport,
    ValidationError,
    validate_pixel_id,
)

PIXEL = "2082629071758453"


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200,
                 headers: dict[str, str] | None = None) -> None:
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.text = str(payload)

    def json(self) -> dict[str, Any]:
        return self._payload


def bucket(start_time: str, aggregation: str, *items: tuple[str, int]) -> dict[str, Any]:
    return {"start_time": start_time, "aggregation": aggregation,
            "data": [{"value": v, "count": c} for v, c in items]}


@pytest.fixture
def client() -> MetaAdsReport:
    return MetaAdsReport({"access_token": "test-token"})


def install(monkeypatch: pytest.MonkeyPatch, responses: list[FakeResponse]) -> list[dict[str, Any]]:
    """Replace requests.get with a queue of canned responses; return the call log."""
    calls: list[dict[str, Any]] = []
    queue = list(responses)

    def fake_get(url: str, headers: dict[str, str] | None = None,
                 params: dict[str, Any] | None = None, **_: Any) -> FakeResponse:
        calls.append({"url": url, "params": params, "headers": headers})
        return queue.pop(0)

    monkeypatch.setattr("facebook_ads_reports.client.requests.get", fake_get)
    return calls


def test_flattens_buckets_and_reads_local_date_and_hour(
        client: MetaAdsReport, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"data": [
        bucket("2026-10-01T00:00:00-0300", "event", ("PageView", 21), ("testride_sucesso", 3)),
        bucket("2026-10-01T01:00:00-0300", "event", ("PageView", 5)),
    ], "paging": {"cursors": {}}}
    install(monkeypatch, [FakeResponse(payload)])

    rows = client.get_pixel_stats(PIXEL, date(2026, 10, 1), date(2026, 10, 1))

    assert len(rows) == 3
    assert rows[1] == {
        "pixel_id": PIXEL, "start_time": "2026-10-01T00:00:00-0300", "date": "2026-10-01",
        "hour": 0, "aggregation": "event", "value": "testride_sucesso", "count": 3,
    }
    assert rows[2]["hour"] == 1


def test_end_date_is_inclusive_and_sent_as_exclusive_end_time(
        client: MetaAdsReport, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = install(monkeypatch, [FakeResponse({"data": []})])

    client.get_pixel_stats(PIXEL, "2026-09-07", datetime(2026, 10, 4, 15, 30))

    params = calls[0]["params"]
    assert params["start_time"] == "2026-09-07"
    assert params["end_time"] == "2026-10-05"
    assert params["aggregation"] == "event"
    assert "event" not in params
    assert calls[0]["url"].endswith(f"/{PIXEL}/stats")
    assert calls[0]["headers"] == {"Authorization": "Bearer test-token"}


def test_event_filter_is_sent_and_echoed_on_rows(
        client: MetaAdsReport, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"data": [bucket("2026-10-04T00:00:00-0300", "host", ("www.tripleducati.com.br", 4))]}
    calls = install(monkeypatch, [FakeResponse(payload)])

    rows = client.get_pixel_stats(PIXEL, "2026-10-04", "2026-10-04",
                                  aggregation="host", event="testride_sucesso")

    assert calls[0]["params"]["event"] == "testride_sucesso"
    assert rows[0]["event"] == "testride_sucesso"
    assert rows[0]["value"] == "www.tripleducati.com.br"


def test_follows_paging_next_without_resending_params_and_stops_on_empty_page(
        client: MetaAdsReport, monkeypatch: pytest.MonkeyPatch) -> None:
    next_url = "https://graph.facebook.com/v25.0/x/stats?after=abc"
    first = {"data": [bucket("2026-10-01T00:00:00-0300", "event", ("PageView", 1))],
             "paging": {"next": next_url}}
    empty = {"data": [], "paging": {"cursors": {}}}
    calls = install(monkeypatch, [FakeResponse(first), FakeResponse(empty)])

    rows = client.get_pixel_stats(PIXEL, "2026-10-01", "2026-10-01")

    assert len(rows) == 1
    assert len(calls) == 2
    assert calls[1]["url"] == next_url
    assert calls[1]["params"] is None


def test_empty_first_page_with_next_does_not_loop(
        client: MetaAdsReport, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"data": [], "paging": {"next": "https://graph.facebook.com/v25.0/x/stats?after=abc"}}
    calls = install(monkeypatch, [FakeResponse(payload)])

    assert client.get_pixel_stats(PIXEL, "2026-10-01", "2026-10-01") == []
    assert len(calls) == 1


def test_skips_malformed_buckets_and_defaults_missing_count(
        client: MetaAdsReport, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"data": [
        {"aggregation": "event", "data": [{"value": "PageView", "count": 1}]},
        {"start_time": None, "data": [{"value": "PageView", "count": 1}]},
        {"start_time": "2026-10-01T00:00:00-0300", "data": [{"value": "Lead"}]},
    ]}
    install(monkeypatch, [FakeResponse(payload)])

    rows = client.get_pixel_stats(PIXEL, "2026-10-01", "2026-10-01")

    assert [(r["value"], r["count"]) for r in rows] == [("Lead", 0)]


@pytest.mark.parametrize("pixel_id", ["", "abc", "123", "act_2082629071758453", "1" * 21])
def test_rejects_invalid_pixel_ids(client: MetaAdsReport, pixel_id: str) -> None:
    with pytest.raises(ValidationError):
        client.get_pixel_stats(pixel_id, "2026-10-01", "2026-10-01")


def test_validate_pixel_id_strips_whitespace() -> None:
    assert validate_pixel_id(f" {PIXEL} ") == PIXEL


def test_rejects_reversed_dates_and_bad_input(client: MetaAdsReport) -> None:
    with pytest.raises(ValidationError):
        client.get_pixel_stats(PIXEL, "2026-10-05", "2026-10-01")
    with pytest.raises(ValidationError):
        client.get_pixel_stats(PIXEL, "not-a-date", "2026-10-01")
    with pytest.raises(ValidationError):
        client.get_pixel_stats(PIXEL, "2026-10-01", "2026-10-01", aggregation="")


def test_permission_denied_is_an_api_error_and_is_not_retried(
        client: MetaAdsReport, monkeypatch: pytest.MonkeyPatch) -> None:
    error = {"error": {"message": "(#100) Permission Denied", "type": "OAuthException", "code": 100}}
    calls = install(monkeypatch, [FakeResponse(error, status_code=400)])

    with pytest.raises(APIError) as exc:
        client.get_pixel_stats(PIXEL, "2026-10-01", "2026-10-01")

    assert exc.value.context["error_code"] == 100
    assert len(calls) == 1


def test_invalid_token_raises_authentication_error(
        client: MetaAdsReport, monkeypatch: pytest.MonkeyPatch) -> None:
    error = {"error": {"message": "Error validating access token", "code": 190}}
    calls = install(monkeypatch, [FakeResponse(error, status_code=400)])

    with pytest.raises(AuthenticationError):
        client.get_pixel_stats(PIXEL, "2026-10-01", "2026-10-01")

    assert len(calls) == 1


def test_error_message_never_contains_the_token(
        client: MetaAdsReport, monkeypatch: pytest.MonkeyPatch) -> None:
    error = {"error": {"message": "(#100) Permission Denied", "code": 100}}
    install(monkeypatch, [FakeResponse(error, status_code=400)])

    with pytest.raises(APIError) as exc:
        client.get_pixel_stats(PIXEL, "2026-10-01", "2026-10-01")

    assert "test-token" not in str(exc.value)
    assert "test-token" not in repr(exc.value.context)


def test_event_hosts_discovers_events_then_crosses_with_host(
        client: MetaAdsReport, monkeypatch: pytest.MonkeyPatch) -> None:
    events = {"data": [bucket("2026-10-01T00:00:00-0300", "event", ("PageView", 21), ("Lead", 2))]}
    page_view_hosts = {"data": [bucket("2026-10-01T00:00:00-0300", "host", ("www.tripleducati.com.br", 21))]}
    lead_hosts = {"data": [bucket("2026-10-01T00:00:00-0300", "host",
                                  ("www.tripleducati.com.br", 1), ("www.quattroducati.com.br", 1))]}
    calls = install(monkeypatch, [FakeResponse(events), FakeResponse(lead_hosts),
                                  FakeResponse(page_view_hosts)])

    rows = client.get_pixel_event_hosts(PIXEL, "2026-10-01", "2026-10-01")

    assert [c["params"].get("event") for c in calls] == [None, "Lead", "PageView"]
    assert [c["params"]["aggregation"] for c in calls] == ["event", "host", "host"]
    assert {(r["event"], r["host"], r["count"]) for r in rows} == {
        ("Lead", "www.tripleducati.com.br", 1),
        ("Lead", "www.quattroducati.com.br", 1),
        ("PageView", "www.tripleducati.com.br", 21),
    }
    assert set(rows[0]) == {"pixel_id", "start_time", "date", "hour", "event", "host", "count"}


def test_event_hosts_with_explicit_events_skips_discovery_and_sleeps_between_calls(
        client: MetaAdsReport, monkeypatch: pytest.MonkeyPatch) -> None:
    hosts = {"data": [bucket("2026-10-01T00:00:00-0300", "host", ("www.tripleducati.com.br", 1))]}
    calls = install(monkeypatch, [FakeResponse(hosts), FakeResponse(hosts)])
    sleeps: list[float] = []
    monkeypatch.setattr("facebook_ads_reports.client.time.sleep", sleeps.append)

    client.get_pixel_event_hosts(PIXEL, "2026-10-01", "2026-10-01",
                                 events=["Lead", "testride_sucesso"], sleep_seconds=15)

    assert [c["params"]["event"] for c in calls] == ["Lead", "testride_sucesso"]
    assert sleeps == [15]
