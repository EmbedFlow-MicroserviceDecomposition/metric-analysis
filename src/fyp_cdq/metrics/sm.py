"""Structural Modularity (SM) decomposition quality metric evaluator."""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from fyp_cdq.metrics.base import BaseMetric
from fyp_cdq.metrics.common import (
    Edge,
    extract_codebase_operations_and_calls,
    load_edges_from_dataset,
    resolve_partition_with_clusters,
)
from fyp_cdq.models import MetricResult, Partition


def calculate_sm(
    partition_func,
    clusters: Dict[str, Set[str]],
    edges: List[Edge],
    undirected: bool = False,
) -> Tuple[float, Dict[str, float]]:
    """
    Structural Modularity (SM).
    Measures intra-partition cohesion density minus inter-partition coupling density
    over the monolith call graph.
    Exact implementation from reference SOTA (sm_sota.py).
    Higher is better.
    """
    K = len(clusters)
    if K == 0:
        return 0.0, {}

    if undirected:
        pairs = {frozenset((e.src, e.dst)) for e in edges if e.src != e.dst}
        edges = [Edge(list(p)[0], list(p)[1] if len(p) > 1 else list(p)[0], "UND", 1.0) for p in pairs]

    mu = {cid: 0 for cid in clusters}
    sigma = {}
    for e in edges:
        ci, cj = partition_func(e.src), partition_func(e.dst)
        if ci is None or cj is None:
            continue
        if ci == cj:
            mu[ci] += 2 if undirected else 1
        else:
            key = frozenset((ci, cj))
            sigma[key] = sigma.get(key, 0) + 1

    microservice_scores = {}
    for cid, members in clusters.items():
        n_k = len(members)
        if n_k == 0:
            microservice_scores[cid] = 0.0
            continue

        intra_k = mu[cid] / (n_k ** 2)
        if K > 1:
            inter_k = sum(
                sigma.get(frozenset((cid, j)), 0) / (2 * n_k * len(clusters[j]))
                for j in clusters if j != cid and len(clusters[j]) > 0
            ) / (K - 1)
        else:
            inter_k = 0.0

        microservice_scores[cid] = intra_k - inter_k

    overall_sm = sum(microservice_scores.values()) / K
    return overall_sm, microservice_scores


class SMMetric(BaseMetric):
    """
    Evaluator for Structural Modularity (SM).
    Decomposition quality metric: requires the monolith call graph (either via a monolith
    codebase `mono_dir` or an external `dataset.json`) and a microservice partition.
    """

    name: str = "SM"
    needs_monolith: bool = True

    def parse_cli_args(self, args: List[str]) -> Dict[str, any]:
        parser = argparse.ArgumentParser(description="SM metric options", prog="sm")
        parser.add_argument("--dataset-path", type=str, default=None, help="Path to directory containing dataset.json")
        parser.add_argument("--undirected", action="store_true", help="Treat call graph edges as undirected")
        parsed, unknown = parser.parse_known_args(args)
        if unknown:
            raise ValueError(f"Unrecognized options for metric 'sm': {' '.join(unknown)}")
        return {
            "dataset_path": Path(parsed.dataset_path) if parsed.dataset_path else None,
            "undirected": parsed.undirected,
        }

    def evaluate(
        self,
        partition: Partition,
        ms_dir: Path,
        mono_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        dataset_path: Optional[Path] = None,
        undirected: bool = False,
        **kwargs,
    ) -> MetricResult:
        # 1. Resolve dataset.json if provided or present
        ds_file = None
        if dataset_path:
            ds_file = dataset_path if dataset_path.is_file() else (dataset_path / "dataset.json")
        elif mono_dir and (mono_dir / "dataset.json").exists():
            ds_file = mono_dir / "dataset.json"
        elif output_dir and (Path(output_dir) / "dataset.json").exists():
            ds_file = Path(output_dir) / "dataset.json"
        elif ms_dir and (ms_dir / "dataset.json").exists():
            ds_file = ms_dir / "dataset.json"

        edges: List[Edge] = []
        dataset_methods = None

        if ds_file and ds_file.exists():
            edges = load_edges_from_dataset(ds_file)
            try:
                with open(ds_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    dataset_methods = data.get("methods")
            except Exception:
                pass
        elif mono_dir and mono_dir.exists():
            _, edges, dataset_methods = extract_codebase_operations_and_calls(mono_dir, partition)
        else:
            raise ValueError(
                "SM is a decomposition quality metric that requires a monolith call graph "
                "(provide a monolith codebase in codebases/monoliths/ or --dataset-path)."
            )

        clusters, get_cluster = resolve_partition_with_clusters(partition.microservices, dataset_methods)

        score, ms_scores = calculate_sm(get_cluster, clusters, edges, undirected=undirected)

        result = MetricResult(
            metric="SM",
            score=score,
            microservice_scores=ms_scores,
            metadata={
                "edges_analyzed": len(edges),
                "services_count": len(clusters),
                "undirected": undirected,
            },
        )

        if output_dir:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            partition.save_json(out_dir / "output.json")
            result.save_json(out_dir / "sm_score.json")

        return result
