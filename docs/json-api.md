# The MicroMPX JSON interface

Thimeo documents this interface in **Appendix 1** of the MicroMPX manual
(<https://download.thimeo.com/MicroMPX_manual.pdf>). This page summarises what
you need for monitoring, plus the widget ids found on MicroMPX Decoder 5.0.x
and the limitations that matter in practice.

## Request format

Every parameter and meter in the web GUI has a numeric **widget id**. You read
it with a GET request whose path contains a small JSON object:

```
GET http://<host>:<port>/json-1/list{"<widget-id>":{}}
```

The `-1` after `json` is the session id. Normal GUI sessions get a real
session id and only receive changes; session **-1** is stateless and always
sends the current value, which is exactly what monitoring wants.

The parser inside MicroMPX is hand-written and deliberately minimal (it must
never allocate memory). Keep the request byte-for-byte like the example above:
no extra spaces, no reformatting. URL-encoding the JSON also works:

```
GET http://<host>:<port>/json-1/list%7B%2223185%22:%7B%7D%7D
```

Read several widgets by adding more keys, but keep batches small — large
batches are silently truncated by the parser:

```
GET .../json-1/list{"23185":{},"20252":{}}
```

`micrompx-monitor` reads in batches of 8 (`--batch`) and re-reads on its own
whatever an answer did not contain, so a truncated batch costs one extra
request instead of a missing metric. The truncation is why the tool never
trusts a batch response to be complete.

## Response format

```json
{
  "23185": { "enabled": "1", "value": "3.59658", "text": "Measured loss|3.6 %" }
}
```

| field | meaning |
|---|---|
| `enabled` | whether the widget is active in the GUI (0/1) |
| `value` | raw value, always a string |
| `value_db` | for level meters: the value in dB |
| `text` | the GUI text, `label|rendered value` |
| `count`, `text` | for the error list: how often the message occurred |

Unknown ids answer `{"12345": "ERROR_UNKNOWN_ID"}`. Widgets of types that have
no scalar representation answer
`{"20251": "ERROR_UNSUPPORTED_PARAMETER_TYPE: TYPE_MPX"}`.

## JSON token

If a token is configured in the GUI (Settings → Security), append it to the
path after `json-1`, separated by a dot:

```
GET .../json-1.Ax8h329RR13l44/list{"23185":{}}
```

The traffic is not encrypted, so the token only makes sense on a trusted
network.

## Widget ids for monitoring (MicroMPX Decoder 5.0.x)

All of these were verified unchanged on **5.0.0, 5.0.2 and 5.0.7**.

| id | label in the GUI | notes |
|---|---|---|
| **23185** | Measured loss | audio loss the decoder measures, in percent |
| 20252 | (MPX level meter) | 1.0 = 0 dB, also has `value_db` |
| 7966 | Play backup file now | 1 = backup player is on air |
| 8431 | MicroMPX inputs | number of configured inputs |
| 4647 | Port | UDP port of the decoder |
| 4648 | Delay | delay buffer in seconds |
| 4649 | Backup file | path of the backup file |
| 4650 | Backup timeout | seconds before the backup player starts |
| 7967–7970 | Measure dropouts over / force backup / allow off / minimum dropout | backup-player thresholds |
| 8097–8099 | Backup file player / also after short drops / minimum dropouts | backup-player behaviour |
| 9181–9188 | RIST | RIST on/off per input |
| 9626–9633 | RIST mode | static/dynamic IPs per input |
| 9726–9741 | RIST encoder IP / RIST advanced URL | per input |
| 9834 | RIST recovery delay | |
| 21078 | Software version | text, e.g. `5.0.2` |
| 20855 | Description (for info only) | text, as set in the GUI |
| 20534 | License ID | text |
| 9134 | JSON token | empty unless configured |

### Older ids that no longer exist

The manual's examples use ids like `11086` (error list), `11159` (packet
counters), `11714`/`11715` (stream status) and `11078` (software version).
These answered `ERROR_UNKNOWN_ID` on 5.0.0 and 5.0.2. If you have an older or
newer build, use `discover` to find the equivalents:

```bash
micrompx-monitor --host 10.0.0.24 --port 8080 discover --from 11000 --to 11200
```

## What is *not* readable this way

- **Per-packet counters** (packets received / recovered / lost) and the
  **error log** are `TYPE_DISPLAYTEXT` widgets. The JSON interface refuses
  them with `ERROR_UNSUPPORTED_PARAMETER_TYPE`. They *are* visible in the GUI.
- The **MPX scope** and other graph widgets (`TYPE_MPX`) are not readable
  either.
- The GUI receives its live values over
  `ws://<host>/websocket/` with an undocumented binary protocol, so scraping
  the GUI's own data channel is not a supported option.

For "did we lose audio", the decoder's own **Measured loss** (23185) is the
value to watch: it is exactly the audio loss caused by late or missing packets.

## Where the decoder logs

On some systems the decoder writes to the systemd journal: lines like
`Recovered 64 blocks` (RIST recovering packets) and `Audio loss`. If your
unit runs under systemd, `journalctl -u <unit>` is a second, useful source —
for example to count recovery events per minute. Check where stdout goes on
your own installation: some images pipe it through a starter script and it
never reaches the journal.