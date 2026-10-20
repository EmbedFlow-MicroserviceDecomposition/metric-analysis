"""Cohesion at Domain Level (CHD) metric evaluator."""

import argparse
from pathlib import Path
import re
from typing import Dict, List, Optional, Set, Tuple

from fyp_cdq.metrics.base import BaseMetric
from fyp_cdq.metrics.common import (
    Operation,
    extract_codebase_operations_and_calls,
    extract_microservice_published_ops,
    jaccard_similarity,
    load_calls_from_dataset,
    pairwise_mean,
    published_ops,
    resolve_partition,
)
from fyp_cdq.models import MetricResult, Partition


_NON_DOMAIN = {
    "void", "int", "long", "short", "byte", "float", "double", "boolean", "bool",
    "char", "string", "str", "list", "map", "set", "collection", "object", "any",
    "integer", "optional", "iterable", "dict", "tuple", "none", "unit", "term",
}


def extract_terms(op: Operation) -> Set[str]:
    """Extracts domain terms from an operation's name, parameter types, and return type."""
    words = []
    names = [op.name] + [p.split(".")[-1] for p in op.params]
    names.append(op.returns.split(".")[-1])
    for name in names:
        words.extend(re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", name))
    return {w.lower() for w in words} - _NON_DOMAIN


def calculate_chd(
    get_cluster,
    clusters: Set[str],
    calls: List[Tuple[str, Operation]],
    ops_per_ms: Optional[Dict[str, Set[Operation]]] = None,
) -> Tuple[float, Dict[str, float]]:
    """
    Cohesion at Domain Level (CHD).
    Mean over partitions of the mean pairwise Jaccard similarity of domain terms in operation signatures.
    Range [0, 1], higher is better.
    """
    def f_dom(a: Operation, b: Operation) -> float:
        return jaccard_similarity(extract_terms(a), extract_terms(b))

    if ops_per_ms is None:
        ops_per_ms = published_ops(get_cluster, clusters, calls)

    active_ms = [cid for cid, ops in ops_per_ms.items() if len(ops) >= 2]
    if not active_ms:
        return 1.0, {cid: 1.0 for cid in clusters}

    microservice_scores = {}
    for cid in clusters:
        ops = ops_per_ms.get(cid, set())
        microservice_scores[cid] = pairwise_mean(ops, f_dom)

    overall_chd = sum(microservice_scores.values()) / len(clusters)
    return overall_chd, microservice_scores


class CHDMetric(BaseMetric):
    """
    Evaluator for Cohesion at Domain Level (CHD).
    Extracts published operations per microservice directly from the microservice codebase,
    or from cross-partition calls when a monolith or dataset.json call graph is provided.
    """

    name: str = "CHD"
    needs_monolith: bool = False

    def parse_cli_args(self, args: List[str]) -> Dict[str, any]:
        parser = argparse.ArgumentParser(description="CHD metric options", prog="chd")
        parser.add_argument("--dataset-path", type=str, default=None, help="Path to directory containing dataset.json")
        parsed, unknown = parser.parse_known_args(args)
        if unknown:
            raise ValueError(f"Unrecognized options for metric 'chd': {' '.join(unknown)}")
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
        ds_file = None
        if dataset_path:
            ds_file = dataset_path if dataset_path.is_file() else (dataset_path / "dataset.json")
        elif output_dir and (Path(output_dir) / "dataset.json").exists():
            ds_file = Path(output_dir) / "dataset.json"
        elif (ms_dir / "dataset.json").exists():
            ds_file = ms_dir / "dataset.json"
        elif mono_dir and (mono_dir / "dataset.json").exists():
            ds_file = mono_dir / "dataset.json"

        clusters = set(partition.microservices.keys())
        calls: List[Tuple[str, Operation]] = []
        ops_per_ms: Optional[Dict[str, Set[Operation]]] = None

        if ds_file and ds_file.exists():
            calls, dataset_methods = load_calls_from_dataset(ds_file)
            get_cluster = resolve_partition(partition.microservices, dataset_methods)
            ops_per_ms = published_ops(get_cluster, clusters, calls)
        elif mono_dir and mono_dir.exists():
            calls, _, dataset_methods = extract_codebase_operations_and_calls(mono_dir, partition)
            get_cluster = resolve_partition(partition.microservices, dataset_methods)
            ops_per_ms = published_ops(get_cluster, clusters, calls)
        else:
            get_cluster = resolve_partition(partition.microservices)
            ops_per_ms = extract_microservice_published_ops(ms_dir, partition)

        score, ms_scores = calculate_chd(get_cluster, clusters, calls, ops_per_ms=ops_per_ms)
        total_ops = sum(len(ops) for ops in ops_per_ms.values()) if ops_per_ms else 0

        result = MetricResult(
            metric="CHD",
            score=score,
            microservice_scores=ms_scores,
            metadata={
                "calls_analyzed": len(calls) if calls else total_ops,
                "published_operations_count": total_ops,
                "services_count": len(clusters),
            },
        )

        if output_dir:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            partition.save_json(out_dir / "output.json")
            result.save_json(out_dir / "chd_score.json")

        return result
