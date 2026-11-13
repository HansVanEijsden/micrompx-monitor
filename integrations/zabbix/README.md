# Zabbix

Two files:

- `userparameter_micrompx.conf` — the agent side. One `UserParameter` per
  metric, each doing exactly one HTTP request to the decoder.
- `micrompx_template.yaml` — a Zabbix 8.0 template (imports fine on 7.x as
  well; the export version tag may need adjusting) with nine items, five
  triggers and a graph.

## Install on the host that runs the agent

The agent usually runs on the same machine as the decoder, so the JSON
interface is reachable on 127.0.0.1 — that is the safest option.

```bash
sudo install -m 755 micrompx-monitor /usr/local/bin/micrompx-monitor
sudo install -m 644 integrations/zabbix/userparameter_micrompx.conf \
    /etc/zabbix/zabbix_agent2.d/micrompx.conf
sudo systemctl restart zabbix-agent2
```

Test as the account the agent runs as (it is `zabbix` on Debian/Ubuntu):

```bash
su -s /bin/sh zabbix -c '/usr/local/bin/micrompx-monitor --port 8080 widget 23185 --format value'
```

If that prints a number, the agent can read it too. If it prints an error, the
port is wrong, the decoder is on another address, or the agent user cannot run
the script. Note that the JSON interface does not need any privileges — it is
HTTP.

## Import the template and link it

1. *Data collection → Templates → Import* → choose
   `micrompx_template.yaml` → check *Create missing* for templates, items,
   triggers and graphs.
2. Link **MicroMPX decoder** to the host that represents the unit.
3. Set the host macro `{$MICROMPX.PORT}`: **80** or **8080**.
4. Wait one minute; the items appear under *Latest data*.

If your agent runs inside a container or on another machine, either give the
host a proper interface and put the decoder's address in the items, or skip the
Zabbix agent and use the Prometheus/SNMP route below.

## What the template alerts on

- measured loss above 0.5 % (5 min min) — warning
- measured loss above 2 % — high
- backup player on air — high
- no MPX output signal for 5 minutes — high
- no data for 10 minutes (decoder or agent unreachable) — high

All items and triggers are named in English; the graph combines loss (left
axis) with the MPX level (right axis).
## Dashboard widgets stay empty?

An SVG graph widget in Zabbix references its data by **visible host name**
(`ds.N.hosts.0`), not by the technical host name. If you gave a host a
friendly display name (*"1Zwolle — MicroMPX decoder"*) while the widget
points at `1Zwolle-mMPX-Zwolle`, the widget renders a title and nothing else:
no axes, no legend, no lines.

Two ways out: point the widget at the visible name, or keep the visible name
identical to the technical one. The second is simpler and is what this
repository's examples assume.

Rule of thumb when a widget looks broken: **axes present = data problem**
(no history yet, wrong item), **no axes at all = resolution problem** (host or
item name does not match).
