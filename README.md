# micrompx-monitor

Read meters and status from **Thimeo MicroMPX** (encoder and decoder) — packet
loss, MPX output level, backup player, version, RIST source — from a shell, a
monitoring agent, Prometheus, Zabbix or SNMP.

MicroMPX runs your FM/DAB feed reliably for years, but when a link starts
dropping packets the GUI is the only place that shows it, and only if someone
is looking. This tool turns the JSON interface of MicroMPX into values that
monitoring systems can scrape, so a loss of packets becomes an alert instead of
a listener complaint.

```
$ micrompx-monitor --host 10.0.0.24 --port 8080 values
1Zwolle Zender Zwolle (10.0.0.24:8080)

  loss_percent   3.59658
  mpx_level      0.689731
  backup_active  0
  inputs         2
  udp_port       8854
  delay_seconds  6.3
  version        5.0.2
  description    1Zwolle Zender Zwolle
  rist_source    rist://192.0.2.10:8854

  firmware 5.0.2
```

## What it gives you

| metric | widget | meaning |
|---|---|---|
| `loss_percent` | 23185 | audio loss as measured by the decoder itself, in percent |
| `mpx_level` | 20252 | MPX output level, 1.0 = 0 dB |
| `backup_active` | 7966 | 1 when the backup player is on air (no usable stream) |
| `inputs` | 8431 | number of configured MicroMPX inputs |
| `udp_port` | 4647 | UDP port the decoder listens on |
| `delay_seconds` | 4648 | configured delay buffer |
| `version` | 21078 | software version |
| `description` | 20855 | description of the unit, as set in the GUI |
| `rist_source` | 9727 | RIST source URL of the first input |

All of these are also available over SNMP through the included MIB, and as
graphs in Zabbix and Prometheus.

`loss_percent` is the important one: it is the share of incoming packets the
decoder had to do without, and it is a rolling measurement (it moves while you
watch). A RIST or UDP path that quietly drops packets shows up here long before
the audio becomes unusable. Note that every link has its own baseline — one
site idles at 0.0 %, another at 20 % all day with perfect audio — so alert on
"worse than usual", not on "not zero".

## Install

The tool is a single Python file with no dependencies outside the standard
library (Python 3.8 or newer, Linux/macOS/Windows):

```bash
sudo install -m 755 micrompx-monitor /usr/local/bin/micrompx-monitor
micrompx-monitor --version
```

If you prefer not to install anything, run it straight from the checkout:
`python3 micrompx-monitor --help`.

## Usage

```bash
# human readable table
micrompx-monitor --host 10.0.0.24 --port 8080 values

# machine readable
micrompx-monitor --host 10.0.0.24 --port 8080 values --format json
micrompx-monitor --host 10.0.0.24 --port 8080 values --format prometheus

# one raw widget, by id (any id you find in the GUI)
micrompx-monitor --host 10.0.0.24 --port 8080 widget 23185
micrompx-monitor --host 10.0.0.24 --port 8080 widget 23185 --format value

# keep an eye on it in a terminal
micrompx-monitor --host 10.0.0.24 --port 8080 watch --interval 2
```

Options that apply to every command (before or after the command word — both
`--host 10.0.0.24 values` and `values --host 10.0.0.24` work):

| option | default | meaning |
|---|---|---|
| `--host` | `127.0.0.1` | address of the unit; IPv6 as `::1` or `[::1]` |
| `--port` | `8080` | port of the web interface, 1–65535 (see below) |
| `--token` | empty | JSON token, if you enabled one in the GUI |
| `--timeout` | `5` | socket timeout in seconds, greater than 0 |
| `--batch` | `8` | widget ids per request, 1–32 (see [How it works](#how-it-works)) |

**The port differs between products and versions.** Encoders usually serve the
web interface on 8080; decoders often use **80**. If a connection is refused,
try the other one. `curl -s http://HOST/ | head -c 100` tells you quickly
whether something answers.

### Exit codes

| code | meaning |
|---|---|
| `0` | at least one value was read — a partial answer still counts as success |
| `1` | nothing could be read: the unit is unreachable or answered nothing useful |
| `2` | usage error, or a read failed under `--strict` |

A scrape that reads nothing prints `micrompx_up … 0` and exits `1`, so a
textfile collector keeps its previous file instead of writing an empty one.
Every metric that could not be read is named on stderr; `--strict` turns any
single failed metric into exit code 2.

## Integrations

### Zabbix

`integrations/zabbix` contains the agent `UserParameter`s and a ready
template with nine items, five triggers and a graph:

```bash
sudo install -m 644 integrations/zabbix/userparameter_micrompx.conf \
    /etc/zabbix/zabbix_agent2.d/micrompx.conf
sudo install -m 755 micrompx-monitor /usr/local/bin/micrompx-monitor
sudo systemctl restart zabbix-agent2
```

Import `integrations/zabbix/micrompx_template.yaml` (Data collection →
Templates → Import), link **MicroMPX decoder** to the host and set the host
macro `{$MICROMPX.PORT}` (80 or 8080). Test as the agent user first:

```bash
su -s /bin/sh zabbix -c '/usr/local/bin/micrompx-monitor --port 8080 widget 23185 --format value'
```

### Prometheus

Run the tool as a textfile collector:

```bash
micrompx-monitor --host 127.0.0.1 --port 8080 values --format prometheus \
  > /var/lib/node_exporter/textfile/micrompx_decoder.prom
```

Put that in a systemd timer or cron job every 15–30 seconds. See
`integrations/prometheus/README.md` for a complete example including a
systemd unit.

### The encoder side

Thimeo Stereo Tool serves the same JSON interface on its web port, so the tool
reads an encoder as well: input level, output level and the active preset.
That catches a crashed or silent encoder before the decoder runs out of
buffer. Widget ids and a ready-made monitoring recipe are in
[docs/stereotool.md](docs/stereotool.md).

### SNMP

The unit itself has no SNMP agent, but this repository ships a **MIB** and a
`pass_persist` bridge, so `snmpd` serves the values as real numeric OIDs
with correct types — SNMPv2c or SNMPv3, with all of `snmpd`'s access control:

```bash
./integrations/snmp/make-mib.sh <YOUR-PEN> /usr/share/snmp/mibs   # writes MICROMPX-MIB.txt
echo 'pass_persist 1.3.6.1.4.1.<YOUR-PEN>.1.1.1 /usr/local/bin/micrompx-monitor --port 8080 pass-persist' | sudo tee -a /etc/snmp/snmpd.conf
sudo systemctl restart snmpd
snmpwalk -v2c -c public localhost MICROMPX-MIB::microMPXDecoder
```

A free private enterprise number (PEN) for the MIB is available at
<https://pen.iana.org>. See `integrations/snmp/README.md` for the object
table, testing and the simpler `extend` alternative.

### Anything else

`values --format json` is a stable, documented format: use it from Telegraf,
Checkmk local checks, Nagios/Icinga plugins, Home Assistant REST sensors or
your own scripts.

## How it works

MicroMPX exposes almost everything its GUI shows through a small JSON interface
(Appendix 1 of the MicroMPX manual):

```
GET http://<host>:<port>/json-1/list{"<widget-id>":{}}
```

Every meter and setting has a numeric widget id. This tool knows the ids that
matter for monitoring a decoder, and it can probe ids, so you can find the ones
your firmware uses:

```bash
micrompx-monitor --host 10.0.0.24 --port 8080 discover --from 23180 --to 23190
  23185  Measured loss                            3.59658
  23188  ...
```

`discover` walks a range and prints every widget that answers with a label or
a value. That is how the ids in this repository were found — and how you can
find newly added ones. More background, including what is *not* reachable, is
in [docs/json-api.md](docs/json-api.md).

### Batches

The parser inside MicroMPX is hand-written and small, so every request costs
the unit real work. The tool therefore asks for several ids at once: a
`values` run is **two** requests instead of nine, and a `discover` sweep of 64
ids is eight instead of 64. Because large batches are silently truncated by
that parser, every id the answer did not contain is re-read on its own — a
shortened batch can never lose a metric. `--batch` (1–32) sets the size when a
firmware turns out to be pickier than 8.

## Alerting suggestions

Reasonable starting points, adjust to your link:

- **measured loss above the site baseline** — warning: check the RIST/UDP
  path and the encoder side. The value is a rolling average over roughly three
  minutes, so a 10-second burst is still visible for several minutes. The Zabbix
  template alerts with `max(…,10m) > {$MICROMPX.LOSS.WARN}` for "loss detected"
  and `min(…,10m) > {$MICROMPX.LOSS.HIGH}` for "loss sustained"; set the two
  macros per site (the default 1/5 works when the normal value is 0.0).
- **measured loss far above baseline** — high: error correction is running out.
- **backup player active** — high: the decoder fell back to its backup file,
  the stream is not usable.
- **MPX output level < 0.01 for 5 minutes** — high: no MPX output at all.
- **no data for 10 minutes** — high: the decoder or the agent is unreachable.

## Compatibility

Confirmed on **MicroMPX Decoder 5.0.0, 5.0.2 and 5.0.7**: the same widget ids
work on all three, so the table below is stable across the 5.0 line. The JSON
interface exists in older versions too, but ids do move between major versions:
several ids from older manuals (`11159`, `11714`, `11086`) no longer exist
in 5.0.x. Use `discover` if a value looks off, and please open an issue with your
version and the ids you found so the table in
[docs/json-api.md](docs/json-api.md) can grow.

The encoder side (Thimeo Stereo Tool) exposes the same JSON interface on its web
port; the preset name is readable (widget `21060`), but the software version
and license panels are `TYPE_DISPLAYTEXT` widgets, which the JSON interface
refuses — the same limitation as on the decoder.

## Security

- The JSON interface is **plain HTTP** without encryption. Use it on a
  management VLAN, a tunnel or localhost only — never expose it to the
  internet.
- If you enable the JSON token in the GUI, pass it with `--token`.
- This tool only reads; it never changes settings. (The API can change them —
  that is why it should not be reachable from untrusted networks.)

## Contributing

Issues and pull requests are welcome — especially the widget ids of other
MicroMPX versions, other metric suggestions, and translations of the docs.
Please do not paste license keys, tokens or customer addresses in an issue.

### Tests

The tool is one file, and the tests load it as a module (no packaging step,
no dependencies beyond `pytest`):

```bash
python3 -m venv .venv && .venv/bin/pip install pytest
.venv/bin/python -m pytest          # 86 tests, no network, no decoder needed
```

`tests/conftest.py` starts a fake MicroMPX unit on an ephemeral port. It speaks
the same JSON interface — including the silent batch truncation — so the
transport, the batching, the Prometheus exposition and the `pass_persist`
protocol are all exercised over real HTTP.

## Disclaimer

Not affiliated with Thimeo Audio Technology. MicroMPX and Stereo Tool are
products of Thimeo. The JSON interface is documented by Thimeo in Appendix 1
of the MicroMPX manual; the widget ids in this repository were discovered by
probing that interface.

## License

MIT — see [LICENSE](LICENSE).