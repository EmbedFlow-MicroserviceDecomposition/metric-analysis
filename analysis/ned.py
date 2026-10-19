# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     formats: ipynb,py:percent
#     notebook_metadata_filter: -all,jupytext,kernelspec
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.6
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Non-Extreme Distribution (NED) Analysis across Microservice Architectures
#
# This notebook directly ingests evaluation results from the `outputs/` directory to analyze
# decomposition quality and size balance across open-source microservice systems.
#
# ### Metrics Evaluated:
# 1. **Fixed-Bounds NED (`ned_absolute`)**:
#    $$\text{NED}_{\text{fixed}} = 1 - \frac{\sum_{s \in \text{Extreme}} |s|}{\text{Total Classes}}$$
#    where a service is extreme if $|s| < \text{lo}$ (default: 5) or $|s| > \text{hi}$ (default: 20).
#
# 2. **Relative-Bounds NED (`ned_relative`)**:
#    $$\text{NED}_{\text{relative}} = \frac{\sum_{s \in \text{Balanced}} |s|}{\text{Total Classes}}$$
#    where a service is balanced if its size falls within $[(1-\epsilon)\bar{s}, (1+\epsilon)\bar{s}]$ around the system's average service size $\bar{s}$.

# %%
import json
import math
import os
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd
import seaborn as sns

# Visual formatting settings
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams["figure.figsize"] = (10, 6)
plt.rcParams["figure.dpi"] = 120
plt.rcParams["font.sans-serif"] = "DejaVu Sans"

PROJECT_ROOT = Path(__file__).resolve().parent.parent if "__file__" in globals() else Path(".").resolve()
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
MANIFEST_PATH = PROJECT_ROOT / "codebases" / "microservices" / "microservices.json"

print(f"Project root: {PROJECT_ROOT}")
print(f"Outputs dir:  {OUTPUTS_DIR}")
print(f"Manifest:     {MANIFEST_PATH}")

# %% [markdown]
# ## 1. Ingesting Evaluation Outputs from `outputs/`
#
# We scan each system directory in `outputs/` (e.g. `outputs/MS001/`), load `ned_score.json` and
# `output.json`, and enrich the records with metadata from `microservices.json`.

# %%
def load_analysis_dataset(outputs_dir: Path, manifest_path: Path) -> pd.DataFrame:
    """Ingests evaluation results directly from outputs/ into a structured pandas DataFrame."""
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    records = []
    
    for sys_dir in sorted(outputs_dir.iterdir()):
        if not sys_dir.is_dir() or not sys_dir.name.startswith("MS"):
            continue
            
        sys_id = sys_dir.name
        score_file = sys_dir / "ned_score.json"
        output_file = sys_dir / "output.json"
        
        if not score_file.exists():
            continue
            
        try:
            with open(score_file, "r", encoding="utf-8") as f:
                score_data = json.load(f)
        except Exception as e:
            print(f"Warning: could not parse {score_file}: {e}")
            continue

        meta = score_data.get("metadata", {})
        bounds = score_data.get("bounds", {})
        ms_scores = score_data.get("microservice_scores", {})
        sizes = meta.get("service_sizes", {})
        
        size_values = list(sizes.values()) if sizes else []
        service_count = meta.get("service_count", len(sizes))
        total_classes = meta.get("total_classes", sum(size_values) if size_values else 0)
        
        lo = bounds.get("lo", 5)
        hi = bounds.get("hi", 20)
        eps = bounds.get("eps", 0.5)
        
        score_abs = score_data.get("score_absolute", score_data.get("score", np.nan))
        score_rel = score_data.get("score_relative", np.nan)
        
        # Manifest metadata
        sys_info = manifest.get(sys_id, {})
        sys_name = sys_info.get("name", sys_id)
        language = sys_info.get("language", "Unknown")
        
        # Granular service distribution breakdown
        if size_values and total_classes > 0:
            avg_size = total_classes / service_count
            min_size = min(size_values)
            max_size = max(size_values)
            std_size = float(np.std(size_values)) if len(size_values) > 1 else 0.0
            size_cv = std_size / avg_size if avg_size > 0 else 0.0
            
            tiny_count = sum(1 for s in size_values if s < lo)
            god_count = sum(1 for s in size_values if s > hi)
            balanced_abs_count = sum(1 for s in size_values if lo <= s <= hi)
            
            rel_lo = math.floor(avg_size * (1.0 - eps))
            rel_hi = math.ceil(avg_size * (1.0 + eps))
            balanced_rel_count = sum(1 for s in size_values if rel_lo <= s <= rel_hi)
        else:
            avg_size = 0.0
            min_size = 0
            max_size = 0
            std_size = 0.0
            size_cv = 0.0
            tiny_count = 0
            god_count = 0
            balanced_abs_count = 0
            balanced_rel_count = 0
            rel_lo = 0
            rel_hi = 0

        records.append({
            "system_id": sys_id,
            "system_name": sys_name,
            "language": language,
            "ned_absolute": round(float(score_abs), 4) if pd.notnull(score_abs) else np.nan,
            "ned_relative": round(float(score_rel), 4) if pd.notnull(score_rel) else np.nan,
            "service_count": service_count,
            "total_classes": total_classes,
            "avg_service_size": round(avg_size, 2),
            "std_service_size": round(std_size, 2),
            "size_cv": round(size_cv, 2),
            "min_service_size": min_size,
            "max_service_size": max_size,
            "tiny_services_count": tiny_count,
            "god_services_count": god_count,
            "balanced_services_abs": balanced_abs_count,
            "balanced_services_rel": balanced_rel_count,
            "bound_lo": lo,
            "bound_hi": hi,
            "bound_rel_lo": rel_lo,
            "bound_rel_hi": rel_hi,
            "has_classes": total_classes > 0,
            "is_application": language not in ["Infrastructure", "Documentation"],
            "category": "Application" if language not in ["Infrastructure", "Documentation"] else language
        })
        
    df = pd.DataFrame(records)
    # Sort naturally by System ID number
    df["sys_num"] = df["system_id"].apply(lambda x: int(x[2:]) if x.startswith("MS") and x[2:].isdigit() else 9999)
    df = df.sort_values("sys_num").drop(columns=["sys_num"]).reset_index(drop=True)
    return df

df = load_analysis_dataset(OUTPUTS_DIR, MANIFEST_PATH)
print(f"Loaded {len(df)} systems from outputs/. Systems with extracted classes: {df['has_classes'].sum()}")
df.head(10)

# %% [markdown]
# ## 2. Descriptive Statistical Summary (Segregated by System Nature)
#
# Summary statistics across all evaluated microservice architectures with extracted classes,
# segregated by Application Systems vs. Infrastructure/Deployment Orchestrators.

# %%
df_valid = df[df["has_classes"]].copy()
lang_counts = df_valid["language"].value_counts()
major_langs = lang_counts[lang_counts >= 3].index.tolist()
df_valid["lang_group"] = df_valid["language"].apply(lambda l: l if l in major_langs else "Other")
df_apps = df_valid[df_valid["is_application"]].copy()

stats_cols = [
    "ned_absolute",
    "ned_relative",
    "service_count",
    "total_classes",
    "avg_service_size",
    "size_cv",
    "tiny_services_count",
    "god_services_count"
]

summary_stats = df_valid[stats_cols].describe().T
summary_stats["median"] = df_valid[stats_cols].median()
summary_stats = summary_stats[["count", "mean", "std", "min", "25%", "median", "75%", "max"]]

summary_stats_apps = df_apps[stats_cols].describe().T
summary_stats_apps["median"] = df_apps[stats_cols].median()
summary_stats_apps = summary_stats_apps[["count", "mean", "std", "min", "25%", "median", "75%", "max"]]

segregation_comparison = df_valid.groupby("category").agg(
    systems_count=("system_id", "count"),
    mean_ned_abs=("ned_absolute", "mean"),
    median_ned_abs=("ned_absolute", "median"),
    mean_ned_rel=("ned_relative", "mean"),
    median_ned_rel=("ned_relative", "median"),
    mean_services=("service_count", "mean"),
    mean_classes=("total_classes", "mean")
).reset_index()

print("=== GLOBAL DESCRIPTIVE STATISTICS (ALL SYSTEMS, n={}) ===".format(len(df_valid)))
print(summary_stats.round(3))

print("\n=== APPLICATION SYSTEMS STATISTICS (FILTERED, n={}) ===".format(len(df_apps)))
print(summary_stats_apps.round(3))

print("\n=== SEGREGATION COMPARISON: APPLICATION VS INFRASTRUCTURE ===")
print(segregation_comparison.round(3).to_string(index=False))

# %% [markdown]
# ## 3. Distribution Comparison: Fixed vs. Relative NED
#
# Comparing the distribution of Fixed-Bounds NED (`ned_absolute`) and Relative-Bounds NED (`ned_relative`).
# - Fixed NED penalizes systems that depart from the global [5, 20] range.
# - Relative NED evaluates balance with respect to the system's own mean service size.

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot 1: Histogram & KDE of Fixed vs Relative
sns.histplot(
    df_valid["ned_absolute"],
    kde=True,
    color="steelblue",
    label="Fixed NED (lo=5, hi=20)",
    bins=15,
    ax=axes[0],
    stat="density"
)
sns.histplot(
    df_valid["ned_relative"],
    kde=True,
    color="darkorange",
    label="Relative NED (eps=0.5)",
    bins=15,
    ax=axes[0],
    stat="density",
    alpha=0.6
)
axes[0].set_title("Density Distribution: Fixed vs. Relative NED", fontsize=13, fontweight="bold")
axes[0].set_xlabel("NED Score [0.0 - 1.0]")
axes[0].set_ylabel("Density")
axes[0].legend()

# Plot 2: Boxplot Comparison
sns.boxplot(
    data=df_valid[["ned_absolute", "ned_relative"]],
    palette=["steelblue", "darkorange"],
    ax=axes[1],
    width=0.4
)
axes[1].set_title("Score Spread (Boxplot)", fontsize=13, fontweight="bold")
axes[1].set_xticks([0, 1])
axes[1].set_xticklabels(["Fixed NED", "Relative NED"])
axes[1].set_ylabel("Score")

plt.tight_layout()
fig_path = PROJECT_ROOT / "analysis" / "ned_distributions.png"
fig.savefig(fig_path, dpi=150)
print(f"Saved distribution plot to: {fig_path}")
plt.show()

# %% [markdown]
# ## 4. Breakdown by Technology Stack / Programming Language
#
# How does microservice size balance vary across programming language ecosystems?

# %%
# Group languages with few occurrences into 'Other'
lang_counts = df_apps["language"].value_counts()
major_langs = lang_counts[lang_counts >= 3].index.tolist()
df_apps["lang_group"] = df_apps["language"].apply(lambda l: l if l in major_langs else "Other")

lang_agg = df_apps.groupby("lang_group").agg(
    systems_count=("system_id", "count"),
    mean_ned_abs=("ned_absolute", "mean"),
    median_ned_abs=("ned_absolute", "median"),
    mean_ned_rel=("ned_relative", "mean"),
    median_ned_rel=("ned_relative", "median"),
    mean_services=("service_count", "mean"),
    mean_classes=("total_classes", "mean"),
).reset_index().sort_values("systems_count", ascending=False)

print(lang_agg.round(3).to_string(index=False))

# %%
fig, ax = plt.subplots(figsize=(10, 5))
melted_lang = pd.melt(
    df_apps,
    id_vars=["lang_group"],
    value_vars=["ned_absolute", "ned_relative"],
    var_name="Metric",
    value_name="Score"
)
melted_lang["Metric"] = melted_lang["Metric"].map({"ned_absolute": "Fixed NED", "ned_relative": "Relative NED"})

sns.barplot(
    data=melted_lang,
    x="lang_group",
    y="Score",
    hue="Metric",
    palette=["steelblue", "darkorange"],
    errorbar=None,
    ax=ax
)
ax.set_title("Mean NED Score by Application Language Ecosystem", fontsize=13, fontweight="bold")
ax.set_xlabel("Language Ecosystem")
ax.set_ylabel("Average Score")
ax.set_ylim(0, 1.0)
ax.legend(title="Metric")

fig_lang_path = PROJECT_ROOT / "analysis" / "ned_by_language.png"
fig.savefig(fig_lang_path, dpi=150)
print(f"Saved language comparison plot to: {fig_lang_path}")
plt.show()

# %% [markdown]
# ## 5. Architectural Archetypes: Most Balanced vs. Most Skewed Systems (Filtered by Application)
#
# Identifying the application systems that achieve exemplary decomposition balance vs. those with significant skew,
# excluding pure infrastructure/deployment recipes.

# %%
print("=== TOP 10 BALANCED APPLICATION MICROSERVICES (Fixed NED) ===")
top_balanced = df_apps.sort_values(by=["ned_absolute", "ned_relative"], ascending=[False, False])[
    ["system_id", "system_name", "language", "service_count", "total_classes", "avg_service_size", "ned_absolute", "ned_relative"]
].head(10)
print(top_balanced.to_string(index=False))

# %%
print("\n=== TOP 10 SKEWED / EXTREME APPLICATION MICROSERVICES (Lowest Fixed NED) ===")
most_skewed = df_apps[df_apps["total_classes"] > 0].sort_values(
    by=["ned_absolute", "ned_relative"], ascending=[True, True]
)[
    ["system_id", "system_name", "language", "service_count", "total_classes", "avg_service_size", "tiny_services_count", "god_services_count", "ned_absolute", "ned_relative"]
].head(10)
print(most_skewed.to_string(index=False))

# %% [markdown]
# ## 6. Scale Dynamics: Architectural Size vs. NED Score (Application Microservices)
#
# Does microservice system scale (number of classes or services) degrade Non-Extreme Distribution balance?

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot 1: Total Classes vs Fixed NED
sns.scatterplot(
    data=df_apps,
    x="total_classes",
    y="ned_absolute",
    hue="lang_group",
    size="service_count",
    sizes=(30, 200),
    alpha=0.7,
    ax=axes[0]
)
axes[0].set_xscale("log")
axes[0].set_title("Total Classes vs. Fixed NED (Application Systems, Log Scale)", fontsize=13, fontweight="bold")
axes[0].set_xlabel("Total Classes (log scale)")
axes[0].set_ylabel("Fixed NED Score")
axes[0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')

# Plot 2: Service Count vs Fixed NED
sns.scatterplot(
    data=df_apps,
    x="service_count",
    y="ned_absolute",
    hue="lang_group",
    size="total_classes",
    sizes=(30, 200),
    alpha=0.7,
    ax=axes[1]
)
axes[1].set_title("Service Count vs. Fixed NED (Application Systems)", fontsize=13, fontweight="bold")
axes[1].set_xlabel("Service Count")
axes[1].set_ylabel("Fixed NED Score")
axes[1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')

plt.tight_layout()
fig_scale_path = PROJECT_ROOT / "analysis" / "ned_scale_correlations.png"
fig.savefig(fig_scale_path, dpi=150)
print(f"Saved scale correlation plot to: {fig_scale_path}")
plt.show()

# %% [markdown]
# ### Correlation Analysis
# Numerical rank correlation between system scale and balance across application microservices.

# %%
corr_df = df_apps[["total_classes", "service_count", "avg_service_size", "size_cv", "ned_absolute", "ned_relative"]].corr(method="spearman")
print("Spearman Rank Correlation Matrix (Application Systems):")
corr_df.round(3)

# %% [markdown]
# ## 8. Multi-page PDF Report Generation
#
# Exporting publication-ready PDF analytical report containing summary statistics and all visual figures.

# %%
pdf_report_path = PROJECT_ROOT / "analysis" / "ned_report.pdf"

with PdfPages(pdf_report_path) as pdf:
    # Page 1: Title and Summary Table
    fig_cover, ax_cover = plt.subplots(figsize=(11, 8.5))
    ax_cover.axis("off")
    ax_cover.text(0.5, 0.90, "Non-Extreme Distribution (NED) Report", fontsize=20, fontweight="bold", ha="center")
    ax_cover.text(0.5, 0.85, "Decomposition Quality & Service Size Balance Evaluation across Application Systems", fontsize=12, color="gray", ha="center")
    
    table_data = summary_stats_apps.round(3).reset_index()
    table_data.columns = ["Metric", "Count", "Mean", "Std", "Min", "25%", "Median", "75%", "Max"]
    table = ax_cover.table(
        cellText=table_data.values,
        colLabels=table_data.columns,
        loc="center",
        cellLoc="center"
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.1, 1.6)
    
    summary_text = (
        "Key Insights:\n"
        f"• Evaluated {len(df_apps)} application microservice systems ({len(df_valid)} total including infrastructure/orchestration).\n"
        f"• Application Systems - Fixed NED: Mean = {df_apps['ned_absolute'].mean():.4f}, Median = {df_apps['ned_absolute'].median():.4f}.\n"
        f"• Application Systems - Relative NED: Mean = {df_apps['ned_relative'].mean():.4f}, Median = {df_apps['ned_relative'].median():.4f}.\n"
        "• Segregated pure infrastructure/deployment recipes (which have 0-1 services/classes) to avoid metric skew.\n"
        "• Fixed NED penalizes systems diverging from the global [5, 20] range.\n"
        "• Relative NED adapts to system scale, offering a fairer assessment of internal balance."
    )
    ax_cover.text(0.1, 0.16, summary_text, fontsize=9.5, verticalalignment="top", fontfamily="monospace")
    pdf.savefig(fig_cover, dpi=150)
    plt.close(fig_cover)

    # Page 2: Distribution Figure
    fig_dist_p = PROJECT_ROOT / "analysis" / "ned_distributions.png"
    if fig_dist_p.exists():
        fig_dist = plt.figure(figsize=(11, 6))
        img_dist = plt.imread(fig_dist_p)
        plt.imshow(img_dist)
        plt.axis("off")
        plt.title("Distribution of NED Scores Across Systems", fontsize=14, fontweight="bold")
        pdf.savefig(fig_dist, dpi=150)
        plt.close(fig_dist)

    # Page 3: Language Breakdown Figure
    fig_lang_p = PROJECT_ROOT / "analysis" / "ned_by_language.png"
    if fig_lang_p.exists():
        fig_lang = plt.figure(figsize=(11, 6))
        img_lang = plt.imread(fig_lang_p)
        plt.imshow(img_lang)
        plt.axis("off")
        plt.title("NED Distribution Grouped by Language", fontsize=14, fontweight="bold")
        pdf.savefig(fig_lang, dpi=150)
        plt.close(fig_lang)

    # Page 4: Scale Correlations Figure
    if fig_scale_path.exists():
        fig_scale = plt.figure(figsize=(11, 6))
        img_scale = plt.imread(fig_scale_path)
        plt.imshow(img_scale)
        plt.axis("off")
        plt.title("Correlation: System Scale vs. NED", fontsize=14, fontweight="bold")
        pdf.savefig(fig_scale, dpi=150)
        plt.close(fig_scale)

print(f"Generated multi-page PDF report at: {pdf_report_path}")

