"""Batch evaluation script for evaluating metrics across all systems in outputs/."""

import argparse
import sys
import time
from pathlib import Path

from fyp_cdq.config import OUTPUTS_DIR
from fyp_cdq.pipeline import EvaluationPipeline


def main():
    parser = argparse.ArgumentParser(description="Batch evaluator for metrics across all systems.")
    parser.add_argument("--metrics", nargs="+", default=["chd", "chm", "ifn"], help="Metrics to evaluate")
    parser.add_argument("--force", action="store_true", help="Force re-evaluation even if score file exists")
    args = parser.parse_args()

    pipeline = EvaluationPipeline()
    system_dirs = sorted([d for d in OUTPUTS_DIR.iterdir() if d.is_dir() and d.name.startswith("MS")])

    print(f"Discovered {len(system_dirs)} systems in {OUTPUTS_DIR}")
    print(f"Target metrics: {args.metrics}")

    results_summary = {m: {"success": 0, "failed": 0, "skipped": 0} for m in args.metrics}
    failures = []

    start_time = time.time()

    for idx, sys_dir in enumerate(system_dirs, 1):
        sys_id = sys_dir.name
        for metric in args.metrics:
            score_file = sys_dir / f"{metric.lower()}_score.json"
            if score_file.exists() and not args.force:
                results_summary[metric]["skipped"] += 1
                continue

            try:
                t0 = time.time()
                _, result = pipeline.evaluate(sys_id, metric, output_dir=sys_dir)
                elapsed = time.time() - t0
                results_summary[metric]["success"] += 1
                print(f"[{idx}/{len(system_dirs)}] {sys_id} {metric.upper()}: {result.score:.4f} ({elapsed:.2f}s)")
            except Exception as e:
                results_summary[metric]["failed"] += 1
                failures.append((sys_id, metric, str(e)))
                print(f"[{idx}/{len(system_dirs)}] {sys_id} {metric.upper()} FAILED: {e}")

    total_elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"Batch evaluation finished in {total_elapsed:.2f}s")
    for m, counts in results_summary.items():
        print(f"Metric {m.upper()}: {counts['success']} evaluated, {counts['skipped']} skipped, {counts['failed']} failed")
    if failures:
        print(f"\nFailures ({len(failures)}):")
        for sys_id, m, err in failures:
            print(f"  - {sys_id} [{m}]: {err}")
    print("=" * 60)


if __name__ == "__main__":
    main()
