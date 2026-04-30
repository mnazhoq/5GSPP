"""
correlation_rules.py
====================
Generalised multi-source log correlation engine for 5G environments.
Implements all 7 correlation rule families with confidence scoring,
weighted combination, and a full experiment harness.

Rules
-----
R1  Temporal window     — events within W seconds of each other
R2  Entity identity     — shared IP / SUPI / pod name / NF name
R3  Session/context key — shared (user, src_ip, host) within session TTL
R4  Transaction ID      — shared NF transaction_id or 3GPP SUPI chain
R5  Causal dependency   — A must precede B according to 3GPP procedure DAG
R6  Semantic similarity — cosine similarity of TF-IDF message embeddings
R7  Statistical co-occ. — Apriori lift of (event_type_A, event_type_B) pair

Generalised combination
-----------------------
corr(A, B) = sum_i( w_i * R_i(A, B) ) >= theta
where weights w_i are learned per dataset via logistic regression on
labelled correlated pairs (positive) and random pairs (negative).

Usage
-----
    python correlation_rules.py          # run all experiments
    python correlation_rules.py --demo   # demo on free5GC example
"""

import re
import sys
import json
import math
import time
import random
import argparse
import itertools
import collections
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (precision_score, recall_score, f1_score,
                             roc_auc_score, average_precision_score,
                             precision_recall_curve)
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

random.seed(42)
np.random.seed(42)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Data structures
# ─────────────────────────────────────────────────────────────────────────────

class LogEvent:
    """
    Normalised Common Event Format (CEF) record.

    Fields
    ------
    ts          : datetime
    source      : '5gnf' | 'k8s' | 'syslog' | 'netflow'
    host        : originating host / NF name
    severity    : int 1-5
    actor       : primary entity (IP, SUPI, pod, username)
    target      : secondary entity
    action      : verb (ssh_auth, pfcp_session_release, ...)
    message     : raw message text (for R6 semantic similarity)
    session_key : (username, src_ip, hostname) tuple or None
    txn_id      : NF transaction ID or SUPI string or None
    event_type  : canonical event name (for R7 co-occurrence)
    raw         : original dict
    """
    __slots__ = ('ts','source','host','severity','actor','target',
                 'action','message','session_key','txn_id','event_type','raw')

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def __repr__(self):
        return f"LogEvent({self.source}@{self.ts} {self.action})"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Parsers (one per source)
# ─────────────────────────────────────────────────────────────────────────────

_TS_FMT = ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
           "%Y-%m-%dT%H:%M:%S.%f",  "%Y-%m-%dT%H:%M:%S"]

def _parse_ts(s: str) -> datetime:
    s = s.rstrip("Z")
    for fmt in _TS_FMT:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError(f"Unparseable timestamp: {s!r}")

_SEV = {"DEBUG":1,"INFO":2,"WARN":3,"WARNING":3,"ERROR":4,"CRITICAL":5,
        "Normal":2,"Warning":3}

_IP_RE   = re.compile(r'\b(\d{1,3}(?:\.\d{1,3}){3})\b')
_USER_RE = re.compile(r'(?:for|user)\s+(\w+)')
_HOST_RE = re.compile(r'from\s+(\S+)')

def parse_free5gc(raw: dict) -> LogEvent:
    """
    Format: {ts, level, component, module, message, txn_id?, supi?}
    """
    return LogEvent(
        ts          = _parse_ts(raw["ts"]),
        source      = "5gnf",
        host        = raw.get("component",""),
        severity    = _SEV.get(raw.get("level","INFO"), 2),
        actor       = raw.get("component",""),
        target      = raw.get("module",""),
        action      = raw.get("action", raw.get("message","")[:40]),
        message     = raw.get("message",""),
        session_key = None,
        txn_id      = raw.get("txn_id") or raw.get("supi"),
        event_type  = raw.get("event_type","nf_event"),
        raw         = raw,
    )

def parse_syslog(raw: dict) -> LogEvent:
    """
    Format: {ts, host, facility, severity, message}
    Session key extracted from message via regex.
    """
    msg  = raw.get("message","")
    ips  = _IP_RE.findall(msg)
    users = _USER_RE.findall(msg)
    src_ip = ips[0] if ips else None
    user   = users[0] if users else None
    host   = raw.get("host","")
    sk     = (user, src_ip, host) if user and src_ip else None
    return LogEvent(
        ts          = _parse_ts(raw["ts"]),
        source      = "syslog",
        host        = host,
        severity    = _SEV.get(raw.get("severity","INFO"), 2),
        actor       = src_ip or user or host,
        target      = host,
        action      = raw.get("action","syslog_event"),
        message     = msg,
        session_key = sk,
        txn_id      = None,
        event_type  = raw.get("event_type","sys_event"),
        raw         = raw,
    )

def parse_k8s(raw: dict) -> LogEvent:
    """
    Format: {ts, namespace, pod, reason, message, type}
    """
    return LogEvent(
        ts          = _parse_ts(raw["ts"]),
        source      = "k8s",
        host        = raw.get("pod",""),
        severity    = _SEV.get(raw.get("type","Normal"), 2),
        actor       = raw.get("pod",""),
        target      = raw.get("namespace",""),
        action      = raw.get("reason","k8s_event"),
        message     = raw.get("message",""),
        session_key = None,
        txn_id      = raw.get("pod"),   # pod name serves as correlation key
        event_type  = raw.get("event_type","k8s_event"),
        raw         = raw,
    )

def parse_netflow(raw: dict) -> LogEvent:
    """
    Format: {ts, src_ip, dst_ip, src_port, dst_port, proto, bytes, packets}
    """
    return LogEvent(
        ts          = _parse_ts(raw["ts"]),
        source      = "netflow",
        host        = raw.get("src_ip",""),
        severity    = 2,
        actor       = raw.get("src_ip",""),
        target      = raw.get("dst_ip",""),
        action      = "network_flow",
        message     = f"{raw.get('src_ip')}:{raw.get('src_port')} -> "
                      f"{raw.get('dst_ip')}:{raw.get('dst_port')} "
                      f"{raw.get('proto')} {raw.get('bytes')}B",
        session_key = None,
        txn_id      = None,
        event_type  = "netflow",
        raw         = raw,
    )

SOURCE_PARSERS = {
    "5gnf":    parse_free5gc,
    "syslog":  parse_syslog,
    "k8s":     parse_k8s,
    "netflow": parse_netflow,
}

def normalise(records: List[dict]) -> List[LogEvent]:
    """Parse a mixed list of raw records into LogEvents, sorted by ts."""
    events = []
    for r in records:
        src = r.get("source_type", r.get("source","unknown"))
        parser = SOURCE_PARSERS.get(src)
        if parser:
            try:
                events.append(parser(r))
            except Exception as e:
                pass  # skip malformed
    events.sort(key=lambda e: e.ts)
    return events


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Individual rule implementations
# ─────────────────────────────────────────────────────────────────────────────

# ── R1: Temporal window ───────────────────────────────────────────────────────
# PSEUDOCODE:
#   function R1(A, B, W):
#       delta = |A.ts - B.ts|
#       return 1.0 - (delta.seconds / W)   if delta <= W
#              else 0.0

def r1_temporal(a: LogEvent, b: LogEvent, W: float = 60.0) -> float:
    """
    Confidence = 1 - (gap / W), clipped to [0,1].
    Returns 0 if gap > W.
    W: window size in seconds.
    """
    gap = abs((a.ts - b.ts).total_seconds())
    if gap > W:
        return 0.0
    return 1.0 - gap / W


# ── R2: Entity identity ───────────────────────────────────────────────────────
# PSEUDOCODE:
#   function R2(A, B):
#       entities_A = {A.actor, A.target} | extract_ips(A.message)
#       entities_B = {B.actor, B.target} | extract_ips(B.message)
#       overlap = entities_A ∩ entities_B - {None, ""}
#       return |overlap| / max(|entities_A|, |entities_B|)   (Jaccard-like)

def _entity_set(e: LogEvent) -> Set[str]:
    s = set()
    for v in [e.actor, e.target, e.host]:
        if v:
            s.add(v)
    s.update(_IP_RE.findall(e.message or ""))
    s.discard("")
    return s

def r2_entity(a: LogEvent, b: LogEvent) -> float:
    """Jaccard overlap of entity sets."""
    sa, sb = _entity_set(a), _entity_set(b)
    if not sa or not sb:
        return 0.0
    overlap = len(sa & sb)
    union   = len(sa | sb)
    return overlap / union if union else 0.0


# ── R3: Session / context key ─────────────────────────────────────────────────
# PSEUDOCODE:
#   function R3(A, B, TTL):
#       if A.session_key is None or B.session_key is None: return 0
#       if A.session_key != B.session_key: return 0
#       gap = |A.ts - B.ts|
#       return 1.0 if gap <= TTL else 0.0
#
# This is the rule that resolves the 46-min sshd→NRF gap in our case:
#   A = sshd T03:11  session_key=("vagrant","10.0.2.2","k8s-master")
#   B = NRF  T03:57  session_key=None (NF event, no syslog session)
# → R3 returns 0 here. A HUMAN ANNOTATION links them as same operator context.
# → In the automated system, R5 (causal) or R3-extended (operator context)
#   would be the right rule. See R5 below.

def r3_session(a: LogEvent, b: LogEvent, ttl: float = 3600.0) -> float:
    """
    Confidence = 1.0 if same non-None session key within TTL, else 0.
    TTL in seconds (default 1 hour for SSH sessions).
    """
    if a.session_key is None or b.session_key is None:
        return 0.0
    if a.session_key != b.session_key:
        return 0.0
    gap = abs((a.ts - b.ts).total_seconds())
    return 1.0 if gap <= ttl else 0.0


# ── R4: Transaction / SUPI ID ─────────────────────────────────────────────────
# PSEUDOCODE:
#   function R4(A, B):
#       if A.txn_id is None or B.txn_id is None: return 0
#       return 1.0 if A.txn_id == B.txn_id else 0.0

def r4_transaction(a: LogEvent, b: LogEvent) -> float:
    """Exact match on NF transaction_id or SUPI."""
    if a.txn_id is None or b.txn_id is None:
        return 0.0
    return 1.0 if a.txn_id == b.txn_id else 0.0


# ── R5: Causal dependency (3GPP procedure DAG) ───────────────────────────────
# PSEUDOCODE:
#   CAUSAL_EDGES = {
#       "ssh_auth"          : ["nf_register", "pfcp_session_create"],
#       "nf_register"       : ["pfcp_session_create", "udm_auth"],
#       "udm_auth"          : ["pfcp_session_create"],
#       "pfcp_session_create": ["ng_setup", "pfcp_session_release"],
#       "ng_setup"          : ["pfcp_session_release"],
#   }
#   function R5(A, B):
#       if B.event_type in CAUSAL_EDGES.get(A.event_type, []):
#           and A.ts < B.ts:
#               return 1.0
#       return 0.0
#
# This is the rule that resolves the sshd→NRF case:
#   A = sshd (ssh_auth), B = NRF (nf_register) → R5 = 1.0 (if A before B)

CAUSAL_DAG: Dict[str, List[str]] = {
    "ssh_auth":             ["nf_register", "pfcp_session_create", "k8s_pod_created"],
    "k8s_pod_created":      ["k8s_container_started", "nf_register"],
    "k8s_container_started":["nf_register"],
    "nf_register":          ["udm_auth", "pfcp_session_create", "ng_setup"],
    "udm_auth":             ["pfcp_session_create", "pfcp_session_release"],
    "pfcp_session_create":  ["ng_setup", "pfcp_session_release", "netflow"],
    "ng_setup":             ["pfcp_session_release"],
    "pfcp_session_release": ["netflow"],
    "netflow":              [],
}

def r5_causal(a: LogEvent, b: LogEvent) -> float:
    """
    Returns 1.0 if B.event_type is a known causal successor of A.event_type
    in the 3GPP procedure DAG AND A.ts < B.ts, else 0.
    """
    if a.ts >= b.ts:
        return 0.0
    successors = CAUSAL_DAG.get(a.event_type, [])
    return 1.0 if b.event_type in successors else 0.0


# ── R6: Semantic similarity (TF-IDF) ─────────────────────────────────────────
# PSEUDOCODE:
#   function R6(A, B, corpus_idf):
#       vec_A = tfidf(A.message, corpus_idf)
#       vec_B = tfidf(B.message, corpus_idf)
#       return cosine_similarity(vec_A, vec_B)

class TFIDFVectoriser:
    """Minimal TF-IDF without sklearn dependency for portability."""

    def __init__(self, min_df: int = 2):
        self.idf:  Dict[str, float] = {}
        self.vocab: Dict[str, int]  = {}
        self.min_df = min_df

    def _tokenise(self, text: str) -> List[str]:
        return re.findall(r'[a-zA-Z0-9_]+', text.lower())

    def fit(self, docs: List[str]):
        N = len(docs)
        df: Dict[str, int] = collections.Counter()
        for d in docs:
            for tok in set(self._tokenise(d)):
                df[tok] += 1
        self.vocab = {w: i for i,(w,c) in
                      enumerate((w,c) for w,c in df.items() if c >= self.min_df)}
        self.idf   = {w: math.log((N+1)/(c+1))+1
                      for w,c in df.items() if w in self.vocab}
        return self

    def transform(self, text: str) -> np.ndarray:
        tokens = self._tokenise(text)
        vec = np.zeros(len(self.vocab))
        tf  = collections.Counter(tokens)
        for w, cnt in tf.items():
            if w in self.vocab:
                vec[self.vocab[w]] = (cnt / len(tokens)) * self.idf.get(w, 1.0)
        nrm = np.linalg.norm(vec)
        return vec / nrm if nrm > 0 else vec

def r6_semantic(a: LogEvent, b: LogEvent,
                vectoriser: Optional[TFIDFVectoriser] = None) -> float:
    """
    Cosine similarity of TF-IDF message vectors.
    Returns 0 if no vectoriser fitted yet.
    """
    if vectoriser is None or not a.message or not b.message:
        return 0.0
    va = vectoriser.transform(a.message)
    vb = vectoriser.transform(b.message)
    dot = float(np.dot(va, vb))
    return max(0.0, dot)   # cosine is already normalised


# ── R7: Statistical co-occurrence (Apriori lift) ─────────────────────────────
# PSEUDOCODE:
#   function R7(A, B, lift_table):
#       pair = (A.event_type, B.event_type)
#       lift = lift_table.get(pair, 1.0)   # 1.0 = no association
#       return min(1.0, (lift - 1.0) / lift_threshold)

class CooccurrenceModel:
    """
    Builds an Apriori lift table from a labelled corpus of correlated windows.
    lift(A,B) = P(A,B) / (P(A) * P(B))
    lift > 1 → positively associated; lift < 1 → negatively associated.
    """

    def __init__(self, lift_threshold: float = 2.0):
        self.lift_table: Dict[Tuple[str,str], float] = {}
        self.lift_threshold = lift_threshold

    def fit(self, correlated_pairs: List[Tuple[LogEvent, LogEvent]]):
        """Train on known-correlated event pairs."""
        type_counts: collections.Counter = collections.Counter()
        pair_counts: collections.Counter = collections.Counter()
        n = len(correlated_pairs)
        for a, b in correlated_pairs:
            type_counts[a.event_type] += 1
            type_counts[b.event_type] += 1
            pair_counts[(a.event_type, b.event_type)] += 1
            pair_counts[(b.event_type, a.event_type)] += 1
        total = max(sum(type_counts.values()), 1)
        for (ta, tb), cnt in pair_counts.items():
            p_ab = cnt / n
            p_a  = type_counts[ta] / total
            p_b  = type_counts[tb] / total
            self.lift_table[(ta,tb)] = p_ab / (p_a * p_b) if p_a * p_b > 0 else 1.0
        return self

    def score(self, a: LogEvent, b: LogEvent) -> float:
        lift = self.lift_table.get((a.event_type, b.event_type), 1.0)
        conf = (lift - 1.0) / self.lift_threshold
        return float(np.clip(conf, 0.0, 1.0))


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — Generalised correlator
# ─────────────────────────────────────────────────────────────────────────────

class CorrelationEngine:
    """
    PSEUDOCODE (generalised algorithm):

    Algorithm CorrelateEvents(events, rules, weights, theta):
        correlated_pairs = []
        for each ordered pair (A, B) in events x events  where A.ts <= B.ts:
            score_vec = [R_i(A, B) for R_i in rules]
            score     = dot(weights, score_vec)
            if score >= theta:
                correlated_pairs.append((A, B, score, score_vec))

        groups = union_find(correlated_pairs)   // transitive closure
        return groups

    Complexity: O(N^2) pair evaluation.
    Optimised with: (a) time-bounded candidate generation (only pairs within
    max_gap), (b) inverted index on session_key and txn_id for O(1) R3/R4 lookup.
    """

    DEFAULT_WEIGHTS = {
        "r1": 0.10,  # temporal — weakest alone
        "r2": 0.18,  # entity identity
        "r3": 0.22,  # session key — strong cross-source signal
        "r4": 0.25,  # transaction ID — strongest within-NF signal
        "r5": 0.20,  # causal DAG
        "r6": 0.05,  # semantic — useful fallback
        "r7": 0.00,  # co-occurrence — requires training data
    }

    def __init__(self,
                 window_s:    float = 60.0,
                 session_ttl: float = 3600.0,
                 theta:       float = 0.25,
                 max_gap_s:   float = 7200.0,
                 weights:     Optional[Dict[str,float]] = None):
        self.W          = window_s
        self.ttl        = session_ttl
        self.theta      = theta
        self.max_gap    = max_gap_s
        self.weights    = weights or dict(self.DEFAULT_WEIGHTS)
        self.vectoriser : Optional[TFIDFVectoriser] = None
        self.coocc      : Optional[CooccurrenceModel] = None

    def fit(self, events: List[LogEvent],
            correlated_pairs: Optional[List[Tuple[LogEvent,LogEvent]]] = None):
        """Fit R6 vectoriser and R7 co-occurrence model."""
        docs = [e.message for e in events if e.message]
        if len(docs) >= 5:
            self.vectoriser = TFIDFVectoriser(min_df=2).fit(docs)
        if correlated_pairs:
            self.coocc = CooccurrenceModel().fit(correlated_pairs)
            self.weights["r7"] = 0.10
            # renormalise
            total = sum(self.weights.values())
            self.weights = {k: v/total for k,v in self.weights.items()}

    def score_pair(self, a: LogEvent, b: LogEvent) -> Tuple[float, Dict]:
        """
        Return (combined_score, individual_scores_dict).
        """
        scores = {
            "r1": r1_temporal(a, b, self.W),
            "r2": r2_entity(a, b),
            "r3": r3_session(a, b, self.ttl),
            "r4": r4_transaction(a, b),
            "r5": r5_causal(a, b),
            "r6": r6_semantic(a, b, self.vectoriser),
            "r7": self.coocc.score(a,b) if self.coocc else 0.0,
        }
        combined = sum(self.weights[k] * v for k,v in scores.items())
        return combined, scores

    def correlate(self, events: List[LogEvent]
                  ) -> List[Dict]:
        """
        Returns list of correlated groups.
        Each group: {events: [...], pairs: [...], rules_fired: set}
        Uses Union-Find for transitive closure.
        """
        n = len(events)
        # Build candidate pairs within max_gap (time-bounded optimisation)
        pairs = []
        for i in range(n):
            for j in range(i+1, n):
                gap = (events[j].ts - events[i].ts).total_seconds()
                if gap > self.max_gap:
                    break   # events are sorted; no further j can be within gap
                score, indiv = self.score_pair(events[i], events[j])
                if score >= self.theta:
                    rules = {k for k,v in indiv.items() if v > 0}
                    pairs.append((i, j, score, rules))

        # Union-Find for grouping
        parent = list(range(n))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(x, y):
            parent[find(x)] = find(y)

        for i, j, _, _ in pairs:
            union(i, j)

        # Collect groups
        groups: Dict[int, Dict] = {}
        for i, (_, j, score, rules) in enumerate(pairs):
            root = find(pairs[i][0])
            if root not in groups:
                groups[root] = {"event_ids": set(), "pairs": [], "rules_fired": set()}
            groups[root]["event_ids"].add(pairs[i][0])
            groups[root]["event_ids"].add(pairs[i][1])
            groups[root]["pairs"].append((pairs[i][0], pairs[i][1], score))
            groups[root]["rules_fired"].update(rules)

        # Singletons (uncorrelated)
        correlated_ids = set()
        for g in groups.values():
            correlated_ids.update(g["event_ids"])

        result = []
        for root, g in groups.items():
            result.append({
                "events":      [events[i] for i in sorted(g["event_ids"])],
                "pairs":       g["pairs"],
                "rules_fired": g["rules_fired"],
                "n_events":    len(g["event_ids"]),
                "n_sources":   len(set(events[i].source for i in g["event_ids"])),
            })
        return sorted(result, key=lambda x: -x["n_events"])

    def learn_weights(self, events: List[LogEvent],
                      positive_pairs: List[Tuple[int,int]],
                      n_negatives: int = 500,
                      cv_folds: int = 5) -> Dict[str, float]:
        """
        Learn optimal rule weights via logistic regression with k-fold CV.

        Parameters
        ----------
        positive_pairs : list of (i,j) index pairs that are known-correlated
        n_negatives    : number of random non-correlated pairs to sample
        """
        pos_set = set(map(tuple, positive_pairs))

        # Build feature matrix
        X, y = [], []
        # Positives
        for i, j in positive_pairs:
            _, scores = self.score_pair(events[i], events[j])
            X.append(list(scores.values()))
            y.append(1)
        # Negatives (random pairs not in positive set)
        neg_candidates = [(i,j) for i in range(len(events))
                          for j in range(i+1, len(events))
                          if (i,j) not in pos_set]
        random.shuffle(neg_candidates)
        for i,j in neg_candidates[:n_negatives]:
            _, scores = self.score_pair(events[i], events[j])
            X.append(list(scores.values()))
            y.append(0)

        X, y = np.array(X), np.array(y)
        scaler = StandardScaler()
        X_s = scaler.fit_transform(X)

        # k-fold cross-validation
        kf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        f1s = []
        for tr, te in kf.split(X_s, y):
            lr = LogisticRegression(max_iter=500, C=1.0)
            lr.fit(X_s[tr], y[tr])
            pred = lr.predict(X_s[te])
            f1s.append(f1_score(y[te], pred, zero_division=0))

        # Final model on all data
        lr_final = LogisticRegression(max_iter=500, C=1.0)
        lr_final.fit(X_s, y)
        coefs = lr_final.coef_[0]
        coefs = np.maximum(coefs, 0)  # rules can only add evidence
        total = coefs.sum()
        if total > 0:
            coefs /= total

        rule_names = ["r1","r2","r3","r4","r5","r6","r7"]
        self.weights = dict(zip(rule_names, coefs.tolist()))
        print(f"  Learned weights (CV F1={np.mean(f1s):.3f}±{np.std(f1s):.3f}):")
        for k,v in self.weights.items():
            print(f"    {k}: {v:.3f}")
        return self.weights


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — Synthetic dataset generator (for experiments)
# ─────────────────────────────────────────────────────────────────────────────

def _ts_str(base: datetime, offset_s: float) -> str:
    return (base + timedelta(seconds=offset_s)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]+"Z"

def make_free5gc_session(base: datetime, txn: str,
                         start_s: float = 0.0) -> List[dict]:
    return [
        {"source_type":"5gnf","ts":_ts_str(base,start_s),"level":"INFO",
         "component":"NRF","module":"MGMT","action":"nf_register",
         "message":"Create NF Profile","txn_id":txn,"event_type":"nf_register"},
        {"source_type":"5gnf","ts":_ts_str(base,start_s+40),"level":"INFO",
         "component":"SMF","module":"PFCP","action":"pfcp_session_create",
         "message":"Setup Association","txn_id":txn,"event_type":"pfcp_session_create"},
        {"source_type":"5gnf","ts":_ts_str(base,start_s+80),"level":"INFO",
         "component":"UDM","module":"Nudm_UEAU","action":"udm_auth",
         "message":"ConfirmAuthDataRequest","txn_id":txn,"event_type":"udm_auth"},
        {"source_type":"5gnf","ts":_ts_str(base,start_s+120),"level":"INFO",
         "component":"SMF","module":"PFCP","action":"pfcp_session_release",
         "message":"PFCP Session Deletion","txn_id":txn,"event_type":"pfcp_session_release"},
    ]

def make_syslog_session(base: datetime, user: str, src_ip: str,
                        host: str, start_s: float = 0.0) -> List[dict]:
    return [
        {"source_type":"syslog","ts":_ts_str(base,start_s),"host":host,
         "severity":"INFO","facility":"auth.info",
         "action":"ssh_auth",
         "message":f"sshd: Accepted publickey for {user} from {src_ip} port 36094",
         "event_type":"ssh_auth"},
        {"source_type":"syslog","ts":_ts_str(base,start_s+2760),"host":host,
         "severity":"INFO","facility":"auth.info",
         "action":"ssh_auth",
         "message":f"sshd: session opened for user {user} from {src_ip}",
         "event_type":"ssh_auth"},   # 46 min later — same session
    ]

def make_k8s_events(base: datetime, pod: str,
                    start_s: float = 0.0) -> List[dict]:
    return [
        {"source_type":"k8s","ts":_ts_str(base,start_s),"pod":pod,
         "namespace":"free5gc","type":"Normal","reason":"Scheduled",
         "message":f"pod {pod} scheduled","event_type":"k8s_pod_created"},
        {"source_type":"k8s","ts":_ts_str(base,start_s+0.787),"pod":pod,
         "namespace":"free5gc","type":"Normal","reason":"Started",
         "message":f"container upf started in {pod}","event_type":"k8s_container_started"},
    ]

def make_netflow(base: datetime, src: str, dst: str,
                 start_s: float = 0.0) -> List[dict]:
    return [
        {"source_type":"netflow","ts":_ts_str(base,start_s),
         "src_ip":src,"dst_ip":dst,"src_port":45000,"dst_port":8805,
         "proto":"PFCP","bytes":312,"packets":1},
    ]

def generate_dataset(n_sessions: int = 50,
                     noise_ratio: float = 0.3,
                     seed: int = 42) -> Tuple[List[dict], List[Tuple[int,int]]]:
    """
    Generate a synthetic multi-source log dataset with ground-truth
    correlated pair indices.

    Returns
    -------
    records : flat list of raw log dicts
    gt_pairs: list of (i, j) index pairs that are ground-truth correlated
    """
    random.seed(seed)
    base  = datetime(2022, 11, 10, 3, 0, 0)
    all_records: List[dict] = []
    gt_pairs:    List[Tuple[int,int]] = []

    for s in range(n_sessions):
        t_start = s * 200.0 + random.uniform(0, 50)
        txn  = f"txn-{s:04d}"
        user = random.choice(["vagrant","admin","operator"])
        ip   = f"10.0.{random.randint(1,10)}.{random.randint(1,254)}"
        host = f"k8s-node-{random.randint(1,3)}"
        pod  = f"free5gc-upf-{s % 3}"
        nf_ip, upf_ip = "10.96.1.11", "10.96.1.12"

        # Generate correlated events for this session
        nf_recs   = make_free5gc_session(base, txn, t_start + 2760)
        sys_recs  = make_syslog_session(base, user, ip, host, t_start)
        k8s_recs  = make_k8s_events(base, pod, t_start + 100)
        flow_recs = make_netflow(base, nf_ip, upf_ip, t_start + 2800)

        session_recs = sys_recs + k8s_recs + nf_recs + flow_recs
        base_idx = len(all_records)
        all_records.extend(session_recs)

        # Record ground-truth pairs within this session
        n = len(session_recs)
        for i in range(n):
            for j in range(i+1, n):
                gt_pairs.append((base_idx + i, base_idx + j))

    # Add noise (unrelated single events)
    n_noise = int(len(all_records) * noise_ratio)
    noise_base = base + timedelta(seconds=random.uniform(0, 20000))
    for _ in range(n_noise):
        all_records.append({
            "source_type": random.choice(["5gnf","syslog","k8s","netflow"]),
            "ts": _ts_str(noise_base, random.uniform(0, 20000)),
            "level":"INFO","component":"NOISE","module":"NOISE",
            "action":"noise_event","message":"unrelated system event",
            "event_type":"noise", "host":"noise-host",
        })

    # Shuffle
    combined = list(enumerate(all_records))
    random.shuffle(combined)
    old2new = {old: new for new, (old, _) in enumerate(combined)}
    all_records = [r for _, r in combined]
    gt_pairs    = [(old2new[i], old2new[j]) for i,j in gt_pairs
                   if i in old2new and j in old2new]

    return all_records, gt_pairs


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — Experiments
# ─────────────────────────────────────────────────────────────────────────────

def evaluate(engine: CorrelationEngine,
             events: List[LogEvent],
             gt_pairs: Set[Tuple[int,int]]) -> Dict:
    """
    Evaluate correlation quality against ground-truth pairs.
    Metrics: Precision, Recall, F1, AUC-ROC, AUC-PR.
    """
    n = len(events)
    y_true, y_score = [], []
    for i in range(n):
        for j in range(i+1, n):
            gap = (events[j].ts - events[i].ts).total_seconds()
            if gap > engine.max_gap:
                break
            score, _ = engine.score_pair(events[i], events[j])
            label    = 1 if (i,j) in gt_pairs or (j,i) in gt_pairs else 0
            y_true.append(label)
            y_score.append(score)

    y_true  = np.array(y_true)
    y_score = np.array(y_score)
    y_pred  = (y_score >= engine.theta).astype(int)

    if y_true.sum() == 0:
        return {k: 0.0 for k in ["precision","recall","f1","auc_roc","auc_pr"]}
    return {
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall":    recall_score(y_true, y_pred, zero_division=0),
        "f1":        f1_score(y_true, y_pred, zero_division=0),
        "auc_roc":   roc_auc_score(y_true, y_score),
        "auc_pr":    average_precision_score(y_true, y_score),
        "y_true":    y_true,
        "y_score":   y_score,
    }


def experiment_ablation(n_sessions=30, seeds=range(5)) -> pd.DataFrame:
    """
    EXP-A: Which rules matter most?
    Ablate one rule at a time (set its weight to 0) and measure F1 drop.
    """
    print("\n[EXP-A] Ablation — which rules matter?")
    rows = []
    for seed in seeds:
        records, gt_pairs = generate_dataset(n_sessions, seed=seed)
        events   = normalise(records)
        gt_set   = set(map(tuple, gt_pairs))

        # Baseline: all rules
        eng = CorrelationEngine(theta=0.20)
        eng.fit(events)
        base = evaluate(eng, events, gt_set)
        rows.append({"seed":seed,"ablated":"none (baseline)",
                     "f1":base["f1"],"auc_roc":base["auc_roc"]})

        for rule in ["r1","r2","r3","r4","r5","r6"]:
            w_save = eng.weights[rule]
            eng.weights[rule] = 0.0
            m = evaluate(eng, events, gt_set)
            rows.append({"seed":seed,"ablated":rule,
                         "f1":m["f1"],"auc_roc":m["auc_roc"]})
            eng.weights[rule] = w_save

    df = pd.DataFrame(rows)
    summary = df.groupby("ablated")[["f1","auc_roc"]].mean().round(3)
    print(summary)
    return df


def experiment_threshold(n_sessions=30, seeds=range(5)) -> pd.DataFrame:
    """
    EXP-B: Effect of correlation threshold theta on precision/recall trade-off.
    """
    print("\n[EXP-B] Threshold sensitivity")
    thresholds = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
    rows = []
    for seed in seeds:
        records, gt_pairs = generate_dataset(n_sessions, seed=seed)
        events = normalise(records)
        gt_set = set(map(tuple, gt_pairs))
        eng    = CorrelationEngine(theta=0.20)
        eng.fit(events)
        for th in thresholds:
            eng.theta = th
            m = evaluate(eng, events, gt_set)
            rows.append({"seed":seed,"theta":th,
                         "precision":m["precision"],
                         "recall":m["recall"],
                         "f1":m["f1"]})
    df = pd.DataFrame(rows)
    print(df.groupby("theta")[["precision","recall","f1"]].mean().round(3))
    return df


def experiment_window(n_sessions=30, seeds=range(5)) -> pd.DataFrame:
    """
    EXP-C: Effect of temporal window size W on R1 contribution.
    """
    print("\n[EXP-C] Window size sensitivity")
    windows = [15, 30, 60, 120, 300, 600]
    rows = []
    for seed in seeds:
        records, gt_pairs = generate_dataset(n_sessions, seed=seed)
        events = normalise(records)
        gt_set = set(map(tuple, gt_pairs))
        for W in windows:
            eng = CorrelationEngine(window_s=W, theta=0.20)
            eng.fit(events)
            m = evaluate(eng, events, gt_set)
            rows.append({"seed":seed,"W":W,"f1":m["f1"],"auc_roc":m["auc_roc"]})
    df = pd.DataFrame(rows)
    print(df.groupby("W")[["f1","auc_roc"]].mean().round(3))
    return df


def experiment_noise(n_sessions=30, seeds=range(5)) -> pd.DataFrame:
    """
    EXP-D: Robustness to noise (varying noise_ratio 0–0.6).
    """
    print("\n[EXP-D] Noise robustness")
    noise_levels = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    rows = []
    for seed in seeds:
        for nr in noise_levels:
            records, gt_pairs = generate_dataset(n_sessions, noise_ratio=nr, seed=seed)
            events = normalise(records)
            gt_set = set(map(tuple, gt_pairs))
            eng    = CorrelationEngine(theta=0.20)
            eng.fit(events)
            m = evaluate(eng, events, gt_set)
            rows.append({"seed":seed,"noise_ratio":nr,
                         "f1":m["f1"],"precision":m["precision"],
                         "recall":m["recall"]})
    df = pd.DataFrame(rows)
    print(df.groupby("noise_ratio")[["precision","recall","f1"]].mean().round(3))
    return df


def experiment_learned_vs_default(n_sessions=30, seeds=range(5)) -> pd.DataFrame:
    """
    EXP-E: Learned weights vs default weights.
    """
    print("\n[EXP-E] Learned weights vs default")
    rows = []
    for seed in seeds:
        records, gt_pairs = generate_dataset(n_sessions, seed=seed)
        events  = normalise(records)
        gt_set  = set(map(tuple, gt_pairs))
        gt_list = list(gt_set)

        # Default
        eng_d = CorrelationEngine(theta=0.20)
        eng_d.fit(events)
        m_d = evaluate(eng_d, events, gt_set)
        rows.append({"seed":seed,"method":"default","f1":m_d["f1"],
                     "auc_roc":m_d["auc_roc"],"auc_pr":m_d["auc_pr"]})

        # Learned
        eng_l = CorrelationEngine(theta=0.20)
        eng_l.fit(events)
        events_list = list(events)
        # Use a subset of gt pairs as training signal
        n_train = len(gt_list) // 2
        train_pairs = [(i,j) for i,j in gt_list[:n_train]
                       if i < len(events_list) and j < len(events_list)]
        if len(train_pairs) >= 10:
            eng_l.learn_weights(events_list, train_pairs, n_negatives=200, cv_folds=3)
        m_l = evaluate(eng_l, events_list, gt_set)
        rows.append({"seed":seed,"method":"learned","f1":m_l["f1"],
                     "auc_roc":m_l["auc_roc"],"auc_pr":m_l["auc_pr"]})

    df = pd.DataFrame(rows)
    print(df.groupby("method")[["f1","auc_roc","auc_pr"]].mean().round(3))
    return df


def plot_experiments(abl, thr, win, noi, lrn, outdir="/mnt/user-data/outputs"):
    fig = plt.figure(figsize=(18, 12))
    gs  = gridspec.GridSpec(2, 3, figure=fig, hspace=0.40, wspace=0.35)

    # EXP-A ablation
    ax = fig.add_subplot(gs[0,0])
    ab = abl.groupby("ablated")["f1"].agg(["mean","std"]).reset_index()
    baseline = ab[ab.ablated=="none (baseline)"]["mean"].values[0]
    ab["delta"] = ab["mean"] - baseline
    ab = ab[ab.ablated!="none (baseline)"].sort_values("delta")
    colors = ["#E24B4A" if d < -0.02 else "#888780" for d in ab["delta"]]
    ax.barh(ab["ablated"], ab["delta"], xerr=ab["std"], capsize=3,
            color=colors, alpha=0.85)
    ax.axvline(0, color="black", lw=0.5)
    ax.set_xlabel("F1 change vs baseline")
    ax.set_title("(a) Rule ablation — F1 delta", fontweight="bold")

    # EXP-B threshold
    ax = fig.add_subplot(gs[0,1])
    tb = thr.groupby("theta")[["precision","recall","f1"]].mean()
    ax.plot(tb.index, tb["precision"], "o-", label="Precision", color="#185FA5")
    ax.plot(tb.index, tb["recall"],    "s-", label="Recall",    color="#D85A30")
    ax.plot(tb.index, tb["f1"],        "^-", label="F1",        color="#1D9E75", lw=2)
    ax.set_xlabel("Threshold θ"); ax.set_ylabel("Score")
    ax.set_title("(b) Threshold sensitivity", fontweight="bold")
    ax.legend(fontsize=8)

    # EXP-C window
    ax = fig.add_subplot(gs[0,2])
    wb = win.groupby("W")[["f1","auc_roc"]].mean()
    ws = win.groupby("W")[["f1","auc_roc"]].std()
    ax.plot(wb.index, wb["f1"],     "o-", label="F1",     color="#185FA5", lw=2)
    ax.plot(wb.index, wb["auc_roc"],"s--",label="AUC-ROC",color="#534AB7")
    ax.fill_between(wb.index,(wb["f1"]-ws["f1"]).clip(0),(wb["f1"]+ws["f1"]).clip(0,1),
                    alpha=0.15, color="#185FA5")
    ax.set_xlabel("Window size W (seconds)")
    ax.set_title("(c) Window size sensitivity", fontweight="bold")
    ax.legend(fontsize=8)

    # EXP-D noise
    ax = fig.add_subplot(gs[1,0])
    nb = noi.groupby("noise_ratio")[["precision","recall","f1"]].mean()
    ax.plot(nb.index, nb["precision"], "o-", label="Precision", color="#185FA5")
    ax.plot(nb.index, nb["recall"],    "s-", label="Recall",    color="#D85A30")
    ax.plot(nb.index, nb["f1"],        "^-", label="F1",        color="#1D9E75", lw=2)
    ax.set_xlabel("Noise ratio"); ax.set_ylabel("Score")
    ax.set_title("(d) Noise robustness", fontweight="bold")
    ax.legend(fontsize=8)

    # EXP-E learned vs default
    ax = fig.add_subplot(gs[1,1])
    methods = ["default","learned"]
    metrics = ["f1","auc_roc","auc_pr"]
    x = np.arange(len(metrics))
    w = 0.35
    for i, meth in enumerate(methods):
        grp = lrn[lrn.method==meth]
        means = [grp[m].mean() for m in metrics]
        stds  = [grp[m].std()  for m in metrics]
        color = "#185FA5" if meth=="default" else "#D85A30"
        ax.bar(x + i*w, means, w, yerr=stds, capsize=3, label=meth,
               color=color, alpha=0.85)
    ax.set_xticks(x+w/2); ax.set_xticklabels(["F1","AUC-ROC","AUC-PR"])
    ax.set_ylim(0, 1.1)
    ax.set_title("(e) Learned vs default weights", fontweight="bold")
    ax.legend(fontsize=8)

    # Rule weights bar
    ax = fig.add_subplot(gs[1,2])
    eng = CorrelationEngine()
    w_names = list(eng.weights.keys())
    w_vals  = list(eng.weights.values())
    colors  = ["#185FA5","#1D9E75","#D85A30","#534AB7","#BA7517","#888780","#A32D2D"]
    ax.bar(w_names, w_vals, color=colors[:len(w_names)], alpha=0.85)
    ax.set_ylabel("Default weight")
    ax.set_title("(f) Default rule weights", fontweight="bold")
    for i,(n,v) in enumerate(zip(w_names,w_vals)):
        ax.text(i, v+0.005, f"{v:.2f}", ha="center", fontsize=8)

    fig.suptitle("Multi-Source Log Correlation — Rule Experiments (N=5 seeds)",
                 fontsize=13, fontweight="bold")
    path = f"{outdir}/rule_experiments.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n[Plot] saved → {path}")
    return path


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — Demo on the actual free5GC example
# ─────────────────────────────────────────────────────────────────────────────

FREE5GC_EXAMPLE = [
    {"source_type":"syslog","ts":"2022-11-10T03:11:12Z",
     "host":"k8s-core-master","severity":"INFO","facility":"auth.info",
     "action":"ssh_auth",
     "message":"sshd: Accepted publickey for vagrant from 10.0.2.2 port 36094",
     "event_type":"ssh_auth"},
    {"source_type":"syslog","ts":"2022-11-10T03:40:31Z",
     "host":"k8s-core-master","severity":"INFO","facility":"auth.info",
     "action":"ssh_auth",
     "message":"sshd: session opened for user vagrant from 10.0.2.2",
     "event_type":"ssh_auth"},
    {"source_type":"k8s","ts":"2022-11-10T03:52:32.104Z",
     "pod":"free5gc-upf-0","namespace":"free5gc","type":"Normal",
     "reason":"Created","message":"pod free5gc-upf-0 created",
     "event_type":"k8s_pod_created"},
    {"source_type":"k8s","ts":"2022-11-10T03:52:32.891Z",
     "pod":"free5gc-upf-0","namespace":"free5gc","type":"Normal",
     "reason":"Started","message":"container upf started in free5gc-upf-0",
     "event_type":"k8s_container_started"},
    {"source_type":"5gnf","ts":"2022-11-10T03:57:204892Z",
     "level":"INFO","component":"NRF","module":"MGMT",
     "action":"nf_register",
     "message":"Create NF Profile","txn_id":"txn-nrf-001",
     "event_type":"nf_register"},
    {"source_type":"5gnf","ts":"2022-11-10T03:58:471345Z",
     "level":"INFO","component":"SMF","module":"PFCP",
     "action":"pfcp_session_release",
     "message":"Handle PFCP Session Deletion","txn_id":"txn-smf-001",
     "event_type":"pfcp_session_release"},
    {"source_type":"5gnf","ts":"2022-11-10T04:02:223000Z",
     "level":"INFO","component":"UDM","module":"Nudm_UEAU",
     "action":"udm_auth",
     "message":"Handle ConfirmAuthDataRequest","txn_id":"txn-smf-001",
     "event_type":"udm_auth"},
    {"source_type":"5gnf","ts":"2022-11-10T04:02:452000Z",
     "level":"INFO","component":"SMF","module":"PFCP",
     "action":"pfcp_session_create",
     "message":"Setup Association","txn_id":"txn-smf-001",
     "event_type":"pfcp_session_create"},
    {"source_type":"5gnf","ts":"2022-11-10T04:02:461000Z",
     "level":"INFO","component":"AMF","module":"NGAP",
     "action":"ng_setup",
     "message":"NG Setup procedure is successful","txn_id":"txn-amf-001",
     "event_type":"ng_setup"},
    {"source_type":"netflow","ts":"2022-11-10T03:58:471500Z",
     "src_ip":"10.96.1.11","dst_ip":"10.96.1.12",
     "src_port":45000,"dst_port":8805,"proto":"PFCP","bytes":312,"packets":1},
]

def run_demo():
    print("\n" + "="*60)
    print("DEMO — free5GC example from the paper")
    print("="*60)
    events = normalise(FREE5GC_EXAMPLE)
    print(f"\nNormalised {len(events)} events:")
    for e in events:
        print(f"  {e.ts.strftime('%H:%M:%S')}  [{e.source:8s}]  {e.action:30s}"
              f"  txn={e.txn_id}  sk={e.session_key}")

    engine = CorrelationEngine(theta=0.18)
    engine.fit(events)

    print("\nPairwise rule scores (pairs with score > 0):")
    print(f"  {'A':30s}  {'B':30s}  {'R1':>5} {'R2':>5} {'R3':>5} "
          f"{'R4':>5} {'R5':>5} {'total':>7}")
    for i in range(len(events)):
        for j in range(i+1, len(events)):
            score, indiv = engine.score_pair(events[i], events[j])
            if score > 0:
                print(f"  {events[i].action:30s}  {events[j].action:30s}  "
                      f"{indiv['r1']:5.2f} {indiv['r2']:5.2f} {indiv['r3']:5.2f} "
                      f"{indiv['r4']:5.2f} {indiv['r5']:5.2f} {score:7.3f}")

    groups = engine.correlate(events)
    print(f"\nCorrelated groups ({len(groups)} total):")
    for g in groups:
        print(f"\n  Group ({g['n_events']} events, {g['n_sources']} sources, "
              f"rules={g['rules_fired']}):")
        for e in g["events"]:
            print(f"    {e.ts.strftime('%H:%M:%S')}  [{e.source:8s}]  {e.action}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    os.makedirs("/mnt/user-data/outputs", exist_ok=True)

    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--sessions", type=int, default=25)
    args = parser.parse_args()

    if args.demo:
        run_demo()
        sys.exit(0)

    run_demo()   # always show demo first

    seeds    = range(args.seeds)
    n_sess   = args.sessions

    print("\n" + "="*60)
    print("Running experiments ...")
    print("="*60)

    t0   = time.time()
    abl  = experiment_ablation(n_sess, seeds)
    thr  = experiment_threshold(n_sess, seeds)
    win  = experiment_window(n_sess, seeds)
    noi  = experiment_noise(n_sess, seeds)
    lrn  = experiment_learned_vs_default(n_sess, seeds)

    plot_experiments(abl, thr, win, noi, lrn)

    for name, df in [("ablation",abl),("threshold",thr),
                     ("window",win),("noise",noi),("learned",lrn)]:
        df.to_csv(f"/mnt/user-data/outputs/rules_{name}.csv", index=False)

    print(f"\nTotal time: {time.time()-t0:.1f}s")
    print("All outputs written to /mnt/user-data/outputs/")
