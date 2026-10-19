"""Non-Extreme Distribution (NED) metric evaluator."""

import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fyp_cdq.config import DEFAULT_NED_EPS, DEFAULT_NED_HI, DEFAULT_NED_LO
from fyp_cdq.metrics.base import BaseMetric
from fyp_cdq.models import MetricResult, Partition


def calculate_ned(
    partition: Dict[str, str],
    lo: int = DEFAULT_NED_LO,
    hi: int = DEFAULT_NED_HI,
    eps: float = DEFAULT_NED_EPS,
) -> Tuple[float, float, Dict[str, float]]:
    """
    Non-Extreme Distribution (NED) calculation.

    Fixed bounds NED:
        1 - (#non-extreme-sized partitions / total partitions)
        where a partition is non-extreme if lo <= size <= hi.

    Relative bounds NED (CHGNN variant):
        1 - (#relative-non-extreme partitions / total partitions)
        where a partition is non-extreme if floor(avg*(1-eps)) <= size <= ceil(avg*(1+eps)),
        and avg = total_classes / total_partitions.

    Lower is better. Range: [0.0, 1.0].
    (0.0 = perfect balance, 1.0 = completely extreme partitions).
    """
    clusters: Dict[str, set] = {}
    for cls, cid in partition.items():
        clusters.setdefault(cid, set()).add(cls)

    total_classes = len(partition)
    total_partitions = len(clusters)
    if total_classes == 0 or total_partitions == 0:
        return 0.0, 0.0, {}

    sizes = {cid: len(members) for cid, members in clusters.items()}

    # 1. Fixed bounds NED: 1 - (#non-extreme partitions / total partitions)
    non_extreme_count = sum(1 for size in sizes.values() if lo <= size <= hi)
    overall_ned = 1.0 - (non_extreme_count / total_partitions)

    # 2. Relative bounds NED (CHGNN variant): 1 - (#relative-non-extreme partitions / total partitions)
    avg = total_classes / total_partitions
    rel_lo = math.floor(avg * (1.0 - eps))
    rel_hi = math.ceil(avg * (1.0 + eps))
    non_extreme_rel_count = sum(1 for size in sizes.values() if rel_lo <= size <= rel_hi)
    overall_ned_relative = 1.0 - (non_extreme_rel_count / total_partitions)

    # Microservice level binary indicator (0.0 if balanced/non-extreme, 1.0 if extreme)
    microservice_scores = {}
    for cid, size in sizes.items():
        is_extreme = 0.0 if (lo <= size <= hi) else 1.0
        microservice_scores[cid] = is_extreme

    return overall_ned, overall_ned_relative, microservice_scores


class NEDMetric(BaseMetric):
    """
    Evaluator for Non-Extreme Distribution (NED).
    Only requires the microservice codebase.
    """

    name: str = "NED"
    needs_monolith: bool = False

    def __init__(
        self,
        lo: int = DEFAULT_NED_LO,
        hi: int = DEFAULT_NED_HI,
        eps: float = DEFAULT_NED_EPS,
    ):
        self.lo = lo
        self.hi = hi
        self.eps = eps

    def parse_cli_args(self, args: List[str]) -> Dict[str, any]:
        import argparse
        parser = argparse.ArgumentParser(description="NED metric options", prog="ned")
        parser.add_argument("--lo", type=int, default=self.lo, help=f"NED lower non-extreme bound (default: {self.lo})")
        parser.add_argument("--hi", type=int, default=self.hi, help=f"NED upper non-extreme bound (default: {self.hi})")
        parser.add_argument("--eps", type=float, default=self.eps, help=f"NED relative bound epsilon (default: {self.eps})")
        parsed, unknown = parser.parse_known_args(args)
        if unknown:
            raise ValueError(f"Unrecognized options for metric 'ned': {' '.join(unknown)}")
        return {"lo": parsed.lo, "hi": parsed.hi, "eps": parsed.eps}

    def evaluate(
        self,
        partition: Partition,
        ms_dir: Path,
        mono_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        lo: Optional[int] = None,
        hi: Optional[int] = None,
        eps: Optional[float] = None,
        **kwargs,
    ) -> MetricResult:
        bound_lo = lo if lo is not None else self.lo
        bound_hi = hi if hi is not None else self.hi
        bound_eps = eps if eps is not None else self.eps

        # Flatten microservices dict {service_name: [classes]} to {class: service_name}
        flat_partition = {}
        for cid, members in partition.microservices.items():
            for m in members:
                flat_partition[m] = cid

        score, score_rel, ms_scores = calculate_ned(
            flat_partition, lo=bound_lo, hi=bound_hi, eps=bound_eps
        )

        result = MetricResult(
            metric="NED",
            score=score,
            score_relative=score_rel,
            bounds={"lo": bound_lo, "hi": bound_hi, "eps": bound_eps},
            microservice_scores=ms_scores,
            metadata={
                "total_classes": partition.total_classes,
                "service_count": partition.service_count,
                "service_sizes": partition.sizes,
            },
        )

        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            partition.save_json(output_dir / "output.json")
            result.save_json(output_dir / "ned_score.json")

        return result
