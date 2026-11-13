"""Collecting the metric set: kind conversion, strict mode, error reporting."""

from __future__ import annotations

import pytest


def test_sample_values_are_converted_per_kind(micrompx_monitor, unit, address):
    host, port = address
    result = micrompx_monitor.collect(host, port)
    values = result["values"]
    assert values["loss_percent"] == pytest.approx(3.59658)
    assert isinstance(values["loss_percent"], float)
    assert values["mpx_level"] == pytest.approx(0.689731)
    assert values["backup_active"] == 0
    assert isinstance(values["backup_active"], int)
    assert values["inputs"] == 2
    assert values["udp_port"] == 8854
    assert values["delay_seconds"] == pytest.approx(6.3)
    assert values["version"] == "5.0.2"
    assert values["description"] == "1Zwolle Zender Zwolle"
    assert values["rist_source"] == "rist://192.0.2.10:8854"
    assert result["errors"] == {}
    assert micrompx_monitor.readable_count(result) == 9


def test_collect_keeps_the_raw_entries(micrompx_monitor, unit, address):
    host, port = address
    result = micrompx_monitor.collect(host, port)
    assert result["raw"]["loss_percent"]["text"] == "Measured loss|3.6 %"
    assert len(result["raw"]) == 9


def test_label_of_splits_the_gui_text(micrompx_monitor):
    assert micrompx_monitor.label_of({"text": "Measured loss|3.6 %"}) == "Measured loss"
    assert micrompx_monitor.label_of({"text": "no separator"}) == "no separator"
    assert micrompx_monitor.label_of({}) == ""


def test_a_non_numeric_value_becomes_none_with_a_reason(micrompx_monitor, unit, address):
    unit.widgets[23185]["value"] = "not a number"
    host, port = address
    result = micrompx_monitor.collect(host, port)
    assert result["values"]["loss_percent"] is None
    assert "not a number" in result["errors"]["loss_percent"]
    assert micrompx_monitor.readable_count(result) == 8


def test_strict_mode_raises_on_a_non_numeric_value(micrompx_monitor, unit, address):
    unit.widgets[20252]["value"] = "?"
    host, port = address
    with pytest.raises(micrompx_monitor.MicroMPXError, match="mpx_level"):
        micrompx_monitor.collect(host, port, strict=True)


def test_strict_mode_raises_on_an_unknown_widget(micrompx_monitor, unit, address):
    del unit.widgets[8431]
    host, port = address
    with pytest.raises(micrompx_monitor.MicroMPXError, match="inputs"):
        micrompx_monitor.collect(host, port, strict=True)


def test_one_unknown_widget_does_not_hide_the_others(micrompx_monitor, unit, address):
    del unit.widgets[8431]
    host, port = address
    result = micrompx_monitor.collect(host, port)
    assert result["values"]["inputs"] is None
    assert result["values"]["loss_percent"] == pytest.approx(3.59658)
    assert "inputs" in result["errors"]
    assert micrompx_monitor.readable_count(result) == 8


def test_unreachable_unit_reads_nothing(micrompx_monitor, unit, address):
    host, _port = address
    from conftest import closed_port

    result = micrompx_monitor.collect(host, closed_port(), timeout=2)
    assert micrompx_monitor.readable_count(result) == 0
    assert len(result["errors"]) == 9
    assert all(value is None for value in result["values"].values())


def test_empty_text_value_stays_empty_and_counts_as_read(micrompx_monitor, unit, address):
    unit.widgets[9727]["value"] = ""
    host, port = address
    result = micrompx_monitor.collect(host, port)
    assert result["values"]["rist_source"] == ""
    assert result["errors"] == {}
