# LightBasin Multi-Source Collection Summary

- Timestamp: 20260409-145221
- Syslog file: /home/ubuntu/attacker-vm/APT implementation/LightBasin/lightbasin-syslog-20260409-145221.log
- K8s events: /home/ubuntu/attacker-vm/APT implementation/LightBasin/lightbasin-k8s-events-20260409-145221.log
- 5G pod logs: /home/ubuntu/attacker-vm/APT implementation/LightBasin/lightbasin-free5gc-podlogs-20260409-145221.log
- Falco alerts: /home/ubuntu/attacker-vm/APT implementation/LightBasin/lightbasin-falco-alerts-20260409-145221.log
- Kubescape findings: /home/ubuntu/attacker-vm/APT implementation/LightBasin/lightbasin-kubescape-20260409-145221.json
- Trivy reports: /home/ubuntu/attacker-vm/APT implementation/LightBasin/lightbasin-trivy-vulnreports-20260409-145221.json
- Calico logs: /home/ubuntu/attacker-vm/APT implementation/LightBasin/lightbasin-calico-20260409-145221.log
- K8s audit logs: /home/ubuntu/attacker-vm/APT implementation/LightBasin/lightbasin-k8saudit-20260409-145221.log

## Quick counts
- Syslog lines: 1987
- K8s events lines: 573
- Pod log lines: 977
- Falco lines: 4
- Calico lines: 2392
- K8s audit lines: 2002

## Top Falco LightBasin hits

grep -E "LIGHTBASIN|LightBasin|priority" "/home/ubuntu/attacker-vm/APT implementation/LightBasin/lightbasin-falco-alerts-20260409-145221.log" | tail -n 25

## Recent suspicious audit verbs

grep -E '"verb":"(create|update|patch|delete|get|list)"' "/home/ubuntu/attacker-vm/APT implementation/LightBasin/lightbasin-k8saudit-20260409-145221.log" | tail -n 25
