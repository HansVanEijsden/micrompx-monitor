# SNMP

MicroMPX itself has no SNMP agent, but you can expose the values through
`snmpd` with an `extend` entry. `snmpd` runs the command on demand and
publishes its exit status and output under `NET-SNMP-EXTEND-MIB`:

```
NET-SNMP-EXTEND-MIB::nsExtendOutput1Line."micrompx"
NET-SNMP-EXTEND-MIB::nsExtendOutLine."micrompx".1
```

## Setup

Add to `/etc/snmp/snmpd.conf`:

```
extend micrompx-loss /usr/local/bin/micrompx-monitor --host 127.0.0.1 --port 8080 widget 23185 --format value
extend micrompx-level /usr/local/bin/micrompx-monitor --host 127.0.0.1 --port 8080 widget 20252 --format value
extend micrompx-backup /usr/local/bin/micrompx-monitor --host 127.0.0.1 --port 8080 widget 7966 --format value
```

Restart `snmpd` and check:

```bash
snmpwalk -v2c -c public 127.0.0.1 NET-SNMP-EXTEND-MIB::nsExtendOutLine
```

Each extension shows up as a string OID whose value is the number printed by the
tool. Map them to numbers in your NMS (Zabbix, LibreNMS, PRTG, Checkmk, Cacti,
Nagios) and alert on them like any other OID.

## Practical notes

- `extend` runs the command as the user `snmpd` runs as (`Debian-snmp` on
  Debian/Ubuntu). Test with `sudo -u Debian-snmp ...` first.
- Every poll runs the command once; at a 1-minute poll interval that is three
  tiny HTTP requests to the decoder — negligible.
- The output is a *string*. If your NMS cannot parse strings, add a small
  wrapper that prints an integer, or use the Prometheus route instead.
- `pass_persist` is the alternative when you want real numeric OIDs and a
  single long-running process; it is more work to set up.
