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
# # Cohesion at Message Level (CHM) Analysis across Microservice Architectures
#
# This notebook ingests CHM evaluation results from the `outputs/` directory to analyze
# message type consistency and communication payload cohesion across open-source microservices.
#
# ### Metric Definition:
# **Cohesion at Message Level (CHM)** evaluates the uniformity of message signatures (parameters
# and return types) exposed by each microservice to other services.
#
# $$\text{CHM}(S) = \frac{1}{|M|} \sum_{m \in M} \text{mean}_{a, b \in \text{Ops}(m), a \neq b} \left( \frac{J(\text{params}(a), \text{params}(b)) + J(\text{returns}(a), \text{returns}(b))}{2} \right)$$
#
# where:
# - $\text{Ops}(m)$ is the set of published operations exposed by microservice $m$ that are invoked across services.
# - $\text{params}(op)$ and $\text{returns}(op)$ are the parameter types and return type of operation $op$.
# - Microservices with $\le 1$ published operation default to $1.0$.
# - Range: $[0.0, 1.0]$ (Higher is better).

# %%
import json
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
# We scan each system directory in `outputs/` for `chm_score.json` and `output.json`.

# %%
def load_chm_dataset(outputs_dir: Path, manifest_path: Path) -> pd.DataFrame:
    """Ingests CHM evaluation results directly from outputs/ into a pandas DataFrame."""
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    records = []
    
    for sys_dir in sorted(outputs_dir.iterdir()):
        if not sys_dir.is_dir() or not sys_dir.name.startswith("MS"):
            continue
            
        sys_id = sys_dir.name
        score_file = sys_dir / "chm_score.json"
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
        ms_scores = score_data.get("microservice_scores", {})
        score = score_data.get("score", np.nan)
        
        service_count = meta.get("services_count", len(ms_scores))
        total_classes = 0
        if output_file.exists():
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    out_data = json.load(f)
                    ms_dict = out_data.get("microservices", {})
                    service_count = len(ms_dict)
                    total_classes = sum(len(c) for c in ms_dict.values())
            except Exception:
                pass

        sys_info = manifest.get(sys_id, {})
        sys_name = sys_info.get("name", sys_id)
        language = sys_info.get("language", "Unknown")
        
        ms_vals = list(ms_scores.values()) if ms_scores else []
        min_ms = min(ms_vals) if ms_vals else np.nan
        max_ms = max(ms_vals) if ms_vals else np.nan
        std_ms = float(np.std(ms_vals)) if len(ms_vals) > 1 else 0.0

        records.append({
            "system_id": sys_id,
            "system_name": sys_name,
            "language": language,
            "chm_score": round(float(score), 4) if pd.notnull(score) else np.nan,
            "service_count": service_count,
            "total_classes": total_classes,
            "calls_analyzed": meta.get("calls_analyzed", 0),
            "min_service_chm": round(min_ms, 4) if pd.notnull(min_ms) else np.nan,
            "max_service_chm": round(max_ms, 4) if pd.notnull(max_ms) else np.nan,
            "std_service_chm": round(std_ms, 4),
            "has_classes": total_classes > 0,
            "is_application": language not in ["Infrastructure", "Documentation"],
            "category": "Application" if language not in ["Infrastructure", "Documentation"] else language,
            "has_calls": meta.get("calls_analyzed", 0) > 0
        })
        
    df = pd.DataFrame(records)
    if not df.empty:
        df["sys_num"] = df["system_id"].apply(lambda x: int(x[2:]) if x.startswith("MS") and x[2:].isdigit() else 9999)
        df = df.sort_values("sys_num").drop(columns=["sys_num"]).reset_index(drop=True)
    return df

df = load_chm_dataset(OUTPUTS_DIR, MANIFEST_PATH)
print(f"Loaded {len(df)} systems with CHM scores.")
df.head(10)

# %% [markdown]
# %% [markdown]
# ## 2. Descriptive Statistical Summary (Segregated by System Nature & Call Activity)
#
# Overall distribution and spread of Message Cohesion across evaluated architectures,
# segregated by Application Systems vs. Infrastructure and Active Method Calls (>0) vs. Inactive (0 calls).

# %%
df_valid = df[df["has_classes"]].copy() if not df.empty else df.copy()
lang_counts = df_valid["language"].value_counts()
main_langs = lang_counts[lang_counts >= 3].index.tolist()
df_valid["lang_group"] = df_valid["language"].apply(lambda l: l if l in main_langs else "Other")

df_apps = df_valid[df_valid["is_application"]].copy()
df_active = df_apps[df_apps["has_calls"]].copy()
df_inactive = df_valid[~df_valid["has_calls"]].copy()

stats_cols = [
    "chm_score",
    "service_count",
    "total_classes",
    "calls_analyzed",
    "std_service_chm"
]
available_cols = [c for c in stats_cols if c in df_valid.columns]

summary_stats_global = df_valid[available_cols].describe().T
summary_stats_global["median"] = df_valid[available_cols].median()
summary_stats_global = summary_stats_global[["count", "mean", "std", "min", "25%", "median", "75%", "max"]]

summary_stats_active = df_active[available_cols].describe().T
summary_stats_active["median"] = df_active[available_cols].median()
summary_stats_active = summary_stats_active[["count", "mean", "std", "min", "25%", "median", "75%", "max"]]

segregation_comparison = df_valid.groupby(["category", "has_calls"]).agg(
    systems_count=("system_id", "count"),
    mean_chm=("chm_score", "mean"),
    median_chm=("chm_score", "median"),
    mean_calls=("calls_analyzed", "mean"),
    mean_classes=("total_classes", "mean")
).reset_index()

print(f"=== GLOBAL DESCRIPTIVE STATISTICS (ALL SYSTEMS, n={len(df_valid)}) ===")
print(summary_stats_global.round(3))

print(f"\n=== ACTIVE APPLICATION MICROSERVICES (CALLS > 0, n={len(df_active)}) ===")
print(summary_stats_active.round(3))

print("\n=== SEGREGATION COMPARISON: CATEGORY & CALL ACTIVITY ===")
print(segregation_comparison.round(3).to_string(index=False))

# %% [markdown]
# ## 3. Distribution of Message Cohesion Scores (Comparative Segregation)
#
# Comparing the distribution of CHM scores for Active Application Microservices vs. Global Dataset
# to evaluate the skew introduced by trivial 0-call infrastructure/inactive systems.

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot 1: Histogram & KDE Comparison
sns.histplot(
    df_valid["chm_score"],
    kde=True,
    color="gray",
    label=f"All Systems (n={len(df_valid)})",
    bins=15,
    ax=axes[0],
    stat="density",
    alpha=0.4
)
sns.histplot(
    df_active["chm_score"],
    kde=True,
    color="darkslateblue",
    label=f"Active Apps (calls > 0, n={len(df_active)})",
    bins=15,
    ax=axes[0],
    stat="density",
    alpha=0.7
)
axes[0].set_title("Density Distribution: All vs. Active Applications", fontsize=13, fontweight="bold")
axes[0].set_xlabel("CHM Score [0.0 - 1.0]")
axes[0].set_ylabel("Density")
axes[0].legend()

# Plot 2: Boxplot Breakdown by Cohort
cohort_data = pd.DataFrame({
    "Cohort": ["Active Apps\n(calls > 0)"] * len(df_active) + ["Inactive / Infra\n(calls = 0)"] * len(df_inactive),
    "CHM Score": list(df_active["chm_score"]) + list(df_inactive["chm_score"])
})
sns.boxplot(
    data=cohort_data,
    x="Cohort",
    y="CHM Score",
    palette=["darkslateblue", "lightcoral"],
    ax=axes[1],
    width=0.4
)
axes[1].set_title("CHM Spread: Active Application vs. Inactive Cohorts", fontsize=13, fontweight="bold")
axes[1].set_ylabel("CHM Score")

plt.tight_layout()
fig_dist_path = PROJECT_ROOT / "analysis" / "chm_distributions.png"
fig.savefig(fig_dist_path, dpi=150)
print(f"Saved distribution plot to: {fig_dist_path}")
plt.show()

# %% [markdown]
# ## 4. Breakdown by Implementation Language
#
# Comparing message type homogeneity across language paradigms (e.g. strongly typed Java vs. dynamically typed Python).

# %%
lang_counts = df_valid["language"].value_counts()
main_langs = lang_counts[lang_counts >= 2].index
df_valid["lang_group"] = df_valid["language"].apply(lambda l: l if l in main_langs else "Other")
fig, ax = plt.subplots(figsize=(10, 5))
order_langs = sorted(df_apps["lang_group"].unique())
sns.boxplot(
    data=df_apps,
    x="lang_group",
    y="chm_score",
    palette="Purples",
    ax=ax,
    order=order_langs
)
sns.stripplot(
    data=df_apps,
    x="lang_group",
    y="chm_score",
    color="black",
    alpha=0.5,
    jitter=0.2,
    size=5,
    ax=ax,
    order=order_langs
)
ax.set_title("CHM Score Distribution by Application Primary Language", fontsize=13, fontweight="bold")
ax.set_xlabel("Implementation Language")
ax.set_ylabel("CHM Score")
plt.tight_layout()

fig_lang_path = PROJECT_ROOT / "analysis" / "chm_by_language.png"
fig.savefig(fig_lang_path, dpi=150)
print(f"Saved language breakdown plot to: {fig_lang_path}")
plt.show()

# %% [markdown]
# ## 5. Top Highly Cohesive vs. Heterogeneous Message Systems (Active Applications, calls > 0)

# %%
print("\n=== TOP 10 HIGHEST MESSAGE COHESION (Active Application Microservices) ===")
top_chm = df_active.sort_values(by="chm_score", ascending=False)[
    ["system_id", "system_name", "language", "service_count", "total_classes", "calls_analyzed", "chm_score"]
].head(10)
print(top_chm.to_string(index=False))

print("\n=== TOP 10 LOWEST MESSAGE COHESION (Heterogeneous Payload Signatures) ===")
low_chm = df_active.sort_values(by="chm_score", ascending=True)[
    ["system_id", "system_name", "language", "service_count", "total_classes", "calls_analyzed", "chm_score"]
].head(10)
print(low_chm.to_string(index=False))

# %% [markdown]
# ## 6. Scale Dynamics: Architectural Size vs. CHM (Active Application Microservices)

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot 1: Total Classes vs CHM
sns.scatterplot(
    data=df_active,
    x="total_classes",
    y="chm_score",
    hue="lang_group",
    size="calls_analyzed",
    sizes=(30, 200),
    alpha=0.7,
    ax=axes[0]
)
axes[0].set_xscale("log")
axes[0].set_title("Total Classes vs. CHM (Active Apps, Log Scale)", fontsize=13, fontweight="bold")
axes[0].set_xlabel("Total Classes (log scale)")
axes[0].set_ylabel("CHM Score")
axes[0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')

# Plot 2: Inter-Service Calls vs CHM
sns.scatterplot(
    data=df_active,
    x="calls_analyzed",
    y="chm_score",
    hue="lang_group",
    size="service_count",
    sizes=(30, 200),
    alpha=0.7,
    ax=axes[1]
)
axes[1].set_xscale("symlog")
axes[1].set_title("Calls Analyzed vs. CHM (Active Apps)", fontsize=13, fontweight="bold")
axes[1].set_xlabel("Inter-Service Calls (symlog)")
axes[1].set_ylabel("CHM Score")
axes[1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')

plt.tight_layout()
fig_scale_path = PROJECT_ROOT / "analysis" / "chm_scale_correlations.png"
fig.savefig(fig_scale_path, dpi=150)
print(f"Saved scale correlation plot to: {fig_scale_path}")
plt.show()

# %% [markdown]
# ## 7. Multi-page PDF Report Generation

# %%
pdf_report_path = PROJECT_ROOT / "analysis" / "chm_report.pdf"

with PdfPages(pdf_report_path) as pdf:
    # Page 1: Title and Summary Table
    fig_cover, ax_cover = plt.subplots(figsize=(11, 8.5))
    ax_cover.axis("off")
    ax_cover.text(0.5, 0.90, "Cohesion at Message Level (CHM) Report", fontsize=20, fontweight="bold", ha="center")
    ax_cover.text(0.5, 0.85, "Cross-System Message Payload Consistency Evaluation (Active Application Microservices)", fontsize=12, color="gray", ha="center")
    
    table_data = summary_stats_active.round(3).reset_index()
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
        f"• Evaluated {len(df_valid)} systems total ({len(df_apps)} application systems, {len(df_active)} with active method invocations).\n"
        f"• Active Application Systems CHM: Mean = {df_active['chm_score'].mean():.4f}, Median = {df_active['chm_score'].median():.4f}.\n"
        "• Segregated pure infrastructure/deployment recipes and 0-call repositories which trivially default to CHM=1.0.\n"
        "• CHM evaluates consistency of parameter and return types in published service operations.\n"
        "• High CHM reflects standardized DTO and domain object reuse across RPC/REST endpoints.\n"
        "• Low CHM points to disparate data types across operations within the same service."
    )
    ax_cover.text(0.1, 0.16, summary_text, fontsize=9.5, verticalalignment="top", fontfamily="monospace")
    pdf.savefig(fig_cover, dpi=150)
    plt.close(fig_cover)

    # Page 2: Distribution Figure
    fig_dist = plt.figure(figsize=(11, 6))
    img_dist = plt.imread(fig_dist_path)
    plt.imshow(img_dist)
    plt.axis("off")
    plt.title("Distribution of CHM Scores Across Systems", fontsize=14, fontweight="bold")
    pdf.savefig(fig_dist, dpi=150)
    plt.close(fig_dist)

    # Page 3: Language Breakdown Figure
    fig_lang = plt.figure(figsize=(11, 6))
    img_lang = plt.imread(fig_lang_path)
    plt.imshow(img_lang)
    plt.axis("off")
    plt.title("CHM Distribution Grouped by Language", fontsize=14, fontweight="bold")
    pdf.savefig(fig_lang, dpi=150)
    plt.close(fig_lang)

    # Page 4: Scale Correlations Figure
    fig_scale = plt.figure(figsize=(11, 6))
    img_scale = plt.imread(fig_scale_path)
    plt.imshow(img_scale)
    plt.axis("off")
    plt.title("Correlation: Scale and Inter-Service Calls vs. CHM", fontsize=14, fontweight="bold")
    pdf.savefig(fig_scale, dpi=150)
    plt.close(fig_scale)

print(f"Generated multi-page PDF report at: {pdf_report_path}")
