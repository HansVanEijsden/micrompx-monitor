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
| 20252 | Final (FM) output level (`value`, `value_db`) | wave | yes |
| 20631 | MP / MPX power (`main`), the loudness meter | processing | yes |
| 23242 | Speech detection (`main`, `2nd`) | processing | yes |
| 21060 | Active preset (`value`) | active_preset | yes |
| 20301, 20635, 20890, 22357, 20034, 20320 | I / AGC / TB / SBB / Clip / O in the meter bar | TYPE_DISPLAYTWO | **no** |
| 21078, 20534 | Software version, license | TYPE_DISPLAYTEXT | **no** |

The compact meter bar at the top is largely display-only; the large Input and
Output meters on the main page are the readable ones. Meter labels are not in
the JSON, but they are in the web interface's DOM: every meter block carries
`data-widget-id` and its group button an `aria-label` such as `Meter: O`.

## How to identify a widget yourself

Two ways, neither needs a change to the running stream:

1. **In the web interface.** Open the encoder GUI and inspect the element in
   the browser's developer tools. Every meter block carries
   `data-widget-id`, and the group button above it an `aria-label` such as
   `Meter: O`. That is how 20252 was traced to the **Output** group and 2612
   to **Input**.
2. **By behaviour** (more conclusive). Sample a widget for a minute and look
   at how it moves. Measured on two encoders:

| Widget | mean | min–max | stddev | correlation with input |
|---|---|---|---|---|
| 2612 (input), site A | -2.0 dB | -7.0 … -0.8 | 1.50 | — |
| 2612 (input), site B | -12.7 dB | -20.6 … -7.6 | 2.94 | — |
| 20252 (output), site A | -0.2 dB | -3.1 … 0.0 | 0.56 | 0.57 |
| 20252 (output), site B | -0.2 dB | -1.6 … 0.0 | 0.33 | 0.35 |

The input follows the programme; the output stays pinned near 0 dBFS because
it is the *processed* FM output. A meter that does not follow the music is a
post-processing tap.

Careful with **20631** (`MP`): it barely moves, which made me mistake it for a
setting at first. It is not — it is the **MPX power meter in dBr**, the number
broadcast engineers use to judge processing loudness. It moves slowly on
purpose: it is a long-term average, not a level.
## Reading the MP (MPX power) meter

Widget 20631 reports `main`, the needle position as a fraction of the meter,
with `db_range: 18`. The scale runs from **+12 dBr at the top to −6 dBr at
the bottom**, so the conversion is:

```
dBr = main * 18 - 6
```

Measured: 0.782 → 8.0 dBr (site A), 0.770 → 7.9 dBr (site B) — both in the
7–9 dBr that FM broadcasters aim for. A value well below 7 means the
processing is not contributing enough loudness; far above 9 means it is being
overdriven (and MPX power regulations are about dBr, not about peak level).

So the two numbers worth graphing next to each other are the **input level**
(what comes in) and the **MPX power** (how loud it goes out):

```bash
micrompx-monitor --host 10.0.0.10 --port 8080 widget 20631 --format json
```
## A recipe that works

Three items are enough to catch most failures:

| Item | JSON path | Trigger |
|---|---|---|
| input level | `$["2612"].value_db` | `max(...,5m) < -55` → no audio at the input |
| output level | `$["20252"].value_db` | `max(...,5m) < -50` → no MPX output |
| active preset | `$["21060"].value` | hourly, for the dashboard and change history |
| MPX power | `$["20631"].main * 18 - 6` | slow-moving, for loudness trending, not for alerting |

The Zabbix template in `integrations/zabbix/` watches the decoder; the encoder
template described here is the same idea with three HTTP agent items and needs
no agent on the Windows machine that runs Stereo Tool.

## Why this matters

A real case, 13 November 2026: Stereo Tool on one site crashed. The decoder
kept going on its buffer for a moment, the level fell to 0.09, measured loss
jumped to 59% — and the backup player never engaged, because the gap was
shorter than its 60 second timeout. Nothing in the decoder monitoring said
which side was at fault. The encoder items would have said it immediately.