"""Reading widgets: batching, the silent-truncation fallback, and failures."""

from __future__ import annotations

import pytest
from conftest import closed_port


def test_nine_metrics_cost_two_requests(micrompx_monitor, unit, address):
    host, port = address
    ids = [metric["id"] for metric in micrompx_monitor.METRICS]
    entries, errors = micrompx_monitor.read_widgets(host, port, "", ids, timeout=5)
    assert errors == {}
    assert sorted(entries) == sorted(ids)
    assert unit.count_requests() == 2
    assert unit.ids_requested()[0] == ids[:8]


def test_batch_of_one_is_one_request_per_metric(micrompx_monitor, unit, address):
    host, port = address
    ids = [metric["id"] for metric in micrompx_monitor.METRICS]
    entries, errors = micrompx_monitor.read_widgets(
        host, port, "", ids, timeout=5, batch_size=1
    )
    assert errors == {}
    assert len(entries) == 9
    assert unit.count_requests() == 9


def test_truncated_batch_is_completed_by_single_reads(micrompx_monitor, unit, address):
    """The firmware parser drops keys from a large batch without saying so."""
    unit.truncate_after = 3
    host, port = address
    ids = [metric["id"] for metric in micrompx_monitor.METRICS]
    entries, errors = micrompx_monitor.read_widgets(host, port, "", ids, timeout=5)
    assert sorted(entries) == sorted(ids)
    assert errors == {}
    # 1 truncated batch + 5 individual retries + 1 batch of the ninth id.
    assert unit.count_requests() == 7


def test_truncation_fallback_can_be_turned_off(micrompx_monitor, unit, address):
    """Without the fallback a truncated batch loses ids - hence the default."""
    unit.truncate_after = 3
    host, port = address
    ids = [metric["id"] for metric in micrompx_monitor.METRICS]
    entries, _errors = micrompx_monitor.read_widgets(
        host, port, "", ids, timeout=5, fallback=False
    )
    # Four of nine survive: three from the first batch, one from the second.
    assert len(entries) == 4
    assert unit.count_requests() == 2


def test_unknown_id_string_is_reported_not_crashed(micrompx_monitor, address):
    host, port = address
    entries, errors = micrompx_monitor.read_widgets(host, port, "", [11086], timeout=5)
    assert entries == {}
    assert "ERROR_UNKNOWN_ID" in errors[11086]


def test_http_error_names_the_status(micrompx_monitor, unit, address):
    unit.status = 401
    host, port = address
    entries, errors = micrompx_monitor.read_widgets(host, port, "", [23185], timeout=5)
    assert entries == {}
    assert "HTTP 401" in errors[23185]


def test_non_json_answer_is_named(micrompx_monitor, unit, address):
    unit.raw_body = "<html>login</html>"
    host, port = address
    _entries, errors = micrompx_monitor.read_widgets(host, port, "", [23185], timeout=5)
    assert "did not answer JSON" in errors[23185]


def test_json_that_is_not_an_object_is_named(micrompx_monitor, unit, address):
    """A firmware answering ``"OK"`` used to die with AttributeError."""
    unit.raw_body = '"OK"'
    host, port = address
    _entries, errors = micrompx_monitor.read_widgets(host, port, "", [23185], timeout=5)
    assert "JSON str" in errors[23185]


def test_unreachable_host_is_one_message_per_widget(micrompx_monitor, unit, address):
    host, _port = address
    entries, errors = micrompx_monitor.read_widgets(
        host, closed_port(), "", [23185, 20252], timeout=2
    )
    assert entries == {}
    assert set(errors) == {23185, 20252}
    assert "cannot reach" in errors[23185]


def test_read_widget_raises_and_returns_the_entry(micrompx_monitor, unit, address):
    host, port = address
    entry = micrompx_monitor.read_widget(host, port, "", 23185, timeout=5)
    assert entry["value"] == "3.59658"


def test_read_widget_raises_for_an_unknown_id(micrompx_monitor, unit, address):
    host, port = address
    with pytest.raises(micrompx_monitor.MicroMPXError, match="ERROR_UNKNOWN_ID"):
        micrompx_monitor.read_widget(host, port, "", 11086, timeout=5)


def test_token_is_sent_when_the_unit_expects_one(micrompx_monitor, unit, address):
    unit.token = "Ax8h329RR13l44"
    host, port = address
    entries, errors = micrompx_monitor.read_widgets(
        host, port, "Ax8h329RR13l44", [23185], timeout=5
    )
    assert errors == {} and 23185 in entries
    assert unit.requests[0]["token"] == "Ax8h329RR13l44"


def test_missing_token_is_an_http_error(micrompx_monitor, unit, address):
    unit.token = "secret"
    host, port = address
    _entries, errors = micrompx_monitor.read_widgets(host, port, "", [23185], timeout=5)
    assert "HTTP 401" in errors[23185]
