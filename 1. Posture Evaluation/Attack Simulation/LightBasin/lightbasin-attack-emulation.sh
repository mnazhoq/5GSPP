#!/usr/bin/env bash
set -euo pipefail

# Defensive LightBasin emulation (safe-only) against lab namespace.
TS="$(date +%Y%m%d-%H%M%S)"
OUT_BASE="/home/ubuntu/attacker-vm/APT implementation/LightBasin"
OUT_FILE="${OUT_BASE}/lightbasin-emulation-${TS}.log"

run_on_master() {
  cd /home/ubuntu/quick-kubernetes
  vagrant ssh k8s-master -c "$1"
}

log() {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "${OUT_FILE}"
}

log "Starting defensive LightBasin emulation"
log "Output file: ${OUT_FILE}"

log "Step 1: Cluster and 5G reconnaissance simulation"
run_on_master "kubectl get ns" | tee -a "${OUT_FILE}" || true
run_on_master "kubectl get pods -n free5gc -o wide" | tee -a "${OUT_FILE}" || true
run_on_master "kubectl get svc -n free5gc" | tee -a "${OUT_FILE}" || true

log "Step 2: API permission and token exposure checks (read-only)"
run_on_master "kubectl auth can-i --list | head -60" | tee -a "${OUT_FILE}" || true
run_on_master "POD=\$(kubectl get pods -n free5gc -o jsonpath='{.items[0].metadata.name}'); [ -n \"\$POD\" ] && kubectl exec -n free5gc \"\$POD\" -- sh -c 'ls -l /var/run/secrets/kubernetes.io/serviceaccount || true'" | tee -a "${OUT_FILE}" || true

log "Step 3: Cross-pod execution simulation"
run_on_master "SRC=\$(kubectl get pods -n free5gc -o jsonpath='{.items[0].metadata.name}'); [ -n \"\$SRC\" ] && kubectl exec -n free5gc \"\$SRC\" -- sh -c 'id; uname -a; ip a | head -20'" | tee -a "${OUT_FILE}" || true
run_on_master "kubectl get pods -n free5gc -o jsonpath='{range .items[*]}{.metadata.name}{\"\\n\"}{end}'" | tee -a "${OUT_FILE}" || true

log "Step 4: Collection and staging behavior simulation"
run_on_master "POD=\$(kubectl get pods -n free5gc -o jsonpath='{.items[0].metadata.name}'); [ -n \"\$POD\" ] && kubectl exec -n free5gc \"\$POD\" -- sh -c 'mkdir -p /tmp/lightbasin-demo && ps aux > /tmp/lightbasin-demo/ps.txt 2>/dev/null || true; tar -czf /tmp/lightbasin-demo.tgz /tmp/lightbasin-demo 2>/dev/null || true; ls -lh /tmp/lightbasin-demo.tgz 2>/dev/null || true'" | tee -a "${OUT_FILE}" || true

log "Step 5: Controlled egress probe simulation"
run_on_master "POD=\$(kubectl get pods -n free5gc -o jsonpath='{.items[0].metadata.name}'); [ -n \"\$POD\" ] && kubectl exec -n free5gc \"\$POD\" -- sh -c 'which curl >/dev/null 2>&1 && curl -I --max-time 3 https://example.com >/tmp/lightbasin-curl.out 2>&1 || true; tail -20 /tmp/lightbasin-curl.out 2>/dev/null || true'" | tee -a "${OUT_FILE}" || true

log "Defensive LightBasin emulation completed"
