"""Output formats: table, JSON and the Prometheus text exposition format."""

from __future__ import annotations

import json


def test_escape_label_covers_every_special_character(micrompx_monitor):
    assert micrompx_monitor.escape_label('plain') == "plain"
    assert micrompx_monitor.escape_label('a"b') == 'a\\"b'
    assert micrompx_monitor.escape_label("a\\b") == "a\\\\b"
    assert micrompx_monitor.escape_label("a\nb") == "a\\nb"
    assert micrompx_monitor.escape_label("a\rb") == "a\\rb"
    assert micrompx_monitor.escape_label("a\tb") == "a\\tb"


def test_escape_label_keeps_backslash_and_quote_apart(micrompx_monitor):
    """Escaping the quote first would double the backslash of a newline."""
    assert micrompx_monitor.escape_label('\\"') == '\\\\\\"'


def test_escape_help_escapes_backslash_and_newline_only(micrompx_monitor):
    assert micrompx_monitor.escape_help("a\nb") == "a\\nb"
    assert micrompx_monitor.escape_help("a\\b") == "a\\\\b"
    assert micrompx_monitor.escape_help('a"b') == 'a"b'


def test_prometheus_exposition_of_a_healthy_unit(micrompx_monitor, unit, address, capsys):
    host, port = address
    result = micrompx_monitor.collect(host, port)
    micrompx_monitor.print_prometheus(result, host, port)
    out = capsys.readouterr().out
    assert 'micrompx_loss_percent{instance="127.0.0.1:%d"' % port in out
    assert "micrompx_loss_percent{" in out
    assert out.count("# TYPE micrompx_loss_percent gauge") == 1
    assert 'micrompx_info{instance="127.0.0.1:%d",description="1Zwolle Zender Zwolle",version="5.0.2",rist_source="rist://192.0.2.10:8854"} 1' % port in out
    assert "micrompx_up{" in out
    assert out.rstrip().endswith(" 1")
    # Text metrics are not gauges: they live in the info series only.
    assert "micrompx_version{" not in out


def test_prometheus_reports_up_zero_when_nothing_was_read(
    micrompx_monitor, unit, address, capsys
):
    host, _port = address
    from conftest import closed_port

    result = micrompx_monitor.collect(host, closed_port(), timeout=2)
    micrompx_monitor.print_prometheus(result, host, 8080)
    out = capsys.readouterr().out
    assert "micrompx_up{" in out
    assert out.rstrip().endswith("} 0")
    assert "micrompx_loss_percent{" not in out


def test_prometheus_reports_up_one_for_a_partial_answer(
    micrompx_monitor, unit, address, capsys
):
    del unit.widgets[8431]
    host, port = address
    result = micrompx_monitor.collect(host, port)
    micrompx_monitor.print_prometheus(result, host, port)
    out = capsys.readouterr().out
    assert "micrompx_inputs{" not in out
    assert out.rstrip().endswith("} 1")


def test_prometheus_escapes_a_description_with_a_quote_and_newline(
    micrompx_monitor, unit, address, capsys
):
    unit.widgets[20855]["value"] = 'Zender "Oost"\nFM 91.2'
    host, port = address
    result = micrompx_monitor.collect(host, port)
    micrompx_monitor.print_prometheus(result, host, port)
    out = capsys.readouterr().out
    assert 'description="Zender \\"Oost\\"\\nFM 91.2"' in out
    # One header block plus one sample line per numeric metric: a raw newline
    # inside the label would split a sample in two and break the scrape.
    for line in out.splitlines():
        assert line.startswith("#") or line.count("{") == 1


def test_prometheus_escapes_the_help_text(micrompx_monitor, unit, address, capsys):
    host, port = address
    result = micrompx_monitor.collect(host, port)
    micrompx_monitor.print_prometheus(result, host, port)
    out = capsys.readouterr().out
    assert "# HELP micrompx_loss_percent Measured audio loss" in out
    assert out.count("# HELP") == 8  # six numeric gauges + info + up


def test_table_prints_a_dash_for_a_missing_metric(micrompx_monitor, unit, address, capsys):
    del unit.widgets[8431]
    host, port = address
    result = micrompx_monitor.collect(host, port)
    micrompx_monitor.print_table(result, host, port)
    out = capsys.readouterr().out
    assert "1Zwolle Zender Zwolle (127.0.0.1:%d)" % port in out
    assert "  inputs" in out and "  -" in out
    assert "  firmware 5.0.2" in out


def test_json_payload_is_stable_and_lists_errors(micrompx_monitor, unit, address, capsys):
    del unit.widgets[8431]
    host, port = address
    result = micrompx_monitor.collect(host, port)
    micrompx_monitor.print_json(result, host, port)
    payload = json.loads(capsys.readouterr().out)
    assert payload["host"] == host and payload["port"] == port
    assert payload["readable"] == 8 and payload["total"] == 9
    assert "inputs" in payload["errors"]
    assert isinstance(payload["timestamp"], int)


def test_json_payload_has_no_errors_key_when_everything_was_read(
    micrompx_monitor, unit, address, capsys
):
    host, port = address
    result = micrompx_monitor.collect(host, port)
    micrompx_monitor.print_json(result, host, port)
    payload = json.loads(capsys.readouterr().out)
    assert "errors" not in payload
    assert set(payload["values"]) == {
        metric["name"] for metric in micrompx_monitor.METRICS
    }
