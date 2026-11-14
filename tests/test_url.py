"""Request URLs and host validation."""

from __future__ import annotations

import json
import urllib.parse

import pytest


def test_widget_url_matches_the_documented_request(micrompx_monitor):
    url = micrompx_monitor.widget_url("10.0.0.24", 8080, "", 23185)
    assert url.startswith("http://10.0.0.24:8080/json-1/list")
    body = urllib.parse.unquote(url.split("/list", 1)[1])
    assert body == '{"23185":{}}'


def test_batch_url_lists_every_id_in_order(micrompx_monitor):
    url = micrompx_monitor.list_url("10.0.0.24", 80, "", [23185, 20252])
    body = urllib.parse.unquote(url.split("/list", 1)[1])
    assert body == '{"23185":{},"20252":{}}'
    # The firmware parser is byte-for-byte: the body is URL-encoded, no spaces.
    assert "%7B" in url and " " not in url
    assert json.loads(body) == {"23185": {}, "20252": {}}


def test_token_is_appended_to_the_json_session(micrompx_monitor):
    url = micrompx_monitor.widget_url("10.0.0.24", 8080, "Ax8h329RR13l44", 23185)
    assert "/json-1.Ax8h329RR13l44/list" in url


def test_empty_id_list_is_refused(micrompx_monitor):
    with pytest.raises(micrompx_monitor.MicroMPXError, match="no widget ids"):
        micrompx_monitor.list_url("10.0.0.24", 8080, "", [])


def test_ipv6_literal_is_bracketed(micrompx_monitor):
    assert micrompx_monitor.netloc("::1", 8080) == "[::1]:8080"
    url = micrompx_monitor.widget_url("::1", 8080, "", 23185)
    assert url.startswith("http://[::1]:8080/json-1/list")


def test_already_bracketed_ipv6_is_left_alone(micrompx_monitor):
    assert micrompx_monitor.netloc("[::1]", 8080) == "[::1]:8080"


def test_host_port_typo_is_named(micrompx_monitor):
    with pytest.raises(micrompx_monitor.MicroMPXError, match="pass the port with --port"):
        micrompx_monitor.host_for_url("10.0.0.24:8080")


def test_url_given_as_host_is_named(micrompx_monitor):
    with pytest.raises(micrompx_monitor.MicroMPXError, match="not a URL"):
        micrompx_monitor.host_for_url("http://10.0.0.24")


def test_path_given_as_host_is_named(micrompx_monitor):
    with pytest.raises(micrompx_monitor.MicroMPXError, match="not a path"):
        micrompx_monitor.host_for_url("10.0.0.24/json-1")


def test_empty_host_is_named(micrompx_monitor):
    with pytest.raises(micrompx_monitor.MicroMPXError, match="no host given"):
        micrompx_monitor.host_for_url("   ")


def test_plain_hostname_and_addresses_pass_through(micrompx_monitor):
    assert micrompx_monitor.host_for_url("decoder.local") == "decoder.local"
    assert micrompx_monitor.host_for_url(" 10.0.0.24 ") == "10.0.0.24"
