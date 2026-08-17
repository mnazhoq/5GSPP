"""
correlator.py
-------------
Multi-Source Log Correlation Engine for 5G Telecom SOC

Architecture (inspired by provenance-graph + temporal correlation literature):
  1. Normalisation   – parse heterogeneous logs to a common schema
  2. Entity Extraction – pull out actors: IPs, SUPIs, pods, NF names
  3. Temporal Windowing – sliding-window grouping of co-occurring events
  4. Cross-Source Linking – match entities across log sources
  5. Provenance Graph Construction – directed multigraph of entity interactions
  6. Feature Extraction – structural + statistical features per window
  7. Anomaly Detection – Isolation Forest (unsupervised) + optional GNN embedding
  8. Alert Correlation – group related alerts into incidents via DBSCAN

"""

import re
import json
import hashlib
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
import numpy as np
import networkx as nx
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN

# ══════════════════════════════════════════════════════════════════════════════
# 1. NORMALISATION LAYER
# ══════════════════════════════════════════════════════════════════════════════

class LogNormalizer:
    """
    Converts heterogeneous log records to a Common Event Format (CEF) dict.

    Common schema:
      ts        : ISO8601 timestamp
      source    : '5gnf' | 'k8s' | 'syslog' | 'netflow'
      host      : originating host/IP
      severity  : CRITICAL|ERROR|WARN|INFO|DEBUG
      actor     : primary entity (IP / SUPI / pod-name / NF-name)
      target    : secondary entity, if any
      action    : verb (register, auth, exec, flow, ...)
      attributes: dict of source-specific fields
      raw       : original record
    """

    SEV_MAP = {
        "CRITICAL": 5, "ERROR": 4, "WARN": 3, "WARNING": 3,
        "INFO": 2, "DEBUG": 1
    }

    IP_RE   = re.compile(r'\b(\d{1,3}(?:\.\d{1,3}){3})\b')
    SUPI_RE = re.compile(r'imsi-\d{15}')
    PID_RE  = re.compile(r'\[(\d+)\]')

    def normalize(self, record: Dict) -> Dict:
        src = record.get("source_type", "unknown")
        if src == "5gnf":
            return self._norm_5gnf(record)
        elif src == "k8s":
            return self._norm_k8s(record)
        elif src == "syslog":
            return self._norm_syslog(record)
        elif src == "netflow":
            return self._norm_netflow(record)
        return self._norm_generic(record)

    def _norm_5gnf(self, r: Dict) -> Dict:
        return {
            "ts":         r.get("ts"),
            "source":     "5gnf",
            "host":       r.get("host", r.get("nf","")),
            "severity":   self.SEV_MAP.get(r.get("level","INFO"), 2),
            "actor":      r.get("supi") or r.get("registered_nf") or r.get("nf",""),
            "target":     r.get("nf",""),
            "action":     r.get("event",""),
            "attributes": {k:v for k,v in r.items() if k not in ("ts","source_type","level","host")},
            "raw":        r,
            "label":      r.get("label","NORMAL"),
            "corr_id":    r.get("corr_id",""),
        }

    def _norm_k8s(self, r: Dict) -> Dict:
        return {
            "ts":         r.get("ts"),
            "source":     "k8s",
            "host":       r.get("pod",""),
            "severity":   self.SEV_MAP.get(r.get("level","INFO"), 2),
            "actor":      r.get("pod",""),
            "target":     r.get("namespace",""),
            "action":     "k8s_event",
            "attributes": r,
            "raw":        r,
            "label":      r.get("label","NORMAL"),
            "corr_id":    r.get("corr_id",""),
        }

    def _norm_syslog(self, r: Dict) -> Dict:
        msg  = r.get("msg","")
        ips  = self.IP_RE.findall(msg)
        supis= self.SUPI_RE.findall(msg)
        # Extract action keyword
        action = "syslog_event"
        for kw in ("sshd","sudo","useradd","su[","kernel","auditd","cron"):
            if kw in msg:
                action = kw.strip("["); break
        return {
            "ts":         r.get("ts"),
            "source":     "syslog",
            "host":       r.get("host",""),
            "severity":   self.SEV_MAP.get(r.get("severity","INFO"), 2),
            "actor":      ips[0] if ips else (supis[0] if supis else r.get("host","")),
            "target":     ips[1] if len(ips)>1 else r.get("host",""),
            "action":     action,
            "attributes": {**r, "extracted_ips": ips},
            "raw":        r,
            "label":      r.get("label","NORMAL"),
            "corr_id":    r.get("corr_id",""),
        }

    def _norm_netflow(self, r: Dict) -> Dict:
        return {
            "ts":         r.get("ts"),
            "source":     "netflow",
            "host":       r.get("src_ip",""),
            "severity":   4 if r.get("label","NORMAL")=="ATTACK" else 2,
            "actor":      r.get("src_ip",""),
            "target":     r.get("dst_ip",""),
            "action":     "network_flow",
            "attributes": r,
            "raw":        r,
            "label":      r.get("label","NORMAL"),
            "corr_id":    r.get("corr_id",""),
        }

    def _norm_generic(self, r: Dict) -> Dict:
        return {
            "ts":r.get("ts"),"source":"unknown","host":"","severity":2,
            "actor":"","target":"","action":"unknown","attributes":r,
            "raw":r,"label":"NORMAL","corr_id":""
        }


# ══════════════════════════════════════════════════════════════════════════════
# 2. TEMPORAL WINDOWING
# ══════════════════════════════════════════════════════════════════════════════

class TemporalWindowBatcher:
    """
    Groups normalised events into overlapping sliding windows.

    Parameters
    ----------
    window_s  : window size in seconds
    stride_s  : stride in seconds (overlap = window_s - stride_s)
    """

    def __init__(self, window_s: int = 60, stride_s: int = 30):
        self.window_s = window_s
        self.stride_s = stride_s

    def _parse_ts(self, ts: str) -> datetime:
        # Handle both Z and no-suffix
        ts = ts.replace("Z","")
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try: return datetime.strptime(ts, fmt)
            except: pass
        return datetime.min

    def batch(self, events: List[Dict]) -> List[Dict]:
        """Returns list of window dicts each containing a list of events."""
        if not events:
            return []
        times = [self._parse_ts(e["ts"]) for e in events]
        t_min, t_max = min(times), max(times)

        windows = []
        t_start = t_min
        while t_start < t_max:
            t_end = t_start + timedelta(seconds=self.window_s)
            win_events = [e for e,t in zip(events,times) if t_start <= t < t_end]
            if win_events:
                windows.append({
                    "t_start":  t_start,
                    "t_end":    t_end,
                    "events":   win_events,
                    "n_events": len(win_events),
                })
            t_start += timedelta(seconds=self.stride_s)
        return windows


# ══════════════════════════════════════════════════════════════════════════════
# 3. PROVENANCE GRAPH BUILDER
# ══════════════════════════════════════════════════════════════════════════════

class ProvenanceGraphBuilder:
    """
    Builds a directed multigraph from a window of events.
    Nodes = entities (IPs, SUPIs, pods, NF names).
    Edges = interactions labelled with action + source type.
    """

    def build(self, window_events: List[Dict]) -> nx.MultiDiGraph:
        G = nx.MultiDiGraph()
        for ev in window_events:
            actor  = str(ev.get("actor","") or "?")
            target = str(ev.get("target","") or "?")
            if not actor or actor == "?":
                continue
            # Add/update nodes
            for n, src_label in [(actor, "actor"), (target, "target")]:
                if n not in G:
                    G.add_node(n, sources=set(), actions=[], severity_max=0)
                G.nodes[n]["sources"].add(ev["source"])
                G.nodes[n]["actions"].append(ev["action"])
                G.nodes[n]["severity_max"] = max(
                    G.nodes[n]["severity_max"], ev.get("severity",2))
            # Add edge
            G.add_edge(actor, target,
                       action=ev["action"],
                       source=ev["source"],
                       severity=ev.get("severity",2),
                       ts=ev["ts"])
        return G

    def extract_graph_features(self, G: nx.MultiDiGraph) -> Dict:
        """Structural features used for anomaly detection."""
        if G.number_of_nodes() == 0:
            return {k:0 for k in self._feature_keys()}

        degrees_in  = [d for _,d in G.in_degree()]
        degrees_out = [d for _,d in G.out_degree()]
        # PageRank
        pr  = list(nx.pagerank(G, alpha=0.85, max_iter=50, tol=1e-4).values()) if G.number_of_nodes()>1 else [0]
        # Cross-source edges (actor from src A talking to target on src B)
        cross = sum(1 for u,v,d in G.edges(data=True)
                    if G.nodes[u].get("sources",set()) != G.nodes[v].get("sources",set()))

        feats = {
            "n_nodes":         G.number_of_nodes(),
            "n_edges":         G.number_of_edges(),
            "density":         nx.density(G),
            "in_degree_max":   max(degrees_in)  if degrees_in  else 0,
            "in_degree_mean":  float(np.mean(degrees_in))  if degrees_in  else 0,
            "out_degree_max":  max(degrees_out) if degrees_out else 0,
            "out_degree_mean": float(np.mean(degrees_out)) if degrees_out else 0,
            "pagerank_max":    float(max(pr)),
            "pagerank_mean":   float(np.mean(pr)),
            "cross_src_edges": cross,
            "n_scc":           nx.number_strongly_connected_components(G),
            "severity_max":    max((G.nodes[n].get("severity_max",0) for n in G.nodes), default=0),
            "severity_mean":   float(np.mean([G.nodes[n].get("severity_max",0) for n in G.nodes])),
        }
        return feats

    def _feature_keys(self):
        return ["n_nodes","n_edges","density","in_degree_max","in_degree_mean",
                "out_degree_max","out_degree_mean","pagerank_max","pagerank_mean",
                "cross_src_edges","n_scc","severity_max","severity_mean"]


# ══════════════════════════════════════════════════════════════════════════════
# 4. SOURCE-SPECIFIC FEATURE EXTRACTOR
# ══════════════════════════════════════════════════════════════════════════════

class SourceFeatureExtractor:
    """Extracts per-source statistical features for a window."""

    def extract(self, window_events: List[Dict]) -> Dict:
        feats = {}
        by_source = defaultdict(list)
        for ev in window_events:
            by_source[ev["source"]].append(ev)

        # Global
        feats["total_events"]      = len(window_events)
        feats["n_sources"]         = len(by_source)
        feats["severity_max_all"]  = max((e.get("severity",2) for e in window_events), default=0)
        feats["severity_mean_all"] = float(np.mean([e.get("severity",2) for e in window_events]))

        # 5G NF features
        nf_evs = by_source.get("5gnf", [])
        auth_fail = sum(1 for e in nf_evs if e.get("action","") in ("AuthFailure","NFDeregister"))
        reg_req   = sum(1 for e in nf_evs if e.get("action","") == "RegistrationRequest")
        feats["nf_total"]       = len(nf_evs)
        feats["nf_auth_failure"]= auth_fail
        feats["nf_reg_request"] = reg_req
        feats["nf_auth_fail_ratio"] = auth_fail / max(len(nf_evs),1)
        unique_supis = len(set(e["attributes"].get("supi","") for e in nf_evs if e["attributes"].get("supi")))
        feats["nf_unique_supis"]= unique_supis

        # K8s features
        k8s_evs = by_source.get("k8s", [])
        feats["k8s_total"]      = len(k8s_evs)
        feats["k8s_warn_error"] = sum(1 for e in k8s_evs if e.get("severity",2) >= 3)
        feats["k8s_crash"]      = sum(1 for e in k8s_evs if "CrashLoop" in str(e.get("attributes",{}).get("msg","")))
        feats["k8s_exec"]       = sum(1 for e in k8s_evs if "exec" in str(e.get("attributes",{}).get("msg","")).lower())

        # Syslog features
        sys_evs = by_source.get("syslog", [])
        feats["sys_total"]      = len(sys_evs)
        feats["sys_sudo"]       = sum(1 for e in sys_evs if e.get("action","") == "sudo")
        feats["sys_useradd"]    = sum(1 for e in sys_evs if e.get("action","") == "useradd")
        feats["sys_auth_fail"]  = sum(1 for e in sys_evs if "authentication failure" in str(e.get("attributes",{}).get("msg","")).lower())

        # Netflow features
        fl_evs  = by_source.get("netflow", [])
        bytes_  = [e["attributes"].get("bytes",0) for e in fl_evs]
        feats["flow_total"]        = len(fl_evs)
        feats["flow_bytes_max"]    = float(max(bytes_))  if bytes_ else 0
        feats["flow_bytes_mean"]   = float(np.mean(bytes_)) if bytes_ else 0
        feats["flow_bytes_std"]    = float(np.std(bytes_))  if bytes_ else 0
        unique_dsts = len(set(e["attributes"].get("dst_ip","") for e in fl_evs))
        feats["flow_unique_dsts"]  = unique_dsts
        high_vol = sum(1 for b in bytes_ if b > 500_000)
        feats["flow_high_vol_cnt"] = high_vol

        # Cross-source temporal co-occurrence signals
        k8s_warn_ts  = set(e["ts"] for e in k8s_evs  if e.get("severity",2) >= 3)
        sys_warn_ts  = set(e["ts"] for e in sys_evs   if e.get("severity",2) >= 3)
        nf_warn_ts   = set(e["ts"] for e in nf_evs    if e.get("severity",2) >= 3)
        feats["cross_k8s_sys"]   = len(k8s_warn_ts & sys_warn_ts)
        feats["cross_k8s_nf"]    = len(k8s_warn_ts & nf_warn_ts)
        feats["cross_sys_nf"]    = len(sys_warn_ts  & nf_warn_ts)

        return feats


# ══════════════════════════════════════════════════════════════════════════════
# 5. ANOMALY DETECTOR
# ══════════════════════════════════════════════════════════════════════════════

class AnomalyDetector:
    """
    Isolation Forest trained on benign-only feature vectors.
    At inference time, assigns anomaly scores per window.
    """

    def __init__(self, contamination=0.05, n_estimators=200, random_state=42):
        self.model   = IsolationForest(contamination=contamination,
                                       n_estimators=n_estimators,
                                       random_state=random_state)
        self.scaler  = StandardScaler()
        self.fitted  = False
        self.feat_keys: List[str] = []

    def _vec(self, feature_dict: Dict) -> np.ndarray:
        if not self.feat_keys:
            self.feat_keys = sorted(feature_dict.keys())
        return np.array([feature_dict.get(k, 0) for k in self.feat_keys], dtype=float)

    def fit(self, window_feature_dicts: List[Dict]):
        X = np.vstack([self._vec(f) for f in window_feature_dicts])
        X = self.scaler.fit_transform(X)
        self.model.fit(X)
        self.fitted = True

    def predict(self, feature_dict: Dict) -> Tuple[int, float]:
        """
        Returns (label, score).
        label: -1 = anomalous, 1 = normal
        score: negative = more anomalous (Isolation Forest convention)
        """
        if not self.fitted:
            raise RuntimeError("Detector not fitted")
        x = self.scaler.transform(self._vec(feature_dict).reshape(1,-1))
        label = self.model.predict(x)[0]
        score = self.model.decision_function(x)[0]
        return int(label), float(score)

    def predict_batch(self, feature_dicts: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        X = np.vstack([self._vec(f) for f in feature_dicts])
        X = self.scaler.transform(X)
        labels = self.model.predict(X)
        scores = self.model.decision_function(X)
        return labels, scores


# ══════════════════════════════════════════════════════════════════════════════
# 6. ALERT CORRELATOR
# ══════════════════════════════════════════════════════════════════════════════

class AlertCorrelator:
    """
    Groups anomalous windows into incidents using DBSCAN on (time, score) space.
    Assigns a preliminary attack-type label using rule-based heuristics.
    """

    ATTACK_RULES = {
        "dos_amf":          lambda f: f.get("nf_auth_fail_ratio",0) > 0.4 and f.get("nf_total",0) > 30,
        "signaling_storm":  lambda f: f.get("nf_auth_fail_ratio",0) > 0.3 and f.get("flow_total",0) > 20,
        "lateral_movement": lambda f: f.get("k8s_exec",0) > 0 and f.get("sys_sudo",0) > 0,
        "priv_escalation":  lambda f: f.get("sys_useradd",0) > 0 or f.get("k8s_exec",0) > 0,
        "data_exfil":       lambda f: f.get("flow_high_vol_cnt",0) > 2 and f.get("flow_bytes_max",0) > 400_000,
    }

    def correlate(self, anomalous_windows: List[Dict]) -> List[Dict]:
        """
        anomalous_windows: list of dicts with keys t_start, score, features, events
        Returns: list of incident dicts
        """
        if not anomalous_windows:
            return []

        # Build feature matrix for DBSCAN: (normalised_time, normalised_score)
        t0   = anomalous_windows[0]["t_start"].timestamp()
        t_max = max(w["t_start"].timestamp() for w in anomalous_windows) - t0 + 1
        pts  = np.array([
            [(w["t_start"].timestamp()-t0)/t_max, -w["score"]]  # flip score: higher = more anomalous
            for w in anomalous_windows
        ])

        db   = DBSCAN(eps=0.15, min_samples=2).fit(pts)
        labels_db = db.labels_

        incidents = []
        for cluster_id in set(labels_db):
            if cluster_id == -1:
                continue  # noise
            idxs = [i for i,l in enumerate(labels_db) if l==cluster_id]
            cluster_windows = [anomalous_windows[i] for i in idxs]
            merged_feats = self._merge_features([w["features"] for w in cluster_windows])
            attack_type  = self._classify(merged_feats)
            events_flat  = [ev for w in cluster_windows for ev in w["events"]]

            incidents.append({
                "incident_id":  cluster_id,
                "attack_type":  attack_type,
                "ts_start":     min(w["t_start"] for w in cluster_windows),
                "ts_end":       max(w["t_start"] for w in cluster_windows),
                "n_windows":    len(cluster_windows),
                "n_events":     len(events_flat),
                "score_mean":   float(np.mean([w["score"] for w in cluster_windows])),
                "sources":      list(set(ev["source"] for ev in events_flat)),
                "features":     merged_feats,
            })
        return incidents

    def _merge_features(self, feat_list: List[Dict]) -> Dict:
        keys = feat_list[0].keys()
        return {k: float(np.max([f.get(k,0) for f in feat_list])) for k in keys}

    def _classify(self, feats: Dict) -> str:
        for name, rule in self.ATTACK_RULES.items():
            try:
                if rule(feats):
                    return name
            except Exception:
                pass
        return "unknown"


# ══════════════════════════════════════════════════════════════════════════════
# 7. FULL PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

class MultiSourceCorrelationPipeline:
    """
    End-to-end pipeline:
        raw logs → normalise → window → graph+feature extraction
                → anomaly detection → alert correlation → incidents
    """

    def __init__(self, window_s=60, stride_s=30,
                 contamination=0.05, n_estimators=200):
        self.normalizer   = LogNormalizer()
        self.windower     = TemporalWindowBatcher(window_s, stride_s)
        self.pgb          = ProvenanceGraphBuilder()
        self.sfe          = SourceFeatureExtractor()
        self.detector     = AnomalyDetector(contamination, n_estimators)
        self.correlator   = AlertCorrelator()

    def fit(self, raw_logs_benign: List[Dict]):
        """Train anomaly detector on benign logs."""
        normed   = [self.normalizer.normalize(r) for r in raw_logs_benign]
        windows  = self.windower.batch(normed)
        feat_dicts = []
        for w in windows:
            gfeats = self.pgb.extract_graph_features(self.pgb.build(w["events"]))
            sfeats = self.sfe.extract(w["events"])
            feat_dicts.append({**gfeats, **sfeats})
        self.detector.fit(feat_dicts)
        print(f"[Pipeline] Fitted on {len(feat_dicts)} windows from {len(raw_logs_benign)} benign logs.")

    def predict(self, raw_logs: List[Dict]) -> Dict:
        """
        Run full detection on a log stream.
        Returns dict with windows, anomalies, incidents, feature_matrix.
        """
        normed  = [self.normalizer.normalize(r) for r in raw_logs]
        windows = self.windower.batch(normed)

        window_results = []
        feat_dicts     = []
        for w in windows:
            G      = self.pgb.build(w["events"])
            gfeats = self.pgb.extract_graph_features(G)
            sfeats = self.sfe.extract(w["events"])
            feats  = {**gfeats, **sfeats}
            feat_dicts.append(feats)
            window_results.append({**w, "features": feats, "graph": G})

        labels, scores = self.detector.predict_batch(feat_dicts)
        for i,(w,lb,sc) in enumerate(zip(window_results,labels,scores)):
            w["pred_label"] = int(lb)
            w["score"]      = float(sc)
            w["anomalous"]  = (lb == -1)

        # Ground truth per window (any ATTACK event inside?)
        for w in window_results:
            w["gt_anomalous"] = any(e.get("label","NORMAL")=="ATTACK" for e in w["events"])

        anomalous = [w for w in window_results if w["anomalous"]]
        incidents = self.correlator.correlate(anomalous)

        return {
            "windows":        window_results,
            "anomalous":      anomalous,
            "incidents":      incidents,
            "feature_matrix": feat_dicts,
        }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "/home/claude/5g_soc")
    from log_generator import LogGenerator

    # Quick smoke-test
    gen  = LogGenerator(duration_s=1800, event_rate=15,
                        attack_scenarios=["dos_amf","lateral_movement"])
    logs, gt = gen.generate()

    benign = [l for l in logs if l.get("label","NORMAL") == "NORMAL"]
    pipe   = MultiSourceCorrelationPipeline(window_s=60, stride_s=30)
    pipe.fit(benign)
    res = pipe.predict(logs)

    print(f"Total windows : {len(res['windows'])}")
    print(f"Anomalous     : {len(res['anomalous'])}")
    print(f"Incidents     : {len(res['incidents'])}")
    for inc in res["incidents"]:
        print(f"  → Incident {inc['incident_id']}: {inc['attack_type']}  "
              f"(windows={inc['n_windows']}, events={inc['n_events']})")
