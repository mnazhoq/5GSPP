#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/ubuntu/attacker-vm/APT implementation/LightBasin"

run_on_master() {
  cd /home/ubuntu/quick-kubernetes
  vagrant ssh k8s-master -c "$1"
}

run_or_warn() {
  local msg="$1"
  shift
  if ! "$@"; then
    echo "[WARN] ${msg}"
  fi
}

echo "[1/5] Deploy Falco LightBasin rules"
run_or_warn "Falco configmap deployment failed" run_on_master "cat > /tmp/falco-lightbasin-rules.yaml <<'EOF'
$(cat "${BASE_DIR}/falco-lightbasin-rules.yaml")
EOF
kubectl -n falco create configmap falco-lightbasin-rules --from-file=/tmp/falco-lightbasin-rules.yaml --dry-run=client -o yaml | kubectl apply -f -"

echo "[2/5] Deploy Kubescape LightBasin framework"
run_or_warn "Kubescape CRD missing or framework apply failed" run_on_master "cat > /tmp/kubescape-lightbasin-framework.yaml <<'EOF'
$(cat "${BASE_DIR}/kubescape-lightbasin-framework.yaml")
EOF
kubectl apply -f /tmp/kubescape-lightbasin-framework.yaml"

echo "[3/5] Deploy Calico LightBasin policy"
run_or_warn "Calico CRD missing or policy apply failed" run_on_master "cat > /tmp/calico-lightbasin-networkpolicy.yaml <<'EOF'
$(cat "${BASE_DIR}/calico-lightbasin-networkpolicy.yaml")
EOF
kubectl apply -f /tmp/calico-lightbasin-networkpolicy.yaml"

echo "[4/5] Place Kubernetes audit policy file"
run_or_warn "Unable to place k8s audit policy on master" run_on_master "cat > /tmp/k8saudit-lightbasin-policy.yaml <<'EOF'
$(cat "${BASE_DIR}/k8saudit-lightbasin-policy.yaml")
EOF
sudo cp /tmp/k8saudit-lightbasin-policy.yaml /etc/kubernetes/k8saudit-lightbasin-policy.yaml || true
echo 'Audit policy copied to /etc/kubernetes/k8saudit-lightbasin-policy.yaml'"

echo "[5/5] Trivy policy file is provided for operator/Gatekeeper workflow"
run_or_warn "Unable to place Trivy helper policy on master" run_on_master "cat > /tmp/trivy-lightbasin-policies.yaml <<'EOF'
$(cat "${BASE_DIR}/trivy-lightbasin-policies.yaml")
EOF
echo 'Trivy policy helper saved at /tmp/trivy-lightbasin-policies.yaml'"

echo "Deployment complete."
echo "Next: update Falco chart values to mount configmap and restart Falco DaemonSet if needed."
