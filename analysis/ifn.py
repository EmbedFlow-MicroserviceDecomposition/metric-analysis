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
# # Interface Number of Operations (IFN) Analysis across Microservice Architectures
#
# This notebook ingests IFN evaluation results from the `outputs/` directory to analyze
# interface surface area, exposed API complexity, and service coupling across open-source microservices.
#
# ### Metric Definition:
# **Interface Number of Operations (IFN)** measures the average number of distinct operations
# or interfaces exposed by each microservice to other microservices in the system.
#
# $$\text{IFN}(S) = \frac{1}{|M|} \sum_{m \in M} |\text{Interfaces}(m)|$$
#
# where:
# - $\text{Interfaces}(m)$ is the set of unique operations/endpoints of service $m$ invoked by external services.
# - Range: $[0.0, \infty)$ (Lower is generally preferred for lean, decoupled services).

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
# We scan each system directory in `outputs/` for `ifn_score.json` and `output.json`.

# %%
def load_ifn_dataset(outputs_dir: Path, manifest_path: Path) -> pd.DataFrame:
    """Ingests IFN evaluation results directly from outputs/ into a pandas DataFrame."""
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    records = []
    
    for sys_dir in sorted(outputs_dir.iterdir()):
        if not sys_dir.is_dir() or not sys_dir.name.startswith("MS"):
            continue
            
        sys_id = sys_dir.name
        score_file = sys_dir / "ifn_score.json"
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
        min_ms = min(ms_vals) if ms_vals else 0.0
        max_ms = max(ms_vals) if ms_vals else 0.0
        total_ifaces = sum(ms_vals) if ms_vals else 0.0
        std_ms = float(np.std(ms_vals)) if len(ms_vals) > 1 else 0.0

        records.append({
            "system_id": sys_id,
            "system_name": sys_name,
            "language": language,
            "ifn_score": round(float(score), 4) if pd.notnull(score) else np.nan,
            "service_count": service_count,
            "total_classes": total_classes,
            "edges_analyzed": meta.get("edges_analyzed", 0),
            "total_interfaces": int(total_ifaces),
            "min_service_ifaces": int(min_ms),
            "max_service_ifaces": int(max_ms),
            "std_service_ifaces": round(std_ms, 2),
            "has_classes": total_classes > 0
        })
        
    df = pd.DataFrame(records)
    if not df.empty:
        df["sys_num"] = df["system_id"].apply(lambda x: int(x[2:]) if x.startswith("MS") and x[2:].isdigit() else 9999)
        df = df.sort_values("sys_num").drop(columns=["sys_num"]).reset_index(drop=True)
    return df

df = load_ifn_dataset(OUTPUTS_DIR, MANIFEST_PATH)
print(f"Loaded {len(df)} systems with IFN scores.")
df.head(10)

# %% [markdown]
# ## 2. Descriptive Statistical Summary
#
# Overall distribution and spread of Interface Numbers across evaluated architectures.

# %%
df_valid = df[df["has_classes"]].copy() if not df.empty else df.copy()

stats_cols = [
    "ifn_score",
    "total_interfaces",
    "max_service_ifaces",
    "std_service_ifaces",
    "service_count",
    "total_classes",
    "edges_analyzed"
]
available_cols = [c for c in stats_cols if c in df_valid.columns]
summary_stats = df_valid[available_cols].describe().T
summary_stats["median"] = df_valid[available_cols].median()
summary_stats = summary_stats[["count", "mean", "std", "min", "25%", "median", "75%", "max"]]
print("=== IFN GLOBAL DESCRIPTIVE STATISTICS ===")
print(summary_stats.round(3))

# %% [markdown]
# ## 3. Distribution of Interface Numbers
#
# Histogram, KDE, and Boxplot of IFN scores.

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot 1: Histogram & KDE (log scale)
sns.histplot(
    df_valid["ifn_score"],
    kde=True,
    color="darkcyan",
    bins=20,
    ax=axes[0],
    stat="density"
)
axes[0].set_title("Density Distribution: Interface Number (IFN)", fontsize=13, fontweight="bold")
axes[0].set_xlabel("IFN Score (Avg Exposed Interfaces per Service)")
axes[0].set_ylabel("Density")

# Plot 2: Boxplot
sns.boxplot(
    y=df_valid["ifn_score"],
    color="darkcyan",
    ax=axes[1],
    width=0.35
)
axes[1].set_yscale("symlog")
axes[1].set_title("IFN Score Spread (SymLog Scale)", fontsize=13, fontweight="bold")
axes[1].set_ylabel("IFN Score (symlog)")

plt.tight_layout()
fig_dist_path = PROJECT_ROOT / "analysis" / "ifn_distributions.png"
fig.savefig(fig_dist_path, dpi=150)
print(f"Saved distribution plot to: {fig_dist_path}")
plt.show()

# %% [markdown]
# ## 4. Breakdown by Implementation Language
#
# Comparing exposed interface complexity across programming languages.

# %%
lang_counts = df_valid["language"].value_counts()
main_langs = lang_counts[lang_counts >= 2].index
df_valid["lang_group"] = df_valid["language"].apply(lambda l: l if l in main_langs else "Other")

fig, ax = plt.subplots(figsize=(10, 5))
sns.boxplot(
    data=df_valid,
    x="lang_group",
    y="ifn_score",
    palette="GnBu",
    ax=ax,
    order=sorted(df_valid["lang_group"].unique())
)
sns.stripplot(
    data=df_valid,
    x="lang_group",
    y="ifn_score",
    color="black",
    alpha=0.5,
    jitter=0.2,
    size=5,
    ax=ax,
    order=sorted(df_valid["lang_group"].unique())
)
ax.set_yscale("symlog")
ax.set_title("IFN Score Distribution by Primary Language (SymLog Scale)", fontsize=13, fontweight="bold")
ax.set_xlabel("Implementation Language")
ax.set_ylabel("IFN Score")
plt.tight_layout()

fig_lang_path = PROJECT_ROOT / "analysis" / "ifn_by_language.png"
fig.savefig(fig_lang_path, dpi=150)
print(f"Saved language breakdown plot to: {fig_lang_path}")
plt.show()

# %% [markdown]
# ## 5. Top Lean vs. Heavily Exposed Architectures

# %%
print("\n=== TOP 10 LEANEST ARCHITECTURES (Minimal Interface Exposure) ===")
lean_ifn = df_valid[df_valid["edges_analyzed"] > 0].sort_values(by="ifn_score", ascending=True)[
    ["system_id", "system_name", "language", "service_count", "total_classes", "edges_analyzed", "ifn_score", "max_service_ifaces"]
].head(10)
print(lean_ifn.to_string(index=False))

print("\n=== TOP 10 MOST EXPOSED ARCHITECTURES (High Interface Surface / God Interfaces) ===")
heavy_ifn = df_valid.sort_values(by="ifn_score", ascending=False)[
    ["system_id", "system_name", "language", "service_count", "total_classes", "edges_analyzed", "ifn_score", "max_service_ifaces"]
].head(10)
print(heavy_ifn.to_string(index=False))

# %% [markdown]
# ## 6. Scale Dynamics: Architectural Size vs. IFN

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot 1: Total Classes vs IFN
sns.scatterplot(
    data=df_valid,
    x="total_classes",
    y="ifn_score",
    hue="lang_group",
    size="edges_analyzed",
    sizes=(30, 200),
    alpha=0.7,
    ax=axes[0]
)
axes[0].set_xscale("log")
axes[0].set_yscale("symlog")
axes[0].set_title("Total Classes vs. IFN (Log-SymLog Scale)", fontsize=13, fontweight="bold")
axes[0].set_xlabel("Total Classes (log scale)")
axes[0].set_ylabel("IFN Score (symlog)")
axes[0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')

# Plot 2: Service Count vs IFN
sns.scatterplot(
    data=df_valid,
    x="service_count",
    y="ifn_score",
    hue="lang_group",
    size="total_interfaces",
    sizes=(30, 200),
    alpha=0.7,
    ax=axes[1]
)
axes[1].set_yscale("symlog")
axes[1].set_title("Service Count vs. IFN", fontsize=13, fontweight="bold")
axes[1].set_xlabel("Service Count")
axes[1].set_ylabel("IFN Score (symlog)")
axes[1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')

plt.tight_layout()
fig_scale_path = PROJECT_ROOT / "analysis" / "ifn_scale_correlations.png"
fig.savefig(fig_scale_path, dpi=150)
print(f"Saved scale correlation plot to: {fig_scale_path}")
plt.show()

# %% [markdown]
# ## 7. Multi-page PDF Report Generation

# %%
pdf_report_path = PROJECT_ROOT / "analysis" / "ifn_report.pdf"

with PdfPages(pdf_report_path) as pdf:
    # Page 1: Title and Summary Table
    fig_cover, ax_cover = plt.subplots(figsize=(11, 8.5))
    ax_cover.axis("off")
    ax_cover.text(0.5, 0.90, "Interface Number of Operations (IFN) Report", fontsize=20, fontweight="bold", ha="center")
    ax_cover.text(0.5, 0.85, "Cross-System Interface Surface Area & Coupling Evaluation", fontsize=12, color="gray", ha="center")
    
    table_data = summary_stats.round(3).reset_index()
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
        f"• Evaluated {len(df_valid)} systems with valid microservice decompositions.\n"
        f"• Mean IFN: {df_valid['ifn_score'].mean():.2f} interfaces/service (Median: {df_valid['ifn_score'].median():.2f}).\n"
        "• Lower IFN indicates lean microservices with focused, decoupled APIs.\n"
        "• High IFN reveals god interfaces or monolith-style conversational complexity across service boundaries."
    )
    ax_cover.text(0.1, 0.18, summary_text, fontsize=10, verticalalignment="top", fontfamily="monospace")
    pdf.savefig(fig_cover, dpi=150)
    plt.close(fig_cover)

    # Page 2: Distribution Figure
    fig_dist = plt.figure(figsize=(11, 6))
    img_dist = plt.imread(fig_dist_path)
    plt.imshow(img_dist)
    plt.axis("off")
    plt.title("Distribution of IFN Scores Across Systems", fontsize=14, fontweight="bold")
    pdf.savefig(fig_dist, dpi=150)
    plt.close(fig_dist)

    # Page 3: Language Breakdown Figure
    fig_lang = plt.figure(figsize=(11, 6))
    img_lang = plt.imread(fig_lang_path)
    plt.imshow(img_lang)
    plt.axis("off")
    plt.title("IFN Distribution Grouped by Language", fontsize=14, fontweight="bold")
    pdf.savefig(fig_lang, dpi=150)
    plt.close(fig_lang)

    # Page 4: Scale Correlations Figure
    fig_scale = plt.figure(figsize=(11, 6))
    img_scale = plt.imread(fig_scale_path)
    plt.imshow(img_scale)
    plt.axis("off")
    plt.title("Correlation: Scale vs. IFN", fontsize=14, fontweight="bold")
    pdf.savefig(fig_scale, dpi=150)
    plt.close(fig_scale)

print(f"Generated multi-page PDF report at: {pdf_report_path}")
