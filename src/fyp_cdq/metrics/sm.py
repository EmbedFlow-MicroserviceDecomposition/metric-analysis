"""Structural Modularity (SM) decomposition quality metric evaluator."""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from fyp_cdq.extractors.agent_loader import (
    extraction_to_inter_service_edges,
    load_agent_extraction,
    resolve_agent_extraction_path,
)
from fyp_cdq.metrics.base import BaseMetric
from fyp_cdq.metrics.common import (
    Edge,
    extract_codebase_operations_and_calls,
    extract_intra_service_edges,
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
    Supports hybrid evaluation using static intra-service edges + LLM-extracted inter-service
    edges (`agent_extraction.json`), or monolith call graph evaluation (`mono_dir` / `dataset.json`).
    """

    name: str = "SM"
    needs_monolith: bool = False

    def parse_cli_args(self, args: List[str]) -> Dict[str, any]:
        parser = argparse.ArgumentParser(description="SM metric options", prog="sm")
        parser.add_argument("--dataset-path", type=str, default=None, help="Path to directory containing dataset.json")
        parser.add_argument("--extraction-path", type=str, default=None, help="Path to agent_extraction.json")
        parser.add_argument("--undirected", action="store_true", help="Treat call graph edges as undirected")
        parsed, unknown = parser.parse_known_args(args)
        if unknown:
            raise ValueError(f"Unrecognized options for metric 'sm': {' '.join(unknown)}")
        return {
            "dataset_path": Path(parsed.dataset_path) if parsed.dataset_path else None,
            "extraction_path": Path(parsed.extraction_path) if parsed.extraction_path else None,
            "undirected": parsed.undirected,
        }

    def evaluate(
        self,
        partition: Partition,
        ms_dir: Path,
        mono_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        dataset_path: Optional[Path] = None,
        extraction_path: Optional[Path] = None,
        undirected: bool = False,
        **kwargs,
    ) -> MetricResult:
        # 1. Prioritize agent_extraction.json if provided or present in output_dir / ms_dir
        ext_file = resolve_agent_extraction_path(ms_dir=ms_dir, output_dir=output_dir, extraction_path=extraction_path)

        edges: List[Edge] = []
        dataset_methods = None
        extraction_source = "monolith"
        extra_meta = {}

        if ext_file and ext_file.exists():
            extraction = load_agent_extraction(ext_file)
            intra_edges = extract_intra_service_edges(ms_dir, partition)
            inter_edges = extraction_to_inter_service_edges(extraction)
            seen = set()
            for e in intra_edges + inter_edges:
                if e.src != e.dst and (e.src, e.dst) not in seen:
                    seen.add((e.src, e.dst))
                    edges.append(e)
            extraction_source = "agent_extraction"
            extra_meta = {
                "intra_edges_count": len(intra_edges),
                "inter_edges_count": len(inter_edges),
                "extractor_tool": extraction.extractor_tool,
            }
        else:
            # 2. Fallback to dataset.json or monolith call graph
            ds_file = None
            if dataset_path:
                ds_file = dataset_path if dataset_path.is_file() else (dataset_path / "dataset.json")
            elif mono_dir and (mono_dir / "dataset.json").exists():
                ds_file = mono_dir / "dataset.json"
            elif output_dir and (Path(output_dir) / "dataset.json").exists():
                ds_file = Path(output_dir) / "dataset.json"
            elif ms_dir and (ms_dir / "dataset.json").exists():
                ds_file = ms_dir / "dataset.json"

            if ds_file and ds_file.exists():
                edges = load_edges_from_dataset(ds_file)
                try:
                    with open(ds_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        dataset_methods = data.get("methods")
                except Exception:
                    pass
                extraction_source = "dataset_json"
            elif mono_dir and mono_dir.exists():
                _, edges, dataset_methods = extract_codebase_operations_and_calls(mono_dir, partition)
                extraction_source = "monolith"
            else:
                raise ValueError(
                    "Metric 'SM' requires either an 'agent_extraction.json' file or both monolith and microservice codebases "
                    "(provide agent_extraction.json in outputs/<MS_ID>/, a monolith in codebases/monoliths/, or --dataset-path)."
                )

        clusters, get_cluster = resolve_partition_with_clusters(partition.microservices, dataset_methods)

        score, ms_scores = calculate_sm(get_cluster, clusters, edges, undirected=undirected)

        result = MetricResult(
            metric="SM",
            score=score,
            microservice_scores=ms_scores,
            metadata={
                "extraction_source": extraction_source,
                "edges_analyzed": len(edges),
                "services_count": len(clusters),
                "undirected": undirected,
                **extra_meta,
            },
        )

        if output_dir:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            partition.save_json(out_dir / "output.json")
            result.save_json(out_dir / "sm_score.json")

        return result
