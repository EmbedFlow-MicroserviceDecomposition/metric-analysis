#!/usr/bin/env python3
"""CLI utility to evaluate a decomposition metric on a microservice system."""

import sys
from pathlib import Path

# Add project src to path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from fyp_cdq.pipeline import EvaluationPipeline


def main():
    if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"):
        print("Usage: uv run python scripts/run_eval.py <system_id> <metric> [metric_options...]", file=sys.stderr)
        print("Example: uv run python scripts/run_eval.py MS010 ned --lo 3 --eps 0.25", file=sys.stderr)
        sys.exit(1 if sys.argv[1:2] not in (["-h"], ["--help"]) else 0)

    system_target = sys.argv[1]
    metric_name = sys.argv[2]
    metric_args = sys.argv[3:]

    pipeline = EvaluationPipeline()

    try:
        partition, result = pipeline.evaluate(
            system_target=system_target,
            metric_name=metric_name,
            metric_args=metric_args,
        )
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Print results
    out_dir = pipeline.output_base_dir / partition.system_name
    print("\n========================================================")
    print(f"System: {partition.system_name}")
    print(f"Metric: {result.metric}")
    if result.bounds:
        bounds_str = ", ".join(f"{k}={v}" for k, v in result.bounds.items())
        print(f"Parameters: {bounds_str}")
    print(f"Services Detected: {partition.service_count}")
    print(f"Total Classes: {partition.total_classes}")
    print(f"Score (Fixed): {result.score:.4f}")
    if result.score_relative is not None:
        print(f"Score (Relative): {result.score_relative:.4f}")
    print(f"Saved partition to: {out_dir / 'output.json'}")
    print(f"Saved score to:     {out_dir / f'{result.metric.lower()}_score.json'}")
    print("========================================================\n")


if __name__ == "__main__":
    main()
