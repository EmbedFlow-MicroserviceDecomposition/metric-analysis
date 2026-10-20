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
# # Structural Modularity (SM) Analysis across Microservice Architectures
#
# This notebook ingests Structural Modularity (SM) evaluation results from the `outputs/` directory to analyze
# microservice decomposition quality, balancing intra-service cohesion against inter-service coupling over the monolith call graph.
#
# ### Metric Definition:
# **Structural Modularity (SM)** evaluates the modular quality of a microservice partition $P = \{c_1, \dots, c_K\}$
# derived from a monolithic codebase or dependency call graph:
#
# $$SM(P) = \frac{1}{K} \sum_{k=1}^K \left[ \frac{\mu_k}{|c_k|^2} - \frac{1}{K-1} \sum_{j \ne k, |c_j|>0} \frac{\sigma_{kj}}{2 |c_k| |c_j|} \right]$$
#
# where:
# - $\mu_k$ is the number of internal dependency edges within microservice cluster $c_k$ (intra-service cohesion).
# - $\sigma_{kj}$ is the number of external dependency edges connecting microservice $c_k$ and microservice $c_j$ (inter-service coupling).
# - $|c_k|$ is the number of classes/components assigned to cluster $c_k$.
# - Range: $[-0.5, 1.0]$. Higher values indicate superior decomposition quality (high cohesion, low coupling).

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
# We scan each system directory in `outputs/` for `sm_score.json` and `output.json`.

# %%
def load_sm_dataset(outputs_dir: Path, manifest_path: Path) -> pd.DataFrame:
    """Ingests SM evaluation results directly from outputs/ into a pandas DataFrame."""
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    records = []
    
    for sys_dir in sorted(outputs_dir.iterdir()):
        if not sys_dir.is_dir() or not sys_dir.name.startswith("MS"):
            continue
            
        sys_id = sys_dir.name
        score_file = sys_dir / "sm_score.json"
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
        std_ms = float(np.std(ms_vals)) if len(ms_vals) > 1 else 0.0

        records.append({
            "system_id": sys_id,
            "system_name": sys_name,
            "language": language,
            "sm_score": round(float(score), 4) if pd.notnull(score) else np.nan,
            "service_count": service_count,
            "total_classes": total_classes,
            "edges_analyzed": meta.get("edges_analyzed", 0),
            "undirected": meta.get("undirected", False),
            "min_service_sm": round(float(min_ms), 4),
            "max_service_sm": round(float(max_ms), 4),
            "std_service_sm": round(std_ms, 4),
            "has_classes": total_classes > 0,
            "is_application": language not in ["Infrastructure", "Documentation"],
            "category": "Application" if language not in ["Infrastructure", "Documentation"] else language,
            "has_edges": meta.get("edges_analyzed", 0) > 0
        })
        
    df = pd.DataFrame(records)
    if not df.empty:
        df["sys_num"] = df["system_id"].apply(lambda x: int(x[2:]) if x.startswith("MS") and x[2:].isdigit() else 9999)
        df = df.sort_values("sys_num").drop(columns=["sys_num"]).reset_index(drop=True)
    return df

df = load_sm_dataset(OUTPUTS_DIR, MANIFEST_PATH)
print(f"Loaded {len(df)} systems with SM scores.")
if not df.empty:
    print(df.head(10))

# %% [markdown]
# ## 2. Descriptive Statistical Summary (Segregated by System Nature & Graph Connectivity)
#
# Overall distribution and spread of Structural Modularity across evaluated architectures,
# segregated by Application Systems vs. Infrastructure and Connected Microservice Graphs (>0 edges) vs. Inactive (0 edges).

# %%
df_valid = df[df["has_classes"]].copy() if not df.empty and "has_classes" in df.columns else df.copy()

if not df_valid.empty and "language" in df_valid.columns:
    lang_counts = df_valid["language"].value_counts()
    main_langs = lang_counts[lang_counts >= 3].index.tolist()
    df_valid["lang_group"] = df_valid["language"].apply(lambda l: l if l in main_langs else "Other")
else:
    df_valid["lang_group"] = "Unknown"

df_apps = df_valid[df_valid["is_application"]].copy() if not df_valid.empty and "is_application" in df_valid.columns else df_valid.copy()
df_active = df_apps[df_apps["has_edges"]].copy() if not df_apps.empty and "has_edges" in df_apps.columns else df_apps.copy()
df_inactive = df_valid[~df_valid["has_edges"]].copy() if not df_valid.empty and "has_edges" in df_valid.columns else pd.DataFrame()

stats_cols = [
    "sm_score", "min_service_sm", "max_service_sm", "std_service_sm",
    "service_count", "total_classes", "edges_analyzed"
]
available_cols = [c for c in stats_cols if c in df_valid.columns]

print(f"=== GLOBAL DESCRIPTIVE STATISTICS (ALL SYSTEMS, n={len(df_valid)}) ===")
if not df_valid.empty and available_cols:
    summary_stats_all = df_valid[available_cols].describe().T
    summary_stats_all["median"] = df_valid[available_cols].median()
    summary_stats_all = summary_stats_all[["count", "mean", "std", "min", "25%", "median", "75%", "max"]]
else:
    summary_stats_all = pd.DataFrame()
print(summary_stats_all)

print(f"\n=== ACTIVE CONNECTED APPLICATION MICROSERVICES (EDGES > 0, n={len(df_active)}) ===")
if not df_active.empty and available_cols:
    summary_stats_active = df_active[available_cols].describe().T
    summary_stats_active["median"] = df_active[available_cols].median()
    summary_stats_active = summary_stats_active[["count", "mean", "std", "min", "25%", "median", "75%", "max"]]
else:
    summary_stats_active = pd.DataFrame()
print(summary_stats_active)

print("\n=== SEGREGATION COMPARISON: CATEGORY & GRAPH CONNECTIVITY ===")
seg_stats = df_valid.groupby(["category", "has_edges"]).agg(
    systems_count=("sm_score", "count"),
    mean_sm=("sm_score", "mean"),
    median_sm=("sm_score", "median"),
    mean_edges=("edges_analyzed", "mean"),
    mean_classes=("total_classes", "mean")
).reset_index() if not df_valid.empty else pd.DataFrame()
print(seg_stats.to_string(index=False))

# %% [markdown]
# ## 3. Distribution Visualizations: Histograms & Segregated Boxplots

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot 1: Histogram / KDE of SM scores
plot_df = df_active if not df_active.empty else df_valid
if not plot_df.empty:
    sns.histplot(
        plot_df["sm_score"],
        kde=len(plot_df) > 1,
        bins=min(15, max(5, len(plot_df))),
        color="#2b5c8f",
        ax=axes[0]
    )
    axes[0].set_title(f"Distribution of Structural Modularity (SM) (Connected Apps, n={len(plot_df)})", fontsize=13, fontweight="bold")
    axes[0].set_xlabel("SM Score (intra-cohesion density - inter-coupling density)")
    axes[0].set_ylabel("Frequency")
    if not plot_df.empty:
        axes[0].axvline(plot_df["sm_score"].mean(), color="red", linestyle="--", label=f"Mean: {plot_df['sm_score'].mean():.4f}")
        axes[0].axvline(plot_df["sm_score"].median(), color="orange", linestyle=":", label=f"Median: {plot_df['sm_score'].median():.4f}")
        axes[0].legend()

# Plot 2: Boxplot by Category / Graph Connectivity
if not df_valid.empty:
    sns.boxplot(
        data=df_valid,
        x="category",
        y="sm_score",
        hue="has_edges",
        palette=["#e74c3c", "#2ecc71"] if len(df_valid["has_edges"].unique()) > 1 else ["#2ecc71"],
        ax=axes[1]
    )
    axes[1].set_title("SM Score by Category & Graph Connectivity", fontsize=13, fontweight="bold")
    axes[1].set_xlabel("System Category")
    axes[1].set_ylabel("SM Score")

plt.tight_layout()
fig_dist_path = PROJECT_ROOT / "analysis" / "sm_distributions.png"
fig.savefig(fig_dist_path, dpi=150)
print(f"Saved distribution plot to: {fig_dist_path}")
plt.show()

# %% [markdown]
# ## 4. Structural Modularity Breakdown by Primary Implementation Language

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

target_lang_df = df_active if not df_active.empty else df_valid

if not target_lang_df.empty:
    order = target_lang_df.groupby("lang_group")["sm_score"].mean().sort_values(ascending=False).index

    sns.barplot(
        data=target_lang_df,
        x="lang_group",
        y="sm_score",
        order=order,
        ci=None,
        palette="viridis",
        ax=axes[0]
    )
    axes[0].set_title("Mean SM Score by Implementation Language", fontsize=13, fontweight="bold")
    axes[0].set_xlabel("Primary Language")
    axes[0].set_ylabel("Mean SM Score")
    axes[0].tick_params(axis='x', rotation=30)

    sns.boxplot(
        data=target_lang_df,
        x="lang_group",
        y="sm_score",
        order=order,
        palette="viridis",
        ax=axes[1]
    )
    axes[1].set_title("SM Distribution by Language", fontsize=13, fontweight="bold")
    axes[1].set_xlabel("Primary Language")
    axes[1].set_ylabel("SM Score")
    axes[1].tick_params(axis='x', rotation=30)

plt.tight_layout()
fig_lang_path = PROJECT_ROOT / "analysis" / "sm_by_language.png"
fig.savefig(fig_lang_path, dpi=150)
print(f"Saved language breakdown plot to: {fig_lang_path}")
plt.show()

# %% [markdown]
# ## 5. Top and Bottom Ranked Microservice Architectures by SM

# %%
print("\n=== TOP 10 HIGHEST STRUCTURAL MODULARITY (High Cohesion, Low Coupling) ===")
if not df_active.empty:
    top_sm = df_active.sort_values(by="sm_score", ascending=False)[
        ["system_id", "system_name", "language", "service_count", "total_classes", "edges_analyzed", "sm_score", "min_service_sm", "max_service_sm"]
    ].head(10)
    print(top_sm.to_string(index=False))

print("\n=== TOP 10 LOWEST STRUCTURAL MODULARITY (Inter-Service Entanglement / Low Modularity) ===")
if not df_active.empty:
    bottom_sm = df_active.sort_values(by="sm_score", ascending=True)[
        ["system_id", "system_name", "language", "service_count", "total_classes", "edges_analyzed", "sm_score", "min_service_sm", "max_service_sm"]
    ].head(10)
    print(bottom_sm.to_string(index=False))

# %% [markdown]
# ## 6. Scale Dynamics: Architectural Size vs. SM (Connected Applications)

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

plot_scale_df = df_active if not df_active.empty else df_valid

if not plot_scale_df.empty:
    # Plot 1: Total Classes vs SM
    sns.scatterplot(
        data=plot_scale_df,
        x="total_classes",
        y="sm_score",
        hue="lang_group",
        size="edges_analyzed",
        sizes=(30, 200),
        alpha=0.7,
        ax=axes[0]
    )
    if (plot_scale_df["total_classes"] > 0).all():
        axes[0].set_xscale("log")
    axes[0].set_title("Total Classes vs. SM (Connected Apps)", fontsize=13, fontweight="bold")
    axes[0].set_xlabel("Total Classes (log scale)")
    axes[0].set_ylabel("SM Score")
    axes[0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    # Plot 2: Service Count vs SM
    sns.scatterplot(
        data=plot_scale_df,
        x="service_count",
        y="sm_score",
        hue="lang_group",
        size="edges_analyzed",
        sizes=(30, 200),
        alpha=0.7,
        ax=axes[1]
    )
    axes[1].set_title("Service Count vs. SM (Connected Apps)", fontsize=13, fontweight="bold")
    axes[1].set_xlabel("Service Count")
    axes[1].set_ylabel("SM Score")
    axes[1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')

plt.tight_layout()
fig_scale_path = PROJECT_ROOT / "analysis" / "sm_scale_correlations.png"
fig.savefig(fig_scale_path, dpi=150)
print(f"Saved scale correlation plot to: {fig_scale_path}")
plt.show()

# %% [markdown]
# ## 7. Multi-page PDF Report Generation

# %%
pdf_report_path = PROJECT_ROOT / "analysis" / "sm_report.pdf"

with PdfPages(pdf_report_path) as pdf:
    # Page 1: Title and Summary Table
    fig_cover, ax_cover = plt.subplots(figsize=(11, 8.5))
    ax_cover.axis("off")
    ax_cover.text(0.5, 0.90, "Structural Modularity (SM) Decomposition Quality Report", fontsize=20, fontweight="bold", ha="center")
    ax_cover.text(0.5, 0.85, "Cross-System Decomposition Quality & Coupling Evaluation (Connected Application Microservices)", fontsize=12, color="gray", ha="center")
    
    if not summary_stats_active.empty:
        table_data = summary_stats_active.round(4).reset_index()
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
    
    mean_val = df_active['sm_score'].mean() if not df_active.empty else 0.0
    med_val = df_active['sm_score'].median() if not df_active.empty else 0.0
    summary_text = (
        "Key Insights:\n"
        f"• Evaluated {len(df_valid)} systems total ({len(df_apps)} application systems, {len(df_active)} with connected monolith call graphs).\n"
        f"• Connected Application Microservices SM: Mean = {mean_val:.4f} (Median: {med_val:.4f}).\n"
        "• Structural Modularity evaluates intra-service cohesion density minus inter-service coupling density.\n"
        "• High SM indicates clean decomposition where service boundaries minimize cross-service chatter.\n"
        "• Near-zero or negative SM reveals architectural entanglement where inter-service coupling dominates internal cohesion."
    )
    ax_cover.text(0.1, 0.16, summary_text, fontsize=9.5, verticalalignment="top", fontfamily="monospace")
    pdf.savefig(fig_cover, dpi=150)
    plt.close(fig_cover)

    # Page 2: Distribution Figure
    fig_dist = plt.figure(figsize=(11, 6))
    img_dist = plt.imread(fig_dist_path)
    plt.imshow(img_dist)
    plt.axis("off")
    plt.title("Distribution of SM Scores Across Systems", fontsize=14, fontweight="bold")
    pdf.savefig(fig_dist, dpi=150)
    plt.close(fig_dist)

    # Page 3: Language Breakdown Figure
    fig_lang = plt.figure(figsize=(11, 6))
    img_lang = plt.imread(fig_lang_path)
    plt.imshow(img_lang)
    plt.axis("off")
    plt.title("SM Distribution Grouped by Language", fontsize=14, fontweight="bold")
    pdf.savefig(fig_lang, dpi=150)
    plt.close(fig_lang)

    # Page 4: Scale Correlations Figure
    fig_scale = plt.figure(figsize=(11, 6))
    img_scale = plt.imread(fig_scale_path)
    plt.imshow(img_scale)
    plt.axis("off")
    plt.title("Correlation: Scale vs. SM", fontsize=14, fontweight="bold")
    pdf.savefig(fig_scale, dpi=150)
    plt.close(fig_scale)

print(f"Generated multi-page PDF report at: {pdf_report_path}")
