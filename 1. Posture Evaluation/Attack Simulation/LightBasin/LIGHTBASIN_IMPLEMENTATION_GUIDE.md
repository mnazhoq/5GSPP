# LightBasin APT Defensive Emulation and Detection Guide

## Important Scope
This implementation is a **defensive emulation** of telecom-focused LightBasin tradecraft for your isolated lab.
It does not include destructive payloads or unauthorized access techniques.

## Environment Mapping
- Attacker control plane: `attacker-vm` (Caldera in Docker Compose)
- Target cluster VM: `quick-kubernetes` (`k8s-master`, `k8s-node-*`)
- 5G workloads namespace: `free5gc`
- Output path (fixed): `/home/ubuntu/attacker-vm/APT implementation/LightBasin`

## Files Created
- `LIGHTBASIN_IMPLEMENTATION_GUIDE.md` (this file)
- `lightbasin-attack-emulation.sh`
- `deploy-lightbasin-detections.sh`
- `collect-lightbasin-logs-alerts.sh`
- `falco-lightbasin-rules.yaml`
- `kubescape-lightbasin-framework.yaml`
- `trivy-lightbasin-policies.yaml`
- `calico-lightbasin-networkpolicy.yaml`
- `k8saudit-lightbasin-policy.yaml`
- `k8saudit-lightbasin-detection-queries.md`

## Step-by-Step Execution

### Step 1: Validate VMs and cluster access
```bash
cd /home/ubuntu/attacker-vm
vagrant status

cd /home/ubuntu/quick-kubernetes
vagrant status
vagrant ssh k8s-master -c "kubectl get nodes && kubectl get ns"
```

### Step 2: Deploy LightBasin detection content
```bash
cd /home/ubuntu/attacker-vm/APT\ implementation/LightBasin
chmod +x deploy-lightbasin-detections.sh
./deploy-lightbasin-detections.sh
```

What this applies:
- Falco custom rules for runtime TTP indicators
- Kubescape framework custom controls
- Calico network policy hardening profile
- Kubernetes API server audit policy file (host placement command)
- Trivy policy guidance file for operator/Gatekeeper workflow

### Step 3: Start/verify Caldera on attacker VM
```bash
cd /home/ubuntu/attacker-vm
vagrant ssh default -c "docker compose ps || docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

Caldera UI access:
```bash
cd /home/ubuntu/attacker-vm
ATTACKER_IP=$(vagrant ssh default -c "hostname -I | awk '{print \$1}'" 2>/dev/null | tr -d '\r')
echo "http://${ATTACKER_IP}:8888"
```

In Caldera:
1. Create adversary: `LightBasin-5G-Defensive-Emulation`.
2. Add abilities that execute only benign discovery/collection simulation commands.
3. Run operation against your `free5gc` reachable agent/proxy path.

### Step 4: Run LightBasin emulation sequence (safe)
```bash
cd /home/ubuntu/attacker-vm/APT\ implementation/LightBasin
chmod +x lightbasin-attack-emulation.sh
./lightbasin-attack-emulation.sh
```

This script simulates phases:
1. Discovery of 5G pods and services
2. Service-account/token exposure checks (read-only indicators)
3. Cross-pod exec and API permission reconnaissance
4. Data staging/archive behavior simulation
5. Controlled egress behavior simulation for alerting

### Step 5: Collect logs and alerts from all required sources
```bash
cd /home/ubuntu/attacker-vm/APT\ implementation/LightBasin
chmod +x collect-lightbasin-logs-alerts.sh
./collect-lightbasin-logs-alerts.sh
```

Collected sources:
- Target VM syslog/journal
- Kubernetes control-plane and event logs
- 5G pod logs (`free5gc` namespace)
- Falco alerts
- Kubescape scan outputs
- Trivy operator report CRDs
- Calico node logs
- Kubernetes audit logs (if enabled)

### Step 6: Review generated artifacts
All output stays in:
- `/home/ubuntu/attacker-vm/APT implementation/LightBasin`

Key output files (timestamped):
- `lightbasin-summary-<ts>.md`
- `lightbasin-syslog-<ts>.log`
- `lightbasin-k8s-events-<ts>.log`
- `lightbasin-free5gc-podlogs-<ts>.log`
- `lightbasin-falco-alerts-<ts>.log`
- `lightbasin-kubescape-<ts>.json`
- `lightbasin-trivy-vulnreports-<ts>.json`
- `lightbasin-calico-<ts>.log`
- `lightbasin-k8saudit-<ts>.log`

## Detection Mapping by Emulation Step

| Emulation Step | ATT&CK-like Theme | Falco | Kubescape | Trivy | Calico | K8s Audit |
|---|---|---|---|---|---|---|
| Pod and API discovery | Discovery | Detect `kubectl` recon and unusual process execution | RBAC hardening controls | Misconfig checks | Observe lateral traffic patterns | `get/list` surge |
| SA token and secrets access | Credential Access | Detect token path reads | SA automount controls | Secret/config exposure findings | N/A | reads on secrets/configmaps |
| Cross-pod command execution | Lateral Movement | Detect shell and exec patterns in pods | Pod security controls | Container hardening findings | Block cross-namespace unexpected flows | `pods/exec` create events |
| Archive/staging actions | Collection | Detect `tar`, `gzip`, suspicious temp bundles | Volume/path controls | Image/package findings | N/A | unusual write/update patterns |
| Outbound probe behavior | C2 / Exfil simulation | Detect curl/wget egress | Egress exposure controls | N/A | enforce egress policies | network-related object changes |

## Notes for Realistic Telecom Simulation
- Keep all tests in non-production and isolated lab networks.
- Run emulation only against your owned `free5gc` namespace.
- Use your existing ELK pipeline for correlation dashboards.
- If audit logs are not enabled yet, apply policy and restart API server once during maintenance.

## Quick Troubleshooting
- Falco rules not firing:
  - Check `kubectl logs -n falco -l app.kubernetes.io/name=falco --tail=200`
- Kubescape custom framework not found:
  - `kubectl get kubescapeframework -A | grep lightbasin`
- Trivy CRDs empty:
  - wait 3-5 minutes, then run `kubectl get vulnerabilityreports -A`
- Calico logs missing:
  - `kubectl logs -n kube-system -l k8s-app=calico-node --tail=200`
- K8s audit log missing:
  - verify API server `--audit-log-path` and mounted policy file
