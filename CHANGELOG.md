# Changelog

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