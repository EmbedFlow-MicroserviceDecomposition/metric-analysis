"""Cohesion at Message Level (CHM) metric evaluator."""

import argparse
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from fyp_cdq.metrics.base import BaseMetric
from fyp_cdq.metrics.common import (
    Operation,
    extract_codebase_operations_and_calls,
    jaccard_similarity,
    load_calls_from_dataset,
    pairwise_mean,
    published_ops,
    resolve_partition,
)
from fyp_cdq.models import MetricResult, Partition


def calculate_chm(get_cluster, clusters: Set[str], calls: List[Tuple[str, Operation]]) -> Tuple[float, Dict[str, float]]:
    """
    Cohesion at Message Level (CHM).
    Canonical formulation (Jin et al., TSE 2021):
    f_msg = (Jaccard(returns) + Jaccard(params)) / 2 over externally-invoked operations.
    Range [0, 1], higher is better.
    """
    def f_msg(a: Operation, b: Operation) -> float:
        return (jaccard_similarity({a.returns}, {b.returns}) + jaccard_similarity(a.params, b.params)) / 2.0

    ops_per_ms = published_ops(get_cluster, clusters, calls)
    active_ms = [cid for cid, ops in ops_per_ms.items() if len(ops) >= 2]
    if not active_ms:
        return 1.0, {cid: 1.0 for cid in clusters}

    microservice_scores = {}
    for cid in clusters:
        ops = ops_per_ms.get(cid, set())
        microservice_scores[cid] = pairwise_mean(ops, f_msg)

    overall_chm = sum(microservice_scores.values()) / len(clusters)
    return overall_chm, microservice_scores


class CHMMetric(BaseMetric):
    """
    Evaluator for Cohesion at Message Level (CHM).
    Can evaluate from source codebases directly or from an external dataset.json call graph.
    """

    name: str = "CHM"
    needs_monolith: bool = False

    def parse_cli_args(self, args: List[str]) -> Dict[str, any]:
        parser = argparse.ArgumentParser(description="CHM metric options", prog="chm")
        parser.add_argument("--dataset-path", type=str, default=None, help="Path to directory containing dataset.json")
        parsed, unknown = parser.parse_known_args(args)
        if unknown:
            raise ValueError(f"Unrecognized options for metric 'chm': {' '.join(unknown)}")
        return {"dataset_path": Path(parsed.dataset_path) if parsed.dataset_path else None}

    def evaluate(
        self,
        partition: Partition,
        ms_dir: Path,
        mono_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        dataset_path: Optional[Path] = None,
        **kwargs,
    ) -> MetricResult:
        # 1. Resolve dataset.json if provided or present
        ds_file = None
        if dataset_path:
            ds_file = dataset_path if dataset_path.is_file() else (dataset_path / "dataset.json")
        elif output_dir and (Path(output_dir) / "dataset.json").exists():
            ds_file = Path(output_dir) / "dataset.json"
        elif (ms_dir / "dataset.json").exists():
            ds_file = ms_dir / "dataset.json"
        elif mono_dir and (mono_dir / "dataset.json").exists():
            ds_file = mono_dir / "dataset.json"

        calls: List[Tuple[str, Operation]] = []
        dataset_methods = None

        if ds_file and ds_file.exists():
            calls, dataset_methods = load_calls_from_dataset(ds_file)
        else:
            search_codebase = mono_dir if mono_dir and mono_dir.exists() else ms_dir
            calls, _, dataset_methods = extract_codebase_operations_and_calls(search_codebase, partition)

        clusters = set(partition.microservices.keys())
        get_cluster = resolve_partition(partition.microservices, dataset_methods)

        score, ms_scores = calculate_chm(get_cluster, clusters, calls)

        result = MetricResult(
            metric="CHM",
            score=score,
            microservice_scores=ms_scores,
            metadata={
                "calls_analyzed": len(calls),
                "services_count": len(clusters),
            },
        )

        if output_dir:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            partition.save_json(out_dir / "output.json")
            result.save_json(out_dir / "chm_score.json")

        return result
