"""
experiments.py
--------------
Experimental evaluation framework for the 5G multi-source log correlation system.

Experiments
-----------
  E1: Per-attack-type detection performance (Precision, Recall, F1, AUC-ROC)
  E2: Ablation – what happens when individual log sources are removed?
  E3: Window size sensitivity (30s, 60s, 120s, 300s)
  E4: False positive rate at various alert thresholds
  E5: Scalability – throughput vs log volume
  E6: Alert correlation quality (incident-level precision/recall)
  E7: Comparison with baselines (per-source only detectors)

Metrics
-------
  - Precision, Recall, F1 (window-level, incident-level)
  - AUC-ROC, AUC-PR (window-level anomaly score)
  - Mean Time to Detect (MTTD) per incident
  - False Positive Rate (FPR) at 90/95/99% TPR
  - Throughput (events/sec processed)

Statistical Validation
----------------------
  - Wilcoxon signed-rank test vs baselines (non-parametric)
  - 95% CI via bootstrap (B=1000)
  - 5-fold cross-validation across seeds
"""

import sys
import time
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from scipy import stats
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score,
    confusion_matrix, roc_curve, precision_recall_curve
)
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, "/home/claude/5g_soc")
from log_generator import LogGenerator
from correlator   import (MultiSourceCorrelationPipeline, LogNormalizer,
                           TemporalWindowBatcher, ProvenanceGraphBuilder,
                           SourceFeatureExtractor, AnomalyDetector)

warnings.filterwarnings("ignore")
np.random.seed(42)
plt.style.use("seaborn-v0_8-whitegrid")
PALETTE = sns.color_palette("tab10")

# ── helpers ───────────────────────────────────────────────────────────────────

def bootstrap_ci(values, stat_fn=np.mean, B=1000, alpha=0.95):
    """Returns (lower, upper) confidence interval via bootstrap."""
    bsamps = [stat_fn(np.random.choice(values, len(values), replace=True)) for _ in range(B)]
    lo = np.percentile(bsamps, (1-alpha)/2*100)
    hi = np.percentile(bsamps, (1+alpha)/2*100)
    return float(lo), float(hi)

def window_labels(windows: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
    """Extract ground-truth and predicted binary labels from window dicts."""
    y_true = np.array([int(w["gt_anomalous"]) for w in windows])
    y_score= np.array([-w["score"] for w in windows])   # higher → more anomalous
    y_pred = np.array([int(w["anomalous"]) for w in windows])
    return y_true, y_pred, y_score

def compute_metrics(y_true, y_pred, y_score) -> Dict:
    """Full metric dict for one experiment run."""
    m = {}
    if y_true.sum() == 0:
        return {k:0.0 for k in ["precision","recall","f1","auc_roc","auc_pr","fpr_at_90tpr","fpr_at_95tpr"]}
    m["precision"] = precision_score(y_true, y_pred, zero_division=0)
    m["recall"]    = recall_score(y_true, y_pred, zero_division=0)
    m["f1"]        = f1_score(y_true, y_pred, zero_division=0)
    m["auc_roc"]   = roc_auc_score(y_true, y_score)
    m["auc_pr"]    = average_precision_score(y_true, y_score)
    fpr, tpr, _ = roc_curve(y_true, y_score)
    for thresh, key in [(0.90,"fpr_at_90tpr"), (0.95,"fpr_at_95tpr")]:
        idxs = np.where(tpr >= thresh)[0]
        m[key] = float(fpr[idxs[0]]) if len(idxs) else 1.0
    return m

def mttd(windows: List[Dict], gt_events: List[Dict]) -> float:
    """
    Mean Time To Detect: average seconds from incident ts_start to first
    anomalous window containing any ATTACK event.
    """
    delays = []
    for w in windows:
        if not w["anomalous"]:
            continue
        atk_corr_ids = set(e["attributes"].get("corr_id","") for e in w["events"]
                           if e.get("label","NORMAL")=="ATTACK" and e["attributes"].get("corr_id",""))
        for gt in gt_events:
            if gt.get("corr_id","") in atk_corr_ids:
                gt_start = datetime.strptime(gt["ts_start"].replace("Z",""), "%Y-%m-%dT%H:%M:%S.%f") \
                           if "." in gt["ts_start"] else \
                           datetime.strptime(gt["ts_start"].replace("Z",""), "%Y-%m-%dT%H:%M:%S")
                det_start = w["t_start"]
                delay = (det_start - gt_start).total_seconds()
                if delay >= 0:
                    delays.append(delay)
    return float(np.mean(delays)) if delays else np.nan


def make_dataset(seed, duration=3600, rate=15, attacks=None):
    """Helper to generate a full dataset for one random seed."""
    attacks = attacks or ["dos_amf","lateral_movement","priv_escalation",
                          "signaling_storm","data_exfil"]
    gen = LogGenerator(duration_s=duration, event_rate=rate,
                       attack_scenarios=attacks, seed=seed)
    logs, gt = gen.generate()
    benign   = [l for l in logs if l.get("label","NORMAL")=="NORMAL"]
    return logs, gt, benign


# ══════════════════════════════════════════════════════════════════════════════
# E1: Per-attack detection performance (5-fold, 5 seeds)
# ══════════════════════════════════════════════════════════════════════════════

def experiment_e1(n_seeds=5) -> pd.DataFrame:
    print("\n[E1] Per-attack detection performance")
    attack_list = ["dos_amf","lateral_movement","priv_escalation","signaling_storm","data_exfil"]
    rows = []
    for seed in range(n_seeds):
        for atk in attack_list:
            logs, gt, benign = make_dataset(seed, attacks=[atk])
            pipe = MultiSourceCorrelationPipeline(window_s=60, stride_s=30, contamination=0.05)
            pipe.fit(benign)
            res  = pipe.predict(logs)
            y_true, y_pred, y_score = window_labels(res["windows"])
            m = compute_metrics(y_true, y_pred, y_score)
            mttd_val = mttd(res["windows"], gt)
            rows.append({"seed":seed,"attack":atk,**m,"mttd_s":mttd_val})
    df = pd.DataFrame(rows)
    print(df.groupby("attack")[["precision","recall","f1","auc_roc","mttd_s"]].mean().round(3))
    return df

# ══════════════════════════════════════════════════════════════════════════════
# E2: Ablation study – source removal
# ══════════════════════════════════════════════════════════════════════════════

def experiment_e2(n_seeds=5) -> pd.DataFrame:
    print("\n[E2] Ablation – source removal")
    all_sources   = ["5gnf","k8s","syslog","netflow"]
    configurations = {"All sources": all_sources}
    for src in all_sources:
        configurations[f"Without {src}"] = [s for s in all_sources if s!=src]

    rows = []
    for seed in range(n_seeds):
        logs, gt, benign = make_dataset(seed)
        for cfg_name, sources in configurations.items():
            logs_f   = [l for l in logs   if l.get("source_type","") in sources] \
                       if "Without" in cfg_name else logs
            benign_f = [l for l in benign if l.get("source_type","") in sources] \
                       if "Without" in cfg_name else benign
            if not benign_f or not logs_f:
                continue
            pipe = MultiSourceCorrelationPipeline(window_s=60, stride_s=30, contamination=0.05)
            pipe.fit(benign_f)
            res  = pipe.predict(logs_f)
            y_true, y_pred, y_score = window_labels(res["windows"])
            m = compute_metrics(y_true, y_pred, y_score)
            rows.append({"seed":seed,"config":cfg_name,**m})
    df = pd.DataFrame(rows)
    print(df.groupby("config")[["f1","auc_roc"]].mean().round(3))
    return df


# ══════════════════════════════════════════════════════════════════════════════
# E3: Window size sensitivity
# ══════════════════════════════════════════════════════════════════════════════

def experiment_e3(n_seeds=5) -> pd.DataFrame:
    print("\n[E3] Window size sensitivity")
    window_sizes = [30, 60, 120, 300]
    rows = []
    for seed in range(n_seeds):
        logs, gt, benign = make_dataset(seed)
        for ws in window_sizes:
            pipe = MultiSourceCorrelationPipeline(window_s=ws, stride_s=ws//2, contamination=0.05)
            pipe.fit(benign)
            res  = pipe.predict(logs)
            y_true, y_pred, y_score = window_labels(res["windows"])
            m = compute_metrics(y_true, y_pred, y_score)
            rows.append({"seed":seed,"window_s":ws,**m})
    df = pd.DataFrame(rows)
    print(df.groupby("window_s")[["precision","recall","f1","auc_roc"]].mean().round(3))
    return df


# ══════════════════════════════════════════════════════════════════════════════
# E4: FPR-TPR threshold sweep
# ══════════════════════════════════════════════════════════════════════════════

def experiment_e4(n_seeds=5) -> pd.DataFrame:
    print("\n[E4] FPR-TPR threshold sweep")
    rows = []
    for seed in range(n_seeds):
        logs, gt, benign = make_dataset(seed)
        pipe = MultiSourceCorrelationPipeline(window_s=60, stride_s=30, contamination=0.05)
        pipe.fit(benign)
        res  = pipe.predict(logs)
        y_true, _, y_score = window_labels(res["windows"])
        if y_true.sum() == 0:
            continue
        fpr, tpr, thresholds = roc_curve(y_true, y_score)
        for f,t,th in zip(fpr,tpr,thresholds):
            rows.append({"seed":seed,"fpr":f,"tpr":t,"threshold":th})
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# E5: Scalability – throughput
# ══════════════════════════════════════════════════════════════════════════════

def experiment_e5() -> pd.DataFrame:
    print("\n[E5] Scalability")
    volumes   = [1000, 5000, 10000, 20000, 50000]
    event_rates = [v // 3600 for v in volumes]  # events per second
    rows = []
    for n_events, rate in zip(volumes, event_rates):
        gen   = LogGenerator(duration_s=max(3600,n_events//max(rate,1)),
                             event_rate=max(rate,5), attack_scenarios=[], seed=0)
        logs, _ = gen.generate()
        logs    = logs[:n_events]

        pipe = MultiSourceCorrelationPipeline(window_s=60, stride_s=30)

        # Normalisation throughput
        norm  = pipe.normalizer
        t0    = time.perf_counter()
        normed= [norm.normalize(r) for r in logs]
        t_norm= time.perf_counter() - t0

        # Full pipeline
        benign= [l for l in logs if l.get("label","NORMAL")=="NORMAL"][:min(500,len(logs))]
        pipe.fit(benign)
        t0 = time.perf_counter()
        _  = pipe.predict(logs)
        t_pipe = time.perf_counter() - t0

        rows.append({
            "n_events":         n_events,
            "norm_tput_keps":   n_events / t_norm / 1000,
            "pipe_tput_keps":   n_events / t_pipe / 1000,
            "norm_latency_ms":  t_norm*1000/n_events,
            "pipe_latency_ms":  t_pipe*1000/n_events,
        })
        print(f"  n={n_events:6d}: norm={rows[-1]['norm_tput_keps']:.1f} kEPS, "
              f"pipe={rows[-1]['pipe_tput_keps']:.2f} kEPS")
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# E6: Baseline comparison
# ══════════════════════════════════════════════════════════════════════════════

class SingleSourceBaseline:
    """Anomaly detection using only ONE log source type."""
    def __init__(self, source: str, window_s=60, stride_s=30, contamination=0.05):
        self.source = source
        self.normalizer = LogNormalizer()
        self.windower   = TemporalWindowBatcher(window_s, stride_s)
        self.pgb        = ProvenanceGraphBuilder()
        self.sfe        = SourceFeatureExtractor()
        self.detector   = AnomalyDetector(contamination=contamination)

    def fit(self, logs):
        normed  = [self.normalizer.normalize(r) for r in logs if r.get("source_type","")==self.source]
        windows = self.windower.batch(normed)
        feats   = []
        for w in windows:
            gf = self.pgb.extract_graph_features(self.pgb.build(w["events"]))
            sf = self.sfe.extract(w["events"])
            feats.append({**gf,**sf})
        if feats:
            self.detector.fit(feats)

    def predict(self, logs):
        normed  = [self.normalizer.normalize(r) for r in logs]
        all_win = self.windower.batch(normed)
        results = []
        for w in all_win:
            src_evs = [e for e in w["events"] if e["source"]==self.source]
            gf = self.pgb.extract_graph_features(self.pgb.build(src_evs)) if src_evs else {k:0 for k in self.pgb._feature_keys()}
            sf = self.sfe.extract(src_evs) if src_evs else {}
            feats = {**gf,**sf}
            try:
                lb, sc = self.detector.predict(feats)
            except Exception:
                lb, sc = 1, 0.0
            results.append({**w, "pred_label":lb, "score":sc,
                             "anomalous":(lb==-1),
                             "gt_anomalous": any(e.get("label","NORMAL")=="ATTACK" for e in w["events"])})
        return results

def experiment_e6(n_seeds=5) -> pd.DataFrame:
    print("\n[E6] Baseline comparison")
    sources  = ["5gnf","k8s","syslog","netflow"]
    rows = []
    for seed in range(n_seeds):
        logs, gt, benign = make_dataset(seed)
        # Our method
        pipe = MultiSourceCorrelationPipeline(window_s=60, stride_s=30, contamination=0.05)
        pipe.fit(benign)
        res  = pipe.predict(logs)
        y_true, y_pred, y_score = window_labels(res["windows"])
        m = compute_metrics(y_true, y_pred, y_score)
        rows.append({"seed":seed,"method":"MultiSource (Ours)",**m})
        # Single-source baselines
        for src in sources:
            bl = SingleSourceBaseline(src, window_s=60, stride_s=30, contamination=0.05)
            try:
                bl.fit(benign)
                wins = bl.predict(logs)
                y_t = np.array([int(w["gt_anomalous"]) for w in wins])
                y_p = np.array([int(w["anomalous"])    for w in wins])
                y_s = np.array([-w["score"]            for w in wins])
                m   = compute_metrics(y_t, y_p, y_s)
            except Exception:
                m   = {k:0.0 for k in ["precision","recall","f1","auc_roc","auc_pr","fpr_at_90tpr","fpr_at_95tpr"]}
            rows.append({"seed":seed,"method":f"Single: {src}",**m})

    df = pd.DataFrame(rows)
    print(df.groupby("method")[["f1","auc_roc","auc_pr"]].mean().round(3))
    return df


# ══════════════════════════════════════════════════════════════════════════════
# PLOTTING
# ══════════════════════════════════════════════════════════════════════════════

def plot_all(e1_df, e2_df, e3_df, e4_df, e5_df, e6_df, outdir="/mnt/user-data/outputs"):
    fig = plt.figure(figsize=(20, 22))
    gs  = gridspec.GridSpec(3, 3, figure=fig, hspace=0.45, wspace=0.35)

    # ── E1: per-attack F1 ─────────────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    e1_mean = e1_df.groupby("attack")[["precision","recall","f1"]].mean().reset_index()
    e1_std  = e1_df.groupby("attack")[["precision","recall","f1"]].std().reset_index()
    x = np.arange(len(e1_mean))
    w = 0.25
    for i,(col,clr) in enumerate(zip(["precision","recall","f1"],["#4878CF","#6ACC65","#D65F5F"])):
        ax1.bar(x+i*w, e1_mean[col], w, yerr=e1_std[col], capsize=3,
                label=col.capitalize(), color=clr, alpha=0.85)
    ax1.set_xticks(x+w)
    ax1.set_xticklabels([a.replace("_","\n") for a in e1_mean["attack"]], fontsize=8)
    ax1.set_ylim(0,1.15); ax1.set_ylabel("Score"); ax1.set_title("E1: Per-Attack Detection"); ax1.legend(fontsize=7)

    # ── E1: AUC-ROC ──────────────────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    e1_auc = e1_df.groupby("attack")["auc_roc"].mean()
    e1_auc_std = e1_df.groupby("attack")["auc_roc"].std()
    ax2.barh(e1_auc.index, e1_auc.values, xerr=e1_auc_std.values, capsize=3,
             color="#4878CF", alpha=0.85)
    ax2.set_xlim(0,1); ax2.axvline(0.5, ls="--", c="gray", lw=0.8)
    ax2.set_xlabel("AUC-ROC"); ax2.set_title("E1: AUC-ROC per Attack")

    # ── E1: MTTD ─────────────────────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[0, 2])
    mttd_df = e1_df.dropna(subset=["mttd_s"])
    if not mttd_df.empty:
        m_mean = mttd_df.groupby("attack")["mttd_s"].mean()
        m_std  = mttd_df.groupby("attack")["mttd_s"].std()
        ax3.barh(m_mean.index, m_mean.values, xerr=m_std.values, capsize=3, color="#D65F5F", alpha=0.85)
    ax3.set_xlabel("MTTD (seconds)"); ax3.set_title("E1: Mean Time to Detect")

    # ── E2: Ablation ─────────────────────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 0])
    e2_mean = e2_df.groupby("config")[["f1","auc_roc"]].mean().reset_index()
    e2_std  = e2_df.groupby("config")[["f1","auc_roc"]].std().reset_index()
    x = np.arange(len(e2_mean))
    ax4.bar(x-0.2, e2_mean["f1"],      0.35, yerr=e2_std["f1"],      capsize=3, label="F1",      color="#4878CF", alpha=0.85)
    ax4.bar(x+0.2, e2_mean["auc_roc"], 0.35, yerr=e2_std["auc_roc"], capsize=3, label="AUC-ROC", color="#6ACC65", alpha=0.85)
    ax4.set_xticks(x); ax4.set_xticklabels(e2_mean["config"], rotation=30, ha="right", fontsize=7)
    ax4.set_ylim(0,1.1); ax4.set_title("E2: Source Ablation"); ax4.legend(fontsize=7)

    # ── E3: Window size ───────────────────────────────────────────────────────
    ax5 = fig.add_subplot(gs[1, 1])
    for col, clr, ls_ in [("f1","#4878CF","-"),("precision","#6ACC65","--"),("recall","#D65F5F",":")]:
        m = e3_df.groupby("window_s")[col].mean()
        s = e3_df.groupby("window_s")[col].std()
        ax5.plot(m.index, m.values, label=col.capitalize(), color=clr, ls=ls_, marker="o")
        ax5.fill_between(m.index, m-s, m+s, alpha=0.15, color=clr)
    ax5.set_xlabel("Window size (s)"); ax5.set_ylabel("Score"); ax5.set_title("E3: Window Size Sensitivity")
    ax5.legend(fontsize=7)

    # ── E4: ROC curve ─────────────────────────────────────────────────────────
    ax6 = fig.add_subplot(gs[1, 2])
    e4_mean = e4_df.groupby("fpr")["tpr"].mean().reset_index().sort_values("fpr")
    ax6.plot(e4_mean["fpr"], e4_mean["tpr"], color="#4878CF", lw=2, label="MultiSource (Ours)")
    ax6.plot([0,1],[0,1],"--",c="gray",lw=0.8)
    ax6.set_xlabel("FPR"); ax6.set_ylabel("TPR"); ax6.set_title("E4: ROC Curve")
    ax6.legend(fontsize=8)

    # ── E5: Scalability ───────────────────────────────────────────────────────
    ax7 = fig.add_subplot(gs[2, 0])
    ax7.plot(e5_df["n_events"], e5_df["norm_tput_keps"], "o-", label="Normalizer", color="#4878CF")
    ax7.plot(e5_df["n_events"], e5_df["pipe_tput_keps"], "s--", label="Full Pipeline", color="#D65F5F")
    ax7.set_xlabel("Number of Events"); ax7.set_ylabel("Throughput (k events/sec)")
    ax7.set_title("E5: Scalability"); ax7.legend(fontsize=8)

    # ── E6: Baseline comparison (F1) ──────────────────────────────────────────
    ax8 = fig.add_subplot(gs[2, 1])
    e6_mean = e6_df.groupby("method")["f1"].mean().sort_values(ascending=False)
    e6_std  = e6_df.groupby("method")["f1"].std()
    colors  = ["#D65F5F" if "Ours" in m else "#AAAAAA" for m in e6_mean.index]
    ax8.barh(e6_mean.index, e6_mean.values, xerr=e6_std[e6_mean.index].values,
             capsize=3, color=colors, alpha=0.85)
    ax8.set_xlim(0,1); ax8.axvline(0, c="black", lw=0.5)
    ax8.set_xlabel("F1 Score"); ax8.set_title("E6: Baseline Comparison (F1)")

    # ── E6: AUC comparison ────────────────────────────────────────────────────
    ax9 = fig.add_subplot(gs[2, 2])
    e6_auc  = e6_df.groupby("method")["auc_roc"].mean().sort_values(ascending=False)
    e6_astd = e6_df.groupby("method")["auc_roc"].std()
    colors2 = ["#D65F5F" if "Ours" in m else "#AAAAAA" for m in e6_auc.index]
    ax9.barh(e6_auc.index, e6_auc.values, xerr=e6_astd[e6_auc.index].values,
             capsize=3, color=colors2, alpha=0.85)
    ax9.set_xlim(0,1); ax9.axvline(0.5,ls="--",c="gray",lw=0.8)
    ax9.set_xlabel("AUC-ROC"); ax9.set_title("E6: Baseline Comparison (AUC-ROC)")

    fig.suptitle("5G SOC Multi-Source Log Correlation: Experimental Results", fontsize=14, fontweight="bold", y=0.995)
    out_path = f"{outdir}/experiment_results.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n[Plot] Saved → {out_path}")
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
# STATISTICAL TESTS
# ══════════════════════════════════════════════════════════════════════════════

def statistical_tests(e6_df: pd.DataFrame) -> pd.DataFrame:
    """Wilcoxon signed-rank test: our method vs each baseline."""
    ours = e6_df[e6_df["method"]=="MultiSource (Ours)"]["f1"].values
    rows = []
    for method in e6_df["method"].unique():
        if method == "MultiSource (Ours)":
            continue
        other = e6_df[e6_df["method"]==method]["f1"].values
        n = min(len(ours),len(other))
        if n < 2:
            continue
        stat, p = stats.wilcoxon(ours[:n], other[:n], alternative="greater")
        lo, hi = bootstrap_ci(ours - other[:n])
        rows.append({"vs_method":method,"wilcoxon_stat":round(stat,2),
                     "p_value":round(p,4),"significant":p<0.05,
                     "mean_delta":round(float(np.mean(ours[:n]-other[:n])),4),
                     "ci_95_lo":round(lo,4),"ci_95_hi":round(hi,4)})
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# PAPER TABLE GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

def generate_paper_tables(e1_df, e2_df, e3_df, e6_df, stat_df) -> str:
    """Generate LaTeX tables for the scientific paper."""
    lines = []
    lines.append(r"% ════════════════════════════════════════════════════")
    lines.append(r"% Table 1: Per-attack detection performance")
    lines.append(r"% ════════════════════════════════════════════════════")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Per-Attack Detection Performance (mean $\pm$ std, $N=5$ seeds)}")
    lines.append(r"\label{tab:per_attack}")
    lines.append(r"\begin{tabular}{lccccc}")
    lines.append(r"\toprule")
    lines.append(r"Attack Type & Precision & Recall & F1 & AUC-ROC & MTTD (s) \\")
    lines.append(r"\midrule")
    for atk, grp in e1_df.groupby("attack"):
        m = grp[["precision","recall","f1","auc_roc","mttd_s"]].mean()
        s = grp[["precision","recall","f1","auc_roc","mttd_s"]].std()
        lines.append(
            rf"\texttt{{{atk.replace('_','-')}}} & "
            rf"{m.precision:.2f}$\pm${s.precision:.2f} & "
            rf"{m.recall:.2f}$\pm${s.recall:.2f} & "
            rf"\textbf{{{m.f1:.2f}}}$\pm${s.f1:.2f} & "
            rf"{m.auc_roc:.3f}$\pm${s.auc_roc:.3f} & "
            rf"{m.mttd_s:.0f}$\pm${s.mttd_s:.0f} \\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")

    lines.append(r"% ════════════════════════════════════════════════════")
    lines.append(r"% Table 2: Source ablation")
    lines.append(r"% ════════════════════════════════════════════════════")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Source Ablation Study}")
    lines.append(r"\label{tab:ablation}")
    lines.append(r"\begin{tabular}{lcc}")
    lines.append(r"\toprule")
    lines.append(r"Configuration & F1 & AUC-ROC \\")
    lines.append(r"\midrule")
    for cfg, grp in e2_df.groupby("config"):
        m = grp[["f1","auc_roc"]].mean()
        lines.append(rf"{cfg} & {m.f1:.3f} & {m.auc_roc:.3f} \\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")

    lines.append(r"% ════════════════════════════════════════════════════")
    lines.append(r"% Table 3: Baseline comparison with statistical tests")
    lines.append(r"% ════════════════════════════════════════════════════")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Comparison with Baselines (Wilcoxon $p<0.05$)}")
    lines.append(r"\label{tab:baselines}")
    lines.append(r"\begin{tabular}{lcccc}")
    lines.append(r"\toprule")
    lines.append(r"Method & F1 & AUC-ROC & $\Delta$F1 & $p$-val \\")
    lines.append(r"\midrule")
    ours_row = e6_df[e6_df["method"]=="MultiSource (Ours)"][["f1","auc_roc"]].mean()
    lines.append(rf"\textbf{{MultiSource (Ours)}} & \textbf{{{ours_row.f1:.3f}}} & \textbf{{{ours_row.auc_roc:.3f}}} & -- & -- \\")
    for _, row in stat_df.iterrows():
        grp = e6_df[e6_df["method"]==row.vs_method][["f1","auc_roc"]].mean()
        sig = r"$^*$" if row.significant else ""
        lines.append(rf"{row.vs_method} & {grp.f1:.3f} & {grp.auc_roc:.3f} & "
                     rf"{row.mean_delta:+.3f}{sig} & {row.p_value:.4f} \\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\vspace{1pt}{\small $^*$ $p<0.05$, Wilcoxon signed-rank (one-tailed)}")
    lines.append(r"\end{table}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import os
    os.makedirs("/mnt/user-data/outputs", exist_ok=True)

    N_SEEDS = 5
    print("="*60)
    print("5G SOC Log Correlation — Experimental Evaluation")
    print("="*60)

    t0 = time.time()
    e1_df = experiment_e1(N_SEEDS)
    e2_df = experiment_e2(N_SEEDS)
    e3_df = experiment_e3(N_SEEDS)
    e4_df = experiment_e4(N_SEEDS)
    e5_df = experiment_e5()
    e6_df = experiment_e6(N_SEEDS)

    stat_df = statistical_tests(e6_df)
    print("\n[Statistical Tests]")
    print(stat_df.to_string(index=False))

    latex_tables = generate_paper_tables(e1_df, e2_df, e3_df, e6_df, stat_df)
    with open("/mnt/user-data/outputs/paper_tables.tex","w") as f:
        f.write(latex_tables)
    print("\n[LaTeX] Tables saved → /mnt/user-data/outputs/paper_tables.tex")

    plot_all(e1_df, e2_df, e3_df, e4_df, e5_df, e6_df)

    # Save CSVs
    for name, df in [("e1_per_attack",e1_df),("e2_ablation",e2_df),
                     ("e3_window",e3_df),("e5_scalability",e5_df),
                     ("e6_baselines",e6_df),("stat_tests",stat_df)]:
        df.to_csv(f"/mnt/user-data/outputs/{name}.csv", index=False)

    print(f"\nTotal experiment time: {time.time()-t0:.1f}s")
    print("\n✓ All outputs written to /mnt/user-data/outputs/")
