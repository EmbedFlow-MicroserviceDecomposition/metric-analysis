"""Evaluation pipeline for microservice systems."""

import json
from pathlib import Path
from typing import List, Optional, Tuple

from fyp_cdq.config import MICROSERVICES_DIR, MICROSERVICES_JSON, MONOLITHS_DIR, MONOLITHS_JSON, OUTPUTS_DIR
from fyp_cdq.extractors.service_detector import ServiceDetector
from fyp_cdq.metrics.registry import registry
from fyp_cdq.models import MetricResult, Partition


def resolve_system_codebase(target: str) -> Tuple[str, Path]:
    """
    Resolves a system identifier or path to (system_id, codebase_path).
    Prioritizes microservices.json lookup before filesystem directory search.
    Raises FileNotFoundError if the target cannot be located.
    """
    # 1. Check microservices.json manifest
    if MICROSERVICES_JSON.exists():
        try:
            with open(MICROSERVICES_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            if target in data:
                entry = data[target]
                rel_path = entry.get("path", target)
                full_path = (MICROSERVICES_DIR / rel_path).resolve()
                if full_path.is_dir():
                    return target, full_path
        except Exception:
            pass

    # 2. Check if target is a direct existing path
    target_path = Path(target)
    if target_path.is_dir():
        system_id = target_path.name.split("_")[0]
        return system_id, target_path.resolve()

    # 3. Search in codebases/microservices/
    if MICROSERVICES_DIR.exists():
        exact = MICROSERVICES_DIR / target
        if exact.is_dir():
            return target, exact.resolve()

        matches = [d for d in MICROSERVICES_DIR.iterdir() if d.is_dir() and d.name.startswith(f"{target}_")]
        if matches:
            return target, matches[0].resolve()

    available = []
    if MICROSERVICES_DIR.exists():
        available = [d.name.split("_")[0] for d in MICROSERVICES_DIR.iterdir() if d.is_dir()]
    avail_str = f" Available systems: {', '.join(sorted(available))}" if available else ""
    raise FileNotFoundError(
        f"Microservice system '{target}' not found in {MICROSERVICES_DIR}.{avail_str}"
    )


def resolve_monolith_codebase(system_id: str) -> Optional[Path]:
    """
    Locates a monolith codebase in codebases/monoliths/ matching the system ID (e.g. MS001_...).
    Prioritizes monoliths.json manifest before directory matching.
    """
    # 1. Check monoliths.json manifest
    if MONOLITHS_JSON.exists():
        try:
            with open(MONOLITHS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            if system_id in data:
                entry = data[system_id]
                rel_path = entry.get("path", system_id)
                full_path = (MONOLITHS_DIR / rel_path).resolve()
                if full_path.is_dir():
                    return full_path
        except Exception:
            pass

    # 2. Search in codebases/monoliths/
    if not MONOLITHS_DIR.exists():
        return None

    exact = MONOLITHS_DIR / system_id
    if exact.is_dir():
        return exact.resolve()

    matches = [d for d in MONOLITHS_DIR.iterdir() if d.is_dir() and d.name.startswith(f"{system_id}_")]
    if matches:
        return matches[0].resolve()

    return None


class EvaluationPipeline:
    """Orchestrates evaluation of a single microservice system and metric."""

    def __init__(
        self,
        output_base_dir: Path = OUTPUTS_DIR,
        service_detector: Optional[ServiceDetector] = None,
    ):
        self.output_base_dir = output_base_dir
        self.service_detector = service_detector or ServiceDetector()

    def evaluate(
        self,
        system_target: str,
        metric_name: str,
        metric_args: Optional[List[str]] = None,
        output_dir: Optional[Path] = None,
        **kwargs,
    ) -> Tuple[Partition, MetricResult]:
        """
        Evaluates a single metric on a single microservice system.
        Parses metric_args via the target metric implementation.
        Raises ValueError or FileNotFoundError if unsupported or missing.
        """
        # 1. Resolve microservice codebase
        system_id, ms_path = resolve_system_codebase(system_target)

        # 2. Check metric support
        metric_impl = registry.get(metric_name)
        if not metric_impl:
            supported = ", ".join(registry.list_metrics())
            raise ValueError(
                f"Unsupported metric '{metric_name}'. Supported metrics: {supported}"
            )

        # 3. Parse metric-specific CLI arguments
        metric_kwargs = {}
        if metric_args:
            metric_kwargs = metric_impl.parse_cli_args(metric_args)
        metric_kwargs.update(kwargs)

        # 4. Check if monolith is required
        mono_path = None
        if metric_impl.needs_monolith:
            mono_path = resolve_monolith_codebase(system_id)
            has_dataset = bool(metric_kwargs.get("dataset_path"))
            if not has_dataset and (not mono_path or not mono_path.exists()):
                raise ValueError(
                    f"Metric '{metric_name}' requires both monolith and microservice codebases, "
                    f"but monolith codebase was not found for '{system_id}' in {MONOLITHS_DIR}."
                )
        else:
            try:
                mono_path = resolve_monolith_codebase(system_id)
            except Exception:
                mono_path = None

        # 5. Output directory
        out_dir = output_dir or (self.output_base_dir / system_id)
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # 6. Extract microservice partition (prioritizing existing output.json, then detection)
        cached_partition = out_dir / "output.json"
        if cached_partition.exists():
            partition = Partition.from_json(cached_partition)
        else:
            partition = self.service_detector.detect_and_extract(ms_path, system_name=system_id)
            if partition.service_count == 0 or partition.total_classes == 0:
                raise RuntimeError(f"No classes or microservices detected in {ms_path}")
            partition.save_json(cached_partition)

        # 7. Evaluate metric
        result = metric_impl.evaluate(
            partition=partition,
            ms_dir=ms_path,
            mono_dir=mono_path,
            output_dir=out_dir,
            **metric_kwargs,
        )

        return partition, result
