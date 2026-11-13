# SNMP

MicroMPX has no SNMP agent of its own. The Linux SNMP daemon (`snmpd`) already
does authentication, access control, community handling and traps, so the
cleanest route is to let `snmpd` answer for MicroMPX and take the values from
this tool. That is what this folder does:

- **`MICROMPX-MIB.txt`** — a proper SMIv2 MIB with ten scalars for a decoder.
- **`make-mib.sh`** — writes a copy of the MIB with your enterprise number.
- **`micrompx-monitor pass-persist`** — implements the Net-SNMP
  `pass_persist` protocol, so `snmpd` serves the MIB with numeric OIDs,
  correct types and no per-request process start.

The result: any NMS (Zabbix, LibreNMS, PRTG, Checkmk, Cacti, Nagios, Observium)
can poll a MicroMPX unit like any other device, over SNMPv2c or SNMPv3.

## 1. Register an enterprise number (once)

The MIB lives under a private enterprise number (PEN). Get one for free at
<https://pen.iana.org> (it is instant), or ask the vendor to use theirs.

```bash
./make-mib.sh 12345 /usr/share/snmp/mibs
# wrote /usr/share/snmp/mibs/MICROMPX-MIB.txt
# agent-side base OID: 1.3.6.1.4.1.12345.1.1.1
```

Without arguments `make-mib.sh` leaves the placeholder `99999` in place —
fine for testing, but do not publish values under someone else's number.

## 2. Install the tool

```bash
sudo install -m 755 micrompx-monitor /usr/local/bin/micrompx-monitor
sudo install -m 644 MICROMPX-MIB.txt /usr/share/snmp/mibs/
```

## 3. Tell snmpd about it

Add one line to `/etc/snmp/snmpd.conf`, with the base OID that `make-mib.sh`
printed:

```
pass_persist 1.3.6.1.4.1.12345.1.1.1 /usr/local/bin/micrompx-monitor --host 127.0.0.1 --port 8080 pass-persist
```

Then restart the daemon:

```bash
sudo systemctl restart snmpd
```

`snmpd` starts the bridge once and keeps it running; it only re-reads the
decoder when something asks for a value. A snapshot is reused for 10 seconds
(`--cache-seconds`), so a full walk costs one round of reads and many NMS
polls in that window are free.

## 4. Test

```bash
# as the user snmpd runs as (Debian-snmp on Debian/Ubuntu)
sudo -u Debian-snmp /usr/local/bin/micrompx-monitor --port 8080 pass-persist <<< PING   # expects PONG

snmpget -v2c -c public -On localhost .1.3.6.1.4.1.12345.1.1.1.2.0
# .1.3.6.1.4.1.12345.1.1.1.2.0 = Gauge32: 359        <- 3.59 % measured loss

snmpwalk -v2c -c public -On localhost .1.3.6.1.4.1.12345.1.1.1
```

With the MIB installed you can also use names:

```bash
snmptranslate -On MICROMPX-MIB::microMPXDecMeasuredLoss
snmpwalk -v2c -c public -m +MICROMPX-MIB localhost MICROMPX-MIB::microMPXDecoder
```

## The scalars

| OID (after the base) | Object | Type | Meaning |
|---|---|---|---|
| .1.0 | microMPXDecStatus | INTEGER up(1)/down(2) | did the unit answer the last poll |
| .2.0 | microMPXDecMeasuredLoss | Gauge32 | loss in hundredths of a percent (359 = 3.59 %) |
| .3.0 | microMPXDecMpxLevel | Gauge32 | MPX level in thousandths (1000 = 1.0 = 0 dB) |
| .4.0 | microMPXDecBackupActive | TruthValue | true(1) = backup player on air |
| .5.0 | microMPXDecInputs | Gauge32 | configured inputs |
| .6.0 | microMPXDecUdpPort | Gauge32 | UDP port |
| .7.0 | microMPXDecDelayMs | Gauge32 | delay buffer in milliseconds |
| .8.0 | microMPXDecVersion | DisplayString | firmware version |
| .9.0 | microMPXDecDescription | DisplayString | unit description |
| .10.0 | microMPXDecRistSource | DisplayString | RIST source of the first input |

SNMP has no floating point, hence the integer scaling; the MIB documents the
units. If the decoder cannot be reached, `microMPXDecStatus` turns to `down(2)`
and the numeric values read 0 — so an NMS never gets a timeout for a unit that
is simply off the network, only for an `snmpd` that is gone.

## Alternative: extend (quick and dirty)

Without a MIB, `extend` also works:

```
extend micrompx-loss /usr/local/bin/micrompx-monitor --host 127.0.0.1 --port 8080 widget 23185 --format value
```

The value then appears as a *string* under
`NET-SNMP-EXTEND-MIB::nsExtendOutLine`. It starts a process per poll and gives
no numeric type, which is why `pass_persist` is the recommended route.

## Security

Everything that makes SNMP safe is `snmpd`'s job, and it is already solved
there: SNMPv3 users with authentication and privacy, view-based access
control, communities, source-address filters. Bind `snmpd` to a management
interface or localhost and do not expose it to the internet. The bridge itself
is a local process reading the MicroMPX web interface over HTTP on 127.0.0.1.

## For the vendor

Thimeo ships a small JSON-to-SNMP script in their SD-card image. This folder
is the same idea with a published MIB and a `pass_persist` bridge: the
software does not need to grow an SNMP stack (and the security that comes
with it), the operating system's daemon keeps doing that part, and the MIB
gives every NMS a stable object model. If MicroMPX ever grows its own agent,
this MIB is the contract to implement.

## Traps

Not implemented yet. Loss notifications would fit naturally as
`microMPXDecLossNotification` with the current loss as a varbind. Open an
issue if you need them.
