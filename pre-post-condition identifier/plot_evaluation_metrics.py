"""
Plot evaluation metrics (aggregate) produced by compute_evaluation_metrics.py
Saves PDF and JPEG in the same folder.
"""
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


def load_metrics(path):
    with open(path, 'r') as f:
        return json.load(f)


def plot_metrics(metrics_path, out_pdf, out_jpg):
    m = load_metrics(metrics_path)
    agg = m['aggregate']

    components = ['keywords', 'ttps', 'preconditions', 'postconditions']
    precs = [agg[c]['prec'] for c in components]
    recs = [agg[c]['rec'] for c in components]
    f1s = [agg[c]['f1'] for c in components]

    x = np.arange(len(components))
    width = 0.25

    sns.set_theme(style='whitegrid')
    fig, ax = plt.subplots(figsize=(8, 4.5))

    ax.bar(x - width, precs, width, label='Precision', color='#4C72B0')
    ax.bar(x, recs, width, label='Recall', color='#55A868')
    ax.bar(x + width, f1s, width, label='F1', color='#C44E52')

    ax.set_xticks(x)
    ax.set_xticklabels(['Keywords', 'TTPs', 'Pre-conds', 'Post-conds'])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel('Score')
    ax.set_title('Aggregate Evaluation Metrics')
    ax.legend(frameon=False)

    # Add MAP values as text
    map_keywords = agg.get('map_keywords', 0.0)
    map_ttps = agg.get('map_ttps', 0.0)
    text = f"MAP@K (Keywords): {map_keywords:.3f}\nMAP@K (TTPs): {map_ttps:.3f}"
    ax.text(1.02, 0.5, text, transform=ax.transAxes, fontsize=9,
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.tight_layout()
    out_pdf = Path(out_pdf)
    out_jpg = Path(out_jpg)
    fig.savefig(out_pdf, dpi=300, bbox_inches='tight')
    fig.savefig(out_jpg, dpi=300, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    metrics_path = Path('/home/ubuntu/5GSPP/pre-post-condition identifier/evaluation_metrics.json')
    out_pdf = Path('/home/ubuntu/5GSPP/pre-post-condition identifier/evaluation_metrics_figure.pdf')
    out_jpg = Path('/home/ubuntu/5GSPP/pre-post-condition identifier/evaluation_metrics_figure.jpg')
    plot_metrics(metrics_path, out_pdf, out_jpg)
    print(f"Saved: {out_pdf}\nSaved: {out_jpg}")