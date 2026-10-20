"""Interface Number (IFN) decomposition quality metric evaluator."""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from fyp_cdq.metrics.base import BaseMetric
from fyp_cdq.metrics.common import (
    Edge,
    extract_codebase_operations_and_calls,
    load_edges_from_dataset,
    resolve_partition,
)
from fyp_cdq.models import MetricResult, Partition


def calculate_ifn(get_cluster, clusters: Set[str], edges: List[Edge]) -> Tuple[float, Dict[str, float]]:
    """
    Interface Number (IFN).
    Measures the average number of distinct exposed interfaces (target classes in microservice j
    invoked by classes in microservice i != j in the monolith call graph) across all microservices.
    Range [0, inf), lower is better.
    """
    K = len(clusters)
    if K == 0:
        return 0.0, {}

    interfaces_per_ms = {cid: set() for cid in clusters}

    for e in edges:
        edge_type = (e.type or "").upper()
        if edge_type not in ("CALL", "STATIC_CALL"):
            continue
        ci, cj = get_cluster(e.src), get_cluster(e.dst)
        if ci is None or cj is None or ci == cj:
            continue
        if cj in interfaces_per_ms:
            interfaces_per_ms[cj].add(e.dst)

    microservice_scores = {cid: float(len(ifaces)) for cid, ifaces in interfaces_per_ms.items()}
    overall_ifn = sum(microservice_scores.values()) / K
    return overall_ifn, microservice_scores


class IFNMetric(BaseMetric):
    """
    Evaluator for Interface Number (IFN).
    Decomposition quality metric: requires the monolith call graph (either via a monolith
    codebase `mono_dir` or an external `dataset.json`) and a microservice partition.
    """

    name: str = "IFN"
    needs_monolith: bool = True

    def parse_cli_args(self, args: List[str]) -> Dict[str, any]:
        parser = argparse.ArgumentParser(description="IFN metric options", prog="ifn")
        parser.add_argument("--dataset-path", type=str, default=None, help="Path to directory containing dataset.json")
        parsed, unknown = parser.parse_known_args(args)
        if unknown:
            raise ValueError(f"Unrecognized options for metric 'ifn': {' '.join(unknown)}")
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
                "IFN is a decomposition quality metric that requires a monolith call graph "
                "(provide a monolith codebase in codebases/monoliths/ or --dataset-path)."
            )

        clusters = set(partition.microservices.keys())
        get_cluster = resolve_partition(partition.microservices, dataset_methods)

        score, ms_scores = calculate_ifn(get_cluster, clusters, edges)

        result = MetricResult(
            metric="IFN",
            score=score,
            microservice_scores=ms_scores,
            metadata={
                "edges_analyzed": len(edges),
                "services_count": len(clusters),
            },
        )

        if output_dir:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            partition.save_json(out_dir / "output.json")
            result.save_json(out_dir / "ifn_score.json")

        return result
