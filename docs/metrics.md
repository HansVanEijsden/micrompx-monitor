# Metric reference

Everything this tool reports comes straight from the MicroMPX JSON interface.
This page explains what each value means and how to alert on it.

## `loss_percent` — measured loss

Widget 23185, `Measured loss`. The percentage of incoming packets the
decoder had to do without: packets that arrived too late or not at all. It is a
**rolling measurement** (the value moves while you watch it), not a cumulative
counter, and it is *link* loss — the error correction may repair all of it, so
a link can show 20 % loss with perfect audio and the backup player still off.

That is useful, but it also means the number has a baseline per site: one
installation sits at 0.0 %, another at 20 % all day. Alert on the value being
*worse than usual*, not on it being non-zero.

- **0.00 %** — clean link.
- **a few percent** — the path is dropping packets; error correction is working
  but the margin is shrinking.
- **far above the site's baseline** — error correction is being exhausted and
  audible artefacts are likely.

The decoder only falls back to the backup file (see `backup_active`) when the
loss exceeds the configured dropout thresholds, so `loss_percent` moves first.
Watch it for a day or two, write down the normal range per site, and set the
warning threshold a little above it. The Zabbix template does this with the
macros `{$MICROMPX.LOSS.WARN}` and `{$MICROMPX.LOSS.HIGH}`.

## `mpx_level` — MPX output level

Widget 20252, the MPX output meter. `1.0` is 0 dB (100 % deviation), the
normal operating point. A sudden drop to 0 means the decoder is muted or not
producing output. Values above 1.0 mean the MPX is over-deviating.

## `backup_active` — backup player on air

Widget 7966. `1` while the decoder plays its backup file — that is the
"we lost the stream" state. Alert on this with high severity; it is the
clearest on-air problem the decoder can report.

## `inputs`, `udp_port`, `delay_seconds`

Configuration sanity checks: how many MicroMPX inputs are configured, which UDP
port the decoder listens on, and how much delay buffer is configured. They
rarely change; monitoring them detects accidental reconfiguration (or a unit
that came back with a default config).

## `version`, `description`, `rist_source`

Informational, but useful in a dashboard: firmware version, the unit's own
description and the RIST source URL of the first input (handy for spotting a
decoder that reconnected to the wrong encoder).

## Suggested alerts

| condition | severity | why |
|---|---|---|
| `loss_percent > 0.5` (5 min average) | warning | link is dropping packets |
| `loss_percent > 2` (5 min average) | high | audible risk |
| `backup_active = 1` | high | no usable stream, backup on air |
| `mpx_level < 0.01` (5 min average) | high | no MPX output |
| no data for 10 min | high | decoder or agent unreachable |

Tune the loss thresholds to your link: a microwave hop or a congested ISP path
has a different normal than a dedicated fibre. Trend the value for a week
before tightening.