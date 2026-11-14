# Prometheus

`micrompx-monitor values --format prometheus` prints the metrics in the
Prometheus text exposition format. The simplest deployment is the **node
exporter textfile collector**: write the output to a `.prom` file every few
seconds and let node_exporter serve it.

```
micrompx_loss_percent{instance="10.0.0.24:8080",description="1Zwolle Zender Zwolle"} 3.59658
micrompx_mpx_level{instance="10.0.0.24:8080",description="1Zwolle Zender Zwolle"} 0.689731
micrompx_backup_active{instance="10.0.0.24:8080",description="1Zwolle Zender Zwolle"} 0
micrompx_info{instance="10.0.0.24:8080",description="1Zwolle Zender Zwolle",version="5.0.2",rist_source="rist://192.0.2.10:8854"} 1
micrompx_up{instance="10.0.0.24:8080",description="1Zwolle Zender Zwolle"} 1
```

## systemd unit + timer

`/etc/systemd/system/micrompx-textfile.service`:

```ini
[Unit]
Description=Write MicroMPX metrics for node_exporter

[Service]
Type=oneshot
ExecStart=/bin/sh -c '/usr/local/bin/micrompx-monitor --host 127.0.0.1 --port 8080 values --format prometheus > /var/lib/node_exporter/textfile/micrompx.prom.tmp && mv /var/lib/node_exporter/textfile/micrompx.prom.tmp /var/lib/node_exporter/textfile/micrompx.prom'
```

`/etc/systemd/system/micrompx-textfile.timer`:

```ini
[Unit]
Description=Collect MicroMPX metrics every 15 seconds

[Timer]
OnBootSec=30s
OnUnitActiveSec=15s

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now micrompx-textfile.timer
```

Write to a temporary file and rename, so node_exporter never reads a partially
written file. If the decoder is unreachable the script exits non-zero and the
file simply stays at its previous content — add an alert on
`time() - micrompx_up` or use the `micrompx_up` metric with a staleness rule.
Running it by hand against a dead unit prints `micrompx_up … 0` and exits 1,
which is the same statement in the other direction.

A *partial* scrape (one widget refused, the rest readable) still exits 0 and
still writes the file: the missing series is simply absent, which Prometheus
shows as a gap. The names of the metrics that could not be read go to stderr,
so they end up in the journal of the timer above.

## Alert examples

```yaml
groups:
  - name: micrompx
    rules:
      - alert: MicroMPXLoss
        expr: micrompx_loss_percent > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "MicroMPX {{ $labels.description }} is losing {{ $value }}% audio"

      - alert: MicroMPXBackupPlayer
        expr: micrompx_backup_active == 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "MicroMPX {{ $labels.description }} is playing the backup file"
```
