# Stereo Tool (encoder side)

Thimeo Stereo Tool serves the **same JSON interface** as the MicroMPX decoder,
on its web port (8080 by default):

```
http://<encoder>:8080/json-1/list{"<widget-id>":{}}
```

So this tool works on an encoder too — for example:

```bash
micrompx-monitor --host 10.0.0.10 --port 8080 widget 2612 --format value   # input level
micrompx-monitor --host 10.0.0.10 --port 8080 widget 21060 --format value  # active preset
```

Monitoring the encoder is worth it: the decoder only notices a dead encoder
when the stream is already gone (and its backup player needs up to a minute),
while the encoder itself shows the silence immediately.

## Widget ids for monitoring (Stereo Tool 11.x, verified on 12 Nov 2026)

| Id | Meaning | Type | Readable |
|---|---|---|---|
| 2612 | Input level (`value`, `value_db`) | wave | yes |
| 20252 | Output / MPX level (`value`, `value_db`) | wave | yes |
| 20631 | MPX meter (`main`) | processing | yes |
| 23242 | Speech detection (`main`, `2nd`) | processing | yes |
| 21060 | Active preset (`value`) | active_preset | yes |
| 20301, 20635, 20890, 22357, 20034, 20320 | I / AGC / TB / SBB / Clip / O in the meter bar | TYPE_DISPLAYTWO | **no** |
| 21078, 20534 | Software version, license | TYPE_DISPLAYTEXT | **no** |

The compact meter bar at the top is largely display-only; the large Input and
Output meters on the main page are the readable ones. Meter labels are not in
the JSON, but they are in the web interface's DOM: every meter block carries
`data-widget-id` and its group button an `aria-label` such as `Meter: O`.

## A recipe that works

Three items are enough to catch most failures:

| Item | JSON path | Trigger |
|---|---|---|
| input level | `$["2612"].value_db` | `max(...,5m) < -55` → no audio at the input |
| output level | `$["20252"].value_db` | `max(...,5m) < -50` → no MPX output |
| active preset | `$["21060"].value` | hourly, for the dashboard and change history |

The Zabbix template in `integrations/zabbix/` watches the decoder; the encoder
template described here is the same idea with three HTTP agent items and needs
no agent on the Windows machine that runs Stereo Tool.

## Why this matters

A real case, 13 November 2026: Stereo Tool on one site crashed. The decoder
kept going on its buffer for a moment, the level fell to 0.09, measured loss
jumped to 59% — and the backup player never engaged, because the gap was
shorter than its 60 second timeout. Nothing in the decoder monitoring said
which side was at fault. The encoder items would have said it immediately.
