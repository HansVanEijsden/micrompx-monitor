"""Command line behaviour: option validation, exit codes and the SNMP bridge."""

from __future__ import annotations

import io
import json

import pytest
from conftest import closed_port

OID_BASE = "1.3.6.1.4.1.99999.1.1.1"


def run(mm, *argv):
    """Run main() and return its exit code."""
    return mm.main(list(argv))


def test_version_is_printed(mm, capsys):
    with pytest.raises(SystemExit) as excinfo:
        mm.main(["--version"])
    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip() == "micrompx-monitor " + mm.__version__


def test_port_out_of_range_is_a_usage_error(mm):
    with pytest.raises(SystemExit) as excinfo:
        run(mm, "--port", "70000", "metrics")
    assert excinfo.value.code == 2


def test_port_zero_is_a_usage_error(mm):
    with pytest.raises(SystemExit) as excinfo:
        run(mm, "--port", "0", "metrics")
    assert excinfo.value.code == 2


def test_port_that_is_not_a_number_is_a_usage_error(mm):
    with pytest.raises(SystemExit) as excinfo:
        run(mm, "--port", "http", "metrics")
    assert excinfo.value.code == 2


def test_negative_timeout_is_a_usage_error(mm):
    with pytest.raises(SystemExit) as excinfo:
        run(mm, "--timeout", "-1", "metrics")
    assert excinfo.value.code == 2


def test_zero_timeout_is_a_usage_error(mm):
    with pytest.raises(SystemExit) as excinfo:
        run(mm, "--timeout", "0", "metrics")
    assert excinfo.value.code == 2


def test_batch_size_is_bounded(mm):
    with pytest.raises(SystemExit) as excinfo:
        run(mm, "--batch", "0", "metrics")
    assert excinfo.value.code == 2
    with pytest.raises(SystemExit) as excinfo:
        run(mm, "--batch", str(mm.MAX_BATCH_SIZE + 1), "metrics")
    assert excinfo.value.code == 2


def test_discover_rejects_an_inverted_range(mm):
    with pytest.raises(SystemExit) as excinfo:
        run(mm, "discover", "--from", "500", "--to", "400")
    assert excinfo.value.code == 2


def test_discover_rejects_a_negative_range(mm):
    with pytest.raises(SystemExit) as excinfo:
        run(mm, "discover", "--from", "-5", "--to", "10")
    assert excinfo.value.code == 2


def test_discover_rejects_an_endless_sweep(mm):
    with pytest.raises(SystemExit) as excinfo:
        run(mm, "discover", "--from", "0", "--to", str(mm.MAX_DISCOVER_RANGE + 10))
    assert excinfo.value.code == 2


def test_options_after_the_subcommand_are_accepted(mm, unit, address, capsys):
    host, port = address
    code = run(mm, "values", "--host", host, "--port", str(port), "--format", "json")
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["readable"] == 9


def test_a_value_before_the_subcommand_is_not_overridden(mm, unit, address, capsys):
    host, port = address
    code = run(mm, "--host", host, "--port", str(port), "values", "--format", "json")
    assert code == 0
    assert json.loads(capsys.readouterr().out)["readable"] == 9


def test_values_exits_one_when_nothing_could_be_read(mm, unit, address, capsys):
    host, _port = address
    code = run(mm, "--host", host, "--port", str(closed_port()), "--timeout", "2", "values")
    captured = capsys.readouterr()
    assert code == 1
    assert "cannot reach" in captured.err
    assert "loss_percent" in captured.out and "  -" in captured.out


def test_values_strict_exits_two_when_nothing_could_be_read(mm, unit, address, capsys):
    host, _port = address
    code = run(
        mm, "--host", host, "--port", str(closed_port()), "--timeout", "2",
        "values", "--strict",
    )
    captured = capsys.readouterr()
    assert code == 2
    assert "micrompx-monitor:" in captured.err


def test_values_exits_zero_and_warns_on_a_partial_answer(mm, unit, address, capsys):
    del unit.widgets[8431]
    host, port = address
    code = run(mm, "--host", host, "--port", str(port), "values")
    captured = capsys.readouterr()
    assert code == 0
    assert "could not read inputs" in captured.err


def test_prometheus_format_exits_one_when_the_unit_is_down(mm, unit, address, capsys):
    host, _port = address
    code = run(
        mm, "--host", host, "--port", str(closed_port()), "--timeout", "2",
        "values", "--format", "prometheus",
    )
    captured = capsys.readouterr()
    assert code == 1
    assert captured.out.rstrip().endswith("} 0")


def test_widget_value_is_the_raw_field(mm, unit, address, capsys):
    host, port = address
    assert run(mm, "--host", host, "--port", str(port), "widget", "23185", "--format", "value") == 0
    assert capsys.readouterr().out.strip() == "3.59658"


def test_widget_json_is_the_raw_entry(mm, unit, address, capsys):
    host, port = address
    assert run(mm, "--host", host, "--port", str(port), "widget", "23185", "--format", "json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["text"] == "Measured loss|3.6 %"


def test_widget_text_shows_the_gui_label(mm, unit, address, capsys):
    host, port = address
    assert run(mm, "--host", host, "--port", str(port), "widget", "23185") == 0
    out = capsys.readouterr().out
    assert "23185" in out and "Measured loss" in out and "3.59658" in out


def test_widget_unknown_id_exits_two(mm, unit, address, capsys):
    host, port = address
    assert run(mm, "--host", host, "--port", str(port), "widget", "11086") == 2
    assert "ERROR_UNKNOWN_ID" in capsys.readouterr().err


def test_discover_finds_known_ids_in_two_requests(mm, unit, address, capsys):
    host, port = address
    assert run(mm, "--host", host, "--port", str(port), "discover", "--from", "23180", "--to", "23190") == 0
    out = capsys.readouterr().out
    assert "23185" in out and "Measured loss" in out
    assert "1 widget with a value between 23180 and 23190 (2 requests)" in out
    assert unit.count_requests() == 2


def test_discover_reports_the_request_count(mm, unit, address, capsys):
    host, port = address
    assert run(mm, "--host", host, "--port", str(port), "discover", "--from", "0", "--to", "19") == 0
    assert "(3 requests)" in capsys.readouterr().out


def test_discover_sweep_is_not_slowed_down_by_unknown_ids(mm, unit, address, capsys):
    """A missing id is an answer: no per-id retry during a sweep."""
    host, port = address
    assert run(mm, "--host", host, "--port", str(port), "discover", "--from", "0", "--to", "63") == 0
    assert unit.count_requests() == 8
    assert "(8 requests)" in capsys.readouterr().out


def test_watch_prints_a_line_and_stops_on_interrupt(mm, unit, address, capsys, monkeypatch):
    host, port = address

    def interrupt(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(mm.time, "sleep", interrupt)
    code = run(mm, "--host", host, "--port", str(port), "watch")
    out = capsys.readouterr().out
    assert code == 0
    assert "loss=3.59658%" in out


def test_watch_reports_an_unreachable_unit_instead_of_crashing(
    mm, unit, address, capsys, monkeypatch
):
    """Regression: a failed read outside ``values`` raised AttributeError."""
    host, _port = address

    def interrupt(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(mm.time, "sleep", interrupt)
    code = run(mm, "--host", host, "--port", str(closed_port()), "--timeout", "2", "watch")
    out = capsys.readouterr().out
    assert code == 0
    assert "unreachable:" in out
    assert "cannot reach" in out


def test_watch_json_prints_values(mm, unit, address, capsys, monkeypatch):
    host, port = address
    monkeypatch.setattr(mm.time, "sleep", lambda _seconds: (_ for _ in ()).throw(KeyboardInterrupt))
    assert run(mm, "--host", host, "--port", str(port), "watch", "--format", "json") == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[0])
    assert payload["values"]["version"] == "5.0.2"


def test_watch_interval_must_be_positive(mm):
    with pytest.raises(SystemExit) as excinfo:
        run(mm, "watch", "--interval", "0")
    assert excinfo.value.code == 2


def test_metrics_lists_every_metric(mm, capsys):
    assert run(mm, "metrics") == 0
    out = capsys.readouterr().out
    for metric in mm.METRICS:
        assert metric["name"] in out
        assert str(metric["id"]) in out


def test_broken_pipe_is_not_an_error(mm, unit, address, monkeypatch):
    host, port = address
    calls = []

    def explode(*_args, **_kwargs):
        raise BrokenPipeError

    monkeypatch.setattr(mm, "print_table", explode)
    monkeypatch.setattr(mm, "discard_stdout", lambda: calls.append(True))
    assert run(mm, "--host", host, "--port", str(port), "values") == 0
    assert calls == [True]


def test_discard_stdout_never_closes_the_stream(mm, monkeypatch):
    """Closing sys.stdout would break a caller's capture; only the fd moves."""

    class Stream:
        def __init__(self):
            self.closed_by_us = False

        def fileno(self):
            raise ValueError("no fileno here")

    stream = Stream()
    monkeypatch.setattr(mm.sys, "stdout", stream)
    mm.discard_stdout()
    assert stream.closed_by_us is False


# --- SNMP pass_persist bridge -------------------------------------------------


def snmp_args(mm, host, port, cache_seconds=0.0):
    """Parse a real command line, so the SNMP tests use the shipped defaults."""
    return mm.build_parser().parse_args(
        [
            "--host", host,
            "--port", str(port),
            "--timeout", "2",
            "pass-persist",
            "--cache-seconds", str(cache_seconds),
        ]
    )


def pass_persist(mm, address_of, script, monkeypatch, capsys):
    host, port = address_of
    monkeypatch.setattr(mm.sys, "stdin", io.StringIO(script))
    code = run(mm, "--host", host, "--port", str(port), "--timeout", "2", "pass-persist")
    return code, capsys.readouterr().out.splitlines()


def test_pass_persist_answers_ping(mm, unit, address, monkeypatch, capsys):
    code, lines = pass_persist(mm, address, "PING\n", monkeypatch, capsys)
    assert code == 0
    assert lines == ["PONG"]


def test_pass_persist_answers_get_with_a_typed_value(mm, unit, address, monkeypatch, capsys):
    oid = OID_BASE + ".2.0"
    script = "PING\nget\n%s\nget\n%s\n" % (oid, OID_BASE + ".5.0")
    code, lines = pass_persist(mm, address, script, monkeypatch, capsys)
    assert code == 0
    assert lines[0] == "PONG"
    assert lines[1:4] == [oid, "gauge", "360"]  # 3.59658 % in hundredths
    assert lines[4:7] == [OID_BASE + ".5.0", "gauge", "2"]  # two inputs


def test_pass_persist_answers_getnext_in_numeric_order(mm, unit, address, monkeypatch, capsys):
    # A leading dot is what snmpd sends; the answer keeps it stripped.
    script = "getnext\n.%s\ngetnext\n%s.2.0\n" % (OID_BASE, OID_BASE)
    code, lines = pass_persist(mm, address, script, monkeypatch, capsys)
    assert code == 0
    assert lines[0:3] == [OID_BASE + ".1.0", "integer", "1"]  # status: reachable
    assert lines[3:6] == [OID_BASE + ".3.0", "gauge", "690"]  # 0.689731 * 1000


def test_pass_persist_ends_the_walk_with_none(mm, unit, address, monkeypatch, capsys):
    code, lines = pass_persist(
        mm, address, "getnext\n%s.10.0\n" % OID_BASE, monkeypatch, capsys
    )
    assert code == 0
    assert lines == ["NONE"]


def test_pass_persist_answers_none_for_an_unknown_oid(mm, unit, address, monkeypatch, capsys):
    code, lines = pass_persist(
        mm, address, "get\n1.3.6.1.4.1.99999.1.1.1.99.0\n", monkeypatch, capsys
    )
    assert code == 0
    assert lines == ["NONE"]


def test_pass_persist_drains_a_set_without_losing_sync(mm, unit, address, monkeypatch, capsys):
    """A read-only MIB still gets 'set' traffic; the protocol must stay in step."""
    script = "set\n%s.2.0\ngauge\n5\nPING\n" % OID_BASE
    code, lines = pass_persist(mm, address, script, monkeypatch, capsys)
    assert code == 0
    assert lines == ["not-writable", "PONG"]


def test_pass_persist_survives_an_unreachable_unit(mm, unit, address, monkeypatch, capsys):
    host, _port = address
    monkeypatch.setattr(mm.sys, "stdin", io.StringIO("get\n%s.1.0\nPING\n" % OID_BASE))
    code = run(mm, "--host", host, "--port", str(closed_port()), "--timeout", "2", "pass-persist")
    lines = capsys.readouterr().out.splitlines()
    assert code == 0
    assert lines[0:3] == [OID_BASE + ".1.0", "integer", "2"]  # status: unreachable
    assert lines[3] == "PONG"


def test_pass_persist_uses_a_custom_oid_base(mm, unit, address, monkeypatch, capsys):
    host, port = address
    monkeypatch.setattr(mm.sys, "stdin", io.StringIO("get\n1.3.6.1.4.1.42.1.1.1.8.0\n"))
    code = run(
        mm, "--host", host, "--port", str(port), "pass-persist", "--oid-base",
        "1.3.6.1.4.1.42.1.1.1",
    )
    lines = capsys.readouterr().out.splitlines()
    assert code == 0
    assert lines == ["1.3.6.1.4.1.42.1.1.1.8.0", "string", "5.0.2"]


def test_snmp_values_reuses_the_snapshot(mm, unit, address):
    host, port = address

    args = snmp_args(mm, host, port, cache_seconds=60)
    cache: dict = {}
    first = mm.snmp_values(args, cache)
    requests_after_first = unit.count_requests()
    second = mm.snmp_values(args, cache)
    assert first == second
    assert unit.count_requests() == requests_after_first
    assert requests_after_first == 2


def test_snmp_values_scales_the_numbers(mm, unit, address):
    host, port = address

    args = snmp_args(mm, host, port)
    values = mm.snmp_values(args, {})
    assert values["status"] == 1
    assert values["loss_percent"] == 360
    assert values["mpx_level"] == 690
    assert values["delay_seconds"] == 6300
    assert values["backup_active"] == 2  # TruthValue: 0 means false
    assert values["version"] == "5.0.2"


def test_snmp_backup_active_is_true_when_playing(mm, unit, address):
    unit.widgets[7966]["value"] = "1"
    host, port = address

    args = snmp_args(mm, host, port)
    assert mm.snmp_values(args, {})["backup_active"] == 1


def test_oid_ordering_is_numeric(mm):
    assert mm._oid_gt("1.3.6.1.4.1.9.1.1.1.10.0", "1.3.6.1.4.1.9.1.1.1.9.0") is True
    assert mm._oid_gt("1.3.6.1.4.1.9.1.1.1.2.0", "1.3.6.1.4.1.9.1.1.1.10.0") is False
