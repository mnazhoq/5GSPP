"""
Compute evaluation metrics for keyword extraction, TTP mapping, and
pre/post-condition identification.

Usage:
  python compute_evaluation_metrics.py --pred /path/to/experimental_results.json --gold /path/to/gold_labels.json --out /path/to/output_metrics.json

Gold format (JSON): list of breach records, each record must include:
  {
    "breach_id": "B1",
    "keywords": ["credential", "bypass", ...],
    "ttps": ["T1563.002", "T15498", ...],
    "preconditions": ["user credential compromise", ...],
    "postconditions": ["privilege escalation", ...]
  }

Predictions are expected in the same structure as `experimental_results.json`
produced by the analysis pipeline (keys: `results` with per-breach dicts).
"""
import json
import argparse
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Tuple, Dict, Set


def normalize_text(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def set_metrics(pred: Set[str], gold: Set[str]) -> Tuple[float, float, float]:
    if not pred and not gold:
        return 1.0, 1.0, 1.0
    tp = len(pred & gold)
    prec = tp / len(pred) if pred else 0.0
    rec = tp / len(gold) if gold else 0.0
    if prec + rec == 0:
        f1 = 0.0
    else:
        f1 = 2 * prec * rec / (prec + rec)
    return prec, rec, f1


def precision_at_k(pred_list: List[str], gold_set: Set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    pred_k = pred_list[:k]
    if not pred_k:
        return 0.0
    hits = sum(1 for p in pred_k if p in gold_set)
    return hits / len(pred_k)


def average_precision_at_k(pred_list: List[str], gold_set: Set[str], k: int) -> float:
    # simple AP@k: average of precision@i for each correct hit up to k
    hits = 0
    sum_prec = 0.0
    for i, p in enumerate(pred_list[:k], start=1):
        if p in gold_set:
            hits += 1
            sum_prec += hits / i
    denom = min(len(gold_set), k)
    return sum_prec / denom if denom > 0 else 0.0


def fuzzy_match_count(preds: List[str], golds: List[str], threshold: float = 0.6) -> int:
    # greedy matching: each gold can be matched once
    used = set()
    matches = 0
    normalized_golds = [normalize_text(g) for g in golds]
    for p in preds:
        npred = normalize_text(p)
        best_idx = -1
        best_score = 0.0
        for j, g in enumerate(normalized_golds):
            if j in used:
                continue
            score = SequenceMatcher(None, npred, g).ratio()
            if score > best_score:
                best_score = score
                best_idx = j
        if best_score >= threshold and best_idx >= 0:
            matches += 1
            used.add(best_idx)
    return matches


def evaluate(predictions: Dict, gold: List[Dict], top_k: int = 5) -> Dict:
    # Build mapping by breach id for gold
    gold_map = {g['breach_id']: g for g in gold}

    per_breach = {}
    totals = {
        'keywords_tp': 0, 'keywords_pred': 0, 'keywords_gold': 0,
        'ttps_tp': 0, 'ttps_pred': 0, 'ttps_gold': 0,
        'pre_tp': 0, 'pre_pred': 0, 'pre_gold': 0,
        'post_tp': 0, 'post_pred': 0, 'post_gold': 0,
        'map_ttps_sum': 0.0, 'map_keywords_sum': 0.0,
        'n': 0
    }

    for r in predictions.get('results', []):
        bid = r.get('breach_id') or r.get('control_breach', '')[:30]
        gold_rec = gold_map.get(bid)
        if not gold_rec:
            # try numeric index fallback if ids differ
            continue

        # Keywords: predicted are list of dicts with 'term'
        pred_keywords = [normalize_text(k['term']) for k in r.get('step_a_keywords', [])]
        gold_keywords = [normalize_text(k) for k in gold_rec.get('keywords', [])]
        pk_set = set(pred_keywords)
        gk_set = set(gold_keywords)
        kp, kr, kf = set_metrics(pk_set, gk_set)

        # Keywords MAP@k
        map_k = average_precision_at_k(pred_keywords, gk_set, top_k)

        # TTPs: predicted list of dicts with 'ttp_id'
        pred_ttps = [t.get('ttp_id') for t in sorted(r.get('step_b_ttps', []), key=lambda x: x.get('similarity', 0), reverse=True)]
        gold_ttps = [t for t in gold_rec.get('ttps', [])]
        pt_set = set(pred_ttps)
        gt_set = set(gold_ttps)
        tp_p, tp_r, tp_f = set_metrics(pt_set, gt_set)
        map_ttp = average_precision_at_k(pred_ttps, gt_set, top_k)

        # Pre/post conditions: use fuzzy matching on descriptions
        pred_pres = [p.get('description', '') for p in r.get('step_c_preconditions', [])]
        gold_pres = gold_rec.get('preconditions', [])
        matched_pre = fuzzy_match_count(pred_pres, gold_pres)
        pre_prec = matched_pre / len(pred_pres) if pred_pres else 0.0
        pre_rec = matched_pre / len(gold_pres) if gold_pres else 0.0
        pre_f1 = (2 * pre_prec * pre_rec / (pre_prec + pre_rec)) if (pre_prec + pre_rec) > 0 else 0.0

        pred_posts = [p.get('description', '') for p in r.get('step_c_postconditions', [])]
        gold_posts = gold_rec.get('postconditions', [])
        matched_post = fuzzy_match_count(pred_posts, gold_posts)
        post_prec = matched_post / len(pred_posts) if pred_posts else 0.0
        post_rec = matched_post / len(gold_posts) if gold_posts else 0.0
        post_f1 = (2 * post_prec * post_rec / (post_prec + post_rec)) if (post_prec + post_rec) > 0 else 0.0

        per_breach[bid] = {
            'keywords': {'prec': kp, 'rec': kr, 'f1': kf, 'map@k': map_k},
            'ttps': {'prec': tp_p, 'rec': tp_r, 'f1': tp_f, 'map@k': map_ttp},
            'preconditions': {'prec': pre_prec, 'rec': pre_rec, 'f1': pre_f1, 'matched': matched_pre},
            'postconditions': {'prec': post_prec, 'rec': post_rec, 'f1': post_f1, 'matched': matched_post}
        }

        # Totals
        totals['keywords_tp'] += len(pk_set & gk_set)
        totals['keywords_pred'] += len(pk_set)
        totals['keywords_gold'] += len(gk_set)

        totals['ttps_tp'] += len(pt_set & gt_set)
        totals['ttps_pred'] += len(pt_set)
        totals['ttps_gold'] += len(gt_set)

        totals['pre_tp'] += matched_pre
        totals['pre_pred'] += len(pred_pres)
        totals['pre_gold'] += len(gold_pres)

        totals['post_tp'] += matched_post
        totals['post_pred'] += len(pred_posts)
        totals['post_gold'] += len(gold_posts)

        totals['map_ttps_sum'] += map_ttp
        totals['map_keywords_sum'] += map_k
        totals['n'] += 1

    # Aggregate metrics
    def agg(tp, pred, gold):
        prec = tp / pred if pred else 0.0
        rec = tp / gold if gold else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        return {'prec': prec, 'rec': rec, 'f1': f1}

    agg_keywords = agg(totals['keywords_tp'], totals['keywords_pred'], totals['keywords_gold'])
    agg_ttps = agg(totals['ttps_tp'], totals['ttps_pred'], totals['ttps_gold'])
    agg_pre = agg(totals['pre_tp'], totals['pre_pred'], totals['pre_gold'])
    agg_post = agg(totals['post_tp'], totals['post_pred'], totals['post_gold'])

    map_keywords = totals['map_keywords_sum'] / totals['n'] if totals['n'] else 0.0
    map_ttps = totals['map_ttps_sum'] / totals['n'] if totals['n'] else 0.0

    return {
        'per_breach': per_breach,
        'aggregate': {
            'keywords': agg_keywords,
            'ttps': agg_ttps,
            'preconditions': agg_pre,
            'postconditions': agg_post,
            'map_keywords': map_keywords,
            'map_ttps': map_ttps,
            'evaluated_breaches': totals['n']
        }
    }


def load_json(path: Path):
    with open(path, 'r') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pred', required=True, help='Predictions JSON (experimental_results.json)')
    parser.add_argument('--gold', required=True, help='Gold labels JSON (see script header)')
    parser.add_argument('--out', default='evaluation_metrics.json', help='Output JSON for metrics')
    parser.add_argument('--k', type=int, default=5, help='Top-K for MAP/P@K')
    args = parser.parse_args()

    pred = load_json(Path(args.pred))
    gold = load_json(Path(args.gold))

    metrics = evaluate(pred, gold, top_k=args.k)

    with open(args.out, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"Saved evaluation metrics to {args.out}")


if __name__ == '__main__':
    main()
