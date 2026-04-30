"""
Plot experimental results for pre- and post-conditions.

Generates a two-panel figure:
 - Left: grouped bar chart of counts per breach (keywords, TTPs, pre/post-conditions, connections)
 - Right: line chart of average pre/post-condition confidences per breach

Saves outputs as PDF and JPEG suitable for inclusion in a paper.
"""
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


def load_results(path):
    with open(path, 'r') as f:
        return json.load(f)


def build_dataframe(stats):
    # Stats are lists per breach; build a small table-like dict
    n = len(stats['keywords_per_breach'])
    data = {
        'breach': [f'B{i+1}' for i in range(n)],
        'keywords': stats['keywords_per_breach'],
        'ttps': stats['ttps_per_breach'],
        'preconditions': stats['preconditions_per_breach'],
        'postconditions': stats['postconditions_per_breach'],
        'connections': stats['connections_per_breach'],
        'avg_pre_conf': stats.get('avg_precondition_confidence', [0]*n),
        'avg_post_conf': stats.get('avg_postcondition_confidence', [0]*n),
    }
    return data


def plot_pre_post(data, out_pdf, out_jpg):
    sns.set_theme(style='whitegrid')
    plt.rcParams.update({'font.size': 10})

    breaches = data['breach']
    x = np.arange(len(breaches))
    width = 0.15

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), gridspec_kw={'width_ratios': [1.2, 1]})

    ax = axes[0]
    # Grouped bars: keywords, ttps, pre, post, connections
    ax.bar(x - 2*width, data['keywords'], width, label='Keywords', color='#4C72B0')
    ax.bar(x - width, data['ttps'], width, label='TTPs', color='#55A868')
    ax.bar(x, data['preconditions'], width, label='Pre-conditions', color='#C44E52')
    ax.bar(x + width, data['postconditions'], width, label='Post-conditions', color='#8172B2')
    ax.bar(x + 2*width, data['connections'], width, label='Connections', color='#CCB974')

    ax.set_xticks(x)
    ax.set_xticklabels(breaches)
    ax.set_xlabel('Breach (sample)')
    ax.set_ylabel('Count')
    ax.set_title('Per-breach Condition Counts')
    ax.legend(frameon=False, ncol=2, fontsize=8)

    # Annotate top of bars for pre/post only (optional)
    def annotate_bars(bars, fmt='{:.0f}'):
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.annotate(fmt.format(h), xy=(bar.get_x() + bar.get_width()/2, h),
                            xytext=(0, 4), textcoords='offset points', ha='center', va='bottom', fontsize=7)

    # grab patches for annotation (preconditions at x, post at x+width)
    # skip heavy annotations to keep figure clean

    # Right panel: confidences
    ax2 = axes[1]
    ax2.plot(breaches, data['avg_pre_conf'], marker='o', linestyle='-', color='#C44E52', label='Avg Pre-condition Confidence')
    ax2.plot(breaches, data['avg_post_conf'], marker='s', linestyle='--', color='#8172B2', label='Avg Post-condition Confidence')
    ax2.set_ylim(0, 1)
    ax2.set_ylabel('Average Confidence')
    ax2.set_xlabel('Breach (sample)')
    ax2.set_title('Condition Confidence Trends')
    ax2.legend(frameon=False, fontsize=9)

    # Add grid and tighten layout
    for a in axes:
        a.grid(True, axis='y', linestyle=':', linewidth=0.6, alpha=0.8)

    plt.tight_layout()

    # Save outputs
    out_pdf = Path(out_pdf)
    out_jpg = Path(out_jpg)
    fig.savefig(out_pdf, dpi=300, bbox_inches='tight')
    fig.savefig(out_jpg, dpi=300, bbox_inches='tight')
    plt.close(fig)


def main():
    base = Path('/home/ubuntu/experimental_results.json')
    if not base.exists():
        raise FileNotFoundError(f"Expected results JSON at {base}")

    results = load_results(base)
    stats = results['statistics']
    data = build_dataframe(stats)

    out_dir = Path('/home/ubuntu/5GSPP/pre-post-condition identifier')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_dir / 'pre_post_conditions_figure.pdf'
    out_jpg = out_dir / 'pre_post_conditions_figure.jpg'

    plot_pre_post(data, out_pdf, out_jpg)

    print(f"Saved figure: {out_pdf}\nSaved figure: {out_jpg}")


if __name__ == '__main__':
    main()
