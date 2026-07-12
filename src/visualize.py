import os
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)

SOURCE_NOTE = "Source: Open Brewery DB API"


def _us_microbrewery_bar(csv_path, out_path):
    df = pd.read_csv(csv_path)
    plt.figure(figsize=(10, 6))

    # Highlight the leader, mute the rest.
    colors = ['#1f77b4'] + ['#a6cee3'] * (len(df) - 1)
    ax = sns.barplot(data=df, x='microbrewery_count', y='state_province',
                     hue='state_province', palette=colors, legend=False, orient='h')

    # hue puts each bar in its own container, so label them all.
    for container in ax.containers:
        ax.bar_label(container, padding=5, fmt='%.0f', color='#333333', fontweight='bold')

    plt.title('Top 5 US States by Microbrewery Count', fontsize=14, pad=15, fontweight='bold')
    plt.xlabel('Number of Microbreweries')
    plt.ylabel('')
    plt.figtext(0.99, 0.01, SOURCE_NOTE, ha="right", fontsize=9, color='gray')
    ax.xaxis.grid(False)
    ax.yaxis.grid(False)
    sns.despine(left=True, bottom=True)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()


def _korea_types_donut(csv_path, out_path):
    df = pd.read_csv(csv_path)
    total = df['count'].sum()

    def label(pct):
        absolute = int(np.round(pct / 100.0 * total))
        return f"{absolute}\n({pct:.1f}%)"

    plt.figure(figsize=(8, 8))
    plt.pie(
        df['count'],
        labels=df['brewery_type'].str.title(),
        autopct=lambda pct: label(pct),
        colors=['#ff7f0e', '#1f77b4'],
        startangle=90,
        pctdistance=0.8,     # centre the labels within the ring
        labeldistance=1.08,
        wedgeprops=dict(width=0.4, edgecolor='w', linewidth=2),
        textprops={'fontsize': 12, 'fontweight': 'bold'},
    )
    plt.title('South Korea Brewery Types', fontsize=16, fontweight='bold')
    plt.suptitle(f"n = {total} breweries. Mostly brewpubs.", fontsize=11, color='dimgray', y=0.88)
    plt.figtext(0.99, 0.01, SOURCE_NOTE, ha="right", fontsize=9, color='gray')
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()


def _korea_phone_heatmap(csv_path, out_path):
    df = pd.read_csv(csv_path)
    matrix = df.pivot_table(index='state_province', columns='phone_type',
                            values='frequency', aggfunc='sum').fillna(0)

    # Rows by total descending.
    matrix = matrix.loc[matrix.sum(axis=1).sort_values(ascending=False).index]

    # Columns grouped geographic -> tech -> other (only those present).
    order = ['Seoul (Capital)', 'Provincial/Geographic', 'Mobile', 'VoIP/Internet Phone',
             'Personal/Relay', 'National Service', 'Premium-Rate', 'Toll-Free',
             'Other/Invalid', 'Unknown/Null']
    matrix = matrix[[c for c in order if c in matrix.columns]]

    plt.figure(figsize=(12, 7))
    sns.heatmap(matrix, annot=True, fmt='g', cmap='Blues', linewidths=1,
                linecolor='white', cbar_kws={'label': 'Brewery count'})

    fig = plt.gcf()
    fig.suptitle('South Korean Brewery Phone Patterns by Province',
                 fontsize=14, fontweight='bold', y=0.98)
    fig.text(0.5, 0.925,
             "Small sample (n=61); provinces with 1-2 sites are not statistically robust.",
             ha='center', fontsize=10, color='firebrick')
    plt.xlabel('Phone type', fontweight='bold', labelpad=10)
    plt.ylabel('Province', fontweight='bold', labelpad=10)
    plt.xticks(rotation=30, ha='right')
    plt.figtext(0.99, 0.01, SOURCE_NOTE, ha="right", fontsize=9, color='gray')
    plt.tight_layout(rect=[0, 0, 1, 0.90])
    plt.savefig(out_path, dpi=300)
    plt.close()


def run_visualization_pipeline(input_dir: str = "data/analytics_zone",
                               output_dir: str = "data/analytics_zone/visualizations"):
    """Build the three charts from the analytics CSVs."""
    os.makedirs(output_dir, exist_ok=True)
    sns.set_theme(style="whitegrid")

    charts = [
        ("top_us_micro_states.csv", "01_us_microbreweries_bar.png", _us_microbrewery_bar),
        ("korea_brewery_types.csv", "02_korea_brewery_types_donut.png", _korea_types_donut),
        ("korea_phone_by_province.csv", "03_korea_phone_heatmap.png", _korea_phone_heatmap),
    ]
    for csv_name, png_name, builder in charts:
        csv_path = os.path.join(input_dir, csv_name)
        if not os.path.exists(csv_path):
            logger.warning(f"Missing {csv_path}, skipping {png_name}")
            continue
        builder(csv_path, os.path.join(output_dir, png_name))
        logger.info(f"Wrote {png_name}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%m/%d/%Y %H:%M:%S')
    run_visualization_pipeline()
