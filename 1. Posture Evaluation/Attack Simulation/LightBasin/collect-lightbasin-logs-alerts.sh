#!/usr/bin/env bash
set -euo pipefail

TS="$(date +%Y%m%d-%H%M%S)"
BASE="/home/ubuntu/attacker-vm/APT implementation/LightBasin"

run_on_master() {
  cd /home/ubuntu/quick-kubernetes
  vagrant ssh k8s-master -c "$1"
}

echo "Collecting LightBasin logs and alerts for timestamp ${TS}"

SYSLOG_FILE="${BASE}/lightbasin-syslog-${TS}.log"
K8S_EVENTS_FILE="${BASE}/lightbasin-k8s-events-${TS}.log"
POD_LOGS_FILE="${BASE}/lightbasin-free5gc-podlogs-${TS}.log"
FALCO_FILE="${BASE}/lightbasin-falco-alerts-${TS}.log"
KUBESCAPE_FILE="${BASE}/lightbasin-kubescape-${TS}.json"
TRIVY_FILE="${BASE}/lightbasin-trivy-vulnreports-${TS}.json"
CALICO_FILE="${BASE}/lightbasin-calico-${TS}.log"
K8SAUDIT_FILE="${BASE}/lightbasin-k8saudit-${TS}.log"
SUMMARY_FILE="${BASE}/lightbasin-summary-${TS}.md"

# 1) Target syslog/journal
run_on_master "sudo journalctl --since '2 hours ago' -n 2000 --no-pager || sudo tail -n 2000 /var/log/syslog" > "${SYSLOG_FILE}" || true

# 2) Kubernetes events and control-plane view
run_on_master "kubectl get events -A --sort-by=.lastTimestamp" > "${K8S_EVENTS_FILE}" || true

# 3) 5G pod logs (all pods in free5gc)
run_on_master "for p in \$(kubectl get pods -n free5gc -o jsonpath='{.items[*].metadata.name}'); do echo '===== POD:'\"\$p\"' ====='; kubectl logs -n free5gc \"\$p\" --tail=200 || true; echo; done" > "${POD_LOGS_FILE}" || true

# 4) Falco alerts
run_on_master "for p in \$(kubectl get pods -n falco -l app.kubernetes.io/name=falco -o jsonpath='{.items[*].metadata.name}'); do echo '===== FALCO POD:'\"\$p\"' ====='; kubectl logs -n falco \"\$p\" --since=2h --tail=800 || true; echo; done; for p in \$(kubectl get pods -n falco -l app.kubernetes.io/name=falcosidekick -o jsonpath='{.items[*].metadata.name}'); do echo '===== FALCOSIDEKICK POD:'\"\$p\"' ====='; kubectl logs -n falco \"\$p\" --since=2h --tail=400 || true; echo; done" > "${FALCO_FILE}" || true

# 5) Kubescape findings
run_on_master "kubectl get workloadconfigscansummaries -A -o json 2>/dev/null || kubectl get vulnerabilitymanifests -A -o json 2>/dev/null || (for p in \$(kubectl get pods -n kubescape -o jsonpath='{.items[*].metadata.name}'); do echo '===== KUBESCAPE POD:'\"\$p\"' ====='; kubectl logs -n kubescape \"\$p\" --since=2h --tail=600 || true; echo; done) || echo '{}'" > "${KUBESCAPE_FILE}" || true

# 6) Trivy vulnerability reports
run_on_master "echo '{\"vulnerabilityreports\":'; kubectl get vulnerabilityreports.aquasecurity.github.io -A -o json 2>/dev/null || echo '{}'; echo ',\"configauditreports\":'; kubectl get configauditreports.aquasecurity.github.io -A -o json 2>/dev/null || echo '{}'; echo '}'" > "${TRIVY_FILE}" || true

# 7) Calico logs
run_on_master "kubectl logs -n kube-system -l k8s-app=calico-node --since=2h --tail=2000" > "${CALICO_FILE}" || true

# 8) Kubernetes audit logs (if enabled)
run_on_master "sudo test -f /var/log/kubernetes/audit.log && sudo tail -n 2000 /var/log/kubernetes/audit.log || sudo test -f /var/log/apiserver/audit.log && sudo tail -n 2000 /var/log/apiserver/audit.log || echo 'k8s audit log file not found'" > "${K8SAUDIT_FILE}" || true

# 9) Summary
cat > "${SUMMARY_FILE}" <<EOF
# LightBasin Multi-Source Collection Summary

- Timestamp: ${TS}
- Syslog file: ${SYSLOG_FILE}
- K8s events: ${K8S_EVENTS_FILE}
- 5G pod logs: ${POD_LOGS_FILE}
- Falco alerts: ${FALCO_FILE}
- Kubescape findings: ${KUBESCAPE_FILE}
- Trivy reports: ${TRIVY_FILE}
- Calico logs: ${CALICO_FILE}
- K8s audit logs: ${K8SAUDIT_FILE}

## Quick counts
- Syslog lines: $(wc -l < "${SYSLOG_FILE}" 2>/dev/null || echo 0)
- K8s events lines: $(wc -l < "${K8S_EVENTS_FILE}" 2>/dev/null || echo 0)
- Pod log lines: $(wc -l < "${POD_LOGS_FILE}" 2>/dev/null || echo 0)
- Falco lines: $(wc -l < "${FALCO_FILE}" 2>/dev/null || echo 0)
- Calico lines: $(wc -l < "${CALICO_FILE}" 2>/dev/null || echo 0)
- K8s audit lines: $(wc -l < "${K8SAUDIT_FILE}" 2>/dev/null || echo 0)

## Top Falco LightBasin hits

grep -E "LIGHTBASIN|LightBasin|priority" "${FALCO_FILE}" | tail -n 25

## Recent suspicious audit verbs

grep -E '"verb":"(create|update|patch|delete|get|list)"' "${K8SAUDIT_FILE}" | tail -n 25
EOF

echo "Collection completed."
echo "Summary: ${SUMMARY_FILE}"
