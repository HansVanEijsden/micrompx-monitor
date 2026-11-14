# Changelog

## 1.2.1 — 2026-11-14

- **Fixed: `--oid-base` with a leading dot produced an empty SNMP subtree.**
  snmpd writes its own `pass_persist` line as `.1.3.6.1.4.1.12345.1.1.1`, so
  copying that OID into `--oid-base` is the obvious thing to do — but the
  leading dot stayed in the table and every `get`/`getnext` answered `NONE`.
  The base is normalised now.
- **Fixed: the SNMP documentation's `pass_persist` line omitted `--oid-base`**,
  so the example never returned a value, and it did not say that the option
  belongs after the `pass-persist` command word. Both examples show it now.
- The SNMP chapter warns to *restart* `snmpd` instead of reloading it: on
  net-snmp 5.9 (Debian 12) a `SIGHUP` reload with a `pass_persist` line in the
  configuration killed the daemon with SIGSEGV.
- `make-mib.sh` accepts an optional third argument (a sub-identifier) so the
  MIB can live under an existing enterprise number, for example
  `./make-mib.sh 53021 /usr/share/snmp/mibs 2` → base OID
  `1.3.6.1.4.1.53021.2.1.1.1`. That is what you need when the PEN already
  carries another device tree, such as an encoder group under `PEN.1`.

## 1.2.0 — 2026-11-14

- **Fixed: a failed read crashed `watch` and `pass-persist`.** Both commands
  called the collector without the `--strict` option that only `values` has,
  so the first unreadable widget raised
  `AttributeError: 'Namespace' object has no attribute 'strict'` instead of
  reporting the failure. `watch` died with a traceback and the `snmpd` agent
  exited mid-walk; a decoder that drops off the network is exactly when that
  happened.
- **Fixed: `micrompx_up` said 1 for a unit that never answered.** A scrape
  against an unreachable decoder printed `micrompx_up … 1` and exited 0, so
  nothing alerted and the textfile collector overwrote good metrics with
  empty ones. A scrape that reads nothing now prints `up 0`, names the reason
  on stderr and exits 1; a partial scrape exits 0 and names the metrics it
  lost.
- **Fixed: option values were only accepted before the command.** `values
  --host 10.0.0.24` failed with "unrecognized arguments"; the connection
  options are now on every subcommand as well.
- **Fixed: port, timeout, batch size and the `discover` range were
  unvalidated.** `--port 70000` and `--timeout -1` produced tracebacks (or a
  silent all-dashes answer), `discover --from 500 --to 400` reported "0
  widgets" instead of an error, and `watch --interval 0` hammered the unit.
  All four are usage errors (exit 2) or rejected ranges now.
- **Fixed: IPv6 addresses were mangled.** `--host ::1` became
  `http://::1:8080/` and read nothing at all; literals are bracketed, and a
  `host:port` typo or a URL given as `--host` is named instead of silently
  failing.
- **Batched reads.** One request per 8 widget ids instead of one per id: a
  `values` run is two requests instead of nine, a 64-id `discover` sweep is
  eight instead of 64. Ids an answer did not contain (the firmware parser
  truncates large batches without saying so) are re-read individually, so a
  batch can never lose a metric. `--batch` 1–32.
- **Fixed: Prometheus label escaping was inconsistent.** `version` and
  `rist_source` escaped only the quote, so a backslash or a newline in a unit
  description split a sample line and broke the whole scrape. One escaper now
  covers backslash, quote, newline, CR and tab for every label value, plus
  `# HELP` escaping.
- **Fixed: a payload that was not a JSON object crashed the reader** with
  `AttributeError: 'str' object has no attribute 'get'`; it is now a named
  error.
- `--format json` gained `readable` and `total`, and an `errors` object when
  something could not be read (existing keys unchanged).
- `pass-persist` drains a `set` request (type and value lines) and answers
  `not-writable`, so a read-only MIB cannot desynchronise the protocol.
- `snmp_values` reports `status` 2 when nothing could be read, so an
  unreachable unit shows `down(2)` in the MIB instead of a stale `up(1)`. A
  partial answer stays `up(1)`; the scalars it lost read 0, as before.
- A closed pipe (`... | head`) no longer prints a traceback.
- Tests: 86 cases covering the transport, batching and its truncation
  fallback, value conversion, all three output formats, argument validation,
  exit codes and the `pass_persist` protocol, against a fake unit that speaks
  the real JSON interface over HTTP. The suite runs in CI on every push and
  pull request (Python 3.9, 3.11 and 3.13).
- Confirmed on **MicroMPX Decoder 5.0.7** (both of the author's decoders now
  run it): all nine widget ids are unchanged from 5.0.0 and 5.0.2.
- New [docs/stereotool.md](docs/stereotool.md): the encoder side of Thimeo
  Stereo Tool uses the same JSON interface. Input level (2612), output level
  (20252) and active preset (21060) are readable; the compact meter bar
  (I/AGC/Clip) is TYPE_DISPLAYTWO and stays unreadable.

## 1.1.1 — 2026-11-13

- Trigger semantics for measured loss: `max(…,10m)` for "loss detected"
  and `min(…,10m)` for "loss sustained". The decoder reports a rolling
  average over roughly three minutes, not a counter and not a snapshot, so a
  short burst is visible for minutes and a `min()` over a short window was
  too strict.
- Documentation of the measurement window and what it means for polling
  intervals.

## 1.1.0 — 2026-11-13

- **SNMP**: a `MICROMPX-MIB` (SMIv2) with ten scalars for a decoder, a
  `make-mib.sh` that fills in your private enterprise number, and a
  `pass-persist` mode so `snmpd` can serve the values as numeric OIDs.
  Tested end to end against net-snmp 5.9 with `snmpget` and `snmpwalk`.
- `pass-persist` caches a snapshot for 10 seconds (`--cache-seconds`),
  so a walk costs one round of reads.
- Documentation for SNMP, including the object table and the `extend` alternative.

## 1.0.0 — 2026-11-13

- First release.
- `values` (`table`, `json`, `prometheus`), `widget`, `discover`, `watch`
  and `metrics` commands.
- Nine metrics for a MicroMPX decoder: measured loss, MPX output level,
  backup player, inputs, UDP port, delay, version, description and RIST source.
- Zabbix agent UserParameters and a template with nine items, five triggers and
  a graph.
- Prometheus textfile collector example and an SNMP `extend` example.
- Tested with MicroMPX Decoder 5.0.0 and 5.0.2.