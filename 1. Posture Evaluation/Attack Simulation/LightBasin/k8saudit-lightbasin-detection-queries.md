# LightBasin K8s Audit Detection Queries

Use these queries against audit log exports from:
- `/var/log/kubernetes/audit.log`
- `/var/log/apiserver/audit.log`

## 1) Pod exec spikes in free5gc
```bash
grep '"objectRef":{"resource":"pods","subresource":"exec"' lightbasin-k8saudit-*.log | grep '"namespace":"free5gc"'
```

## 2) Secret reads in free5gc
```bash
grep '"objectRef":{"resource":"secrets"' lightbasin-k8saudit-*.log | grep '"namespace":"free5gc"' | grep '"verb":"get"\|"verb":"list"'
```

## 3) RBAC changes
```bash
grep '"apiGroup":"rbac.authorization.k8s.io"' lightbasin-k8saudit-*.log | grep '"verb":"create"\|"verb":"update"\|"verb":"patch"\|"verb":"delete"'
```

## 4) Suspicious anonymous activity
```bash
grep '"user":{"username":"system:anonymous"' lightbasin-k8saudit-*.log
```

## 5) Timeline extraction (UTC)
```bash
grep -o '"stageTimestamp":"[^"]*"' lightbasin-k8saudit-*.log | sort | uniq -c
```
