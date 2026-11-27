"""Computes NED, CHD, CHM, IFN and SM for every corpus system from its committed extraction.

Uses the v4.2 extraction when it exists, otherwise v4.0, for every system that has
services in the manifest. Results are written to benchmarks/metric_results/claude_code/.

Usage: uv run python scripts/run_corpus_eval.py
"""

import csv
import json
import shutil
import statistics

from fyp_cdq.config import BENCHMARKS_DIR, MICROSERVICES_JSON, PROJECT_ROOT
from fyp_cdq.pipeline import EvaluationPipeline

RUNS_DIR = BENCHMARKS_DIR / "corpus_runs" / "claude_code"
RESULTS_DIR = BENCHMARKS_DIR / "metric_results" / "claude_code"
METRICS = ["ned", "chd", "chm", "ifn", "sm"]


def main():
    manifest = json.loads(MICROSERVICES_JSON.read_text(encoding="utf-8"))
    pipeline = EvaluationPipeline()
    if RESULTS_DIR.exists():
        shutil.rmtree(RESULTS_DIR)

    rows, failures = [], []
    for system_id, entry in sorted(manifest.items()):
        services = entry.get("services")
        if not services:
            continue
        extraction = next(
            (p for v in ("v4.2", "v4") if (p := RUNS_DIR / v / f"{system_id}.json").is_file()),
            None,
        )
        if extraction is None:
            failures.append((system_id, "all", "no extraction file"))
            continue

        data = json.loads(extraction.read_text(encoding="utf-8"))
        calls = data["inter_service_calls"]
        row = {
            "system_id": system_id,
            "name": entry.get("name", ""),
            "language": entry.get("language", ""),
            "extraction": extraction.relative_to(PROJECT_ROOT).as_posix(),
            "manifest_services": len(services),
            "interfaces": sum(len(s["exposed_interfaces"]) for s in data["microservices"].values()),
            "calls": len(calls),
            "services_under_2_interfaces": sum(
                len(s["exposed_interfaces"]) < 2 for s in data["microservices"].values()
            ),
        }

        out_dir = RESULTS_DIR / system_id
        for metric in METRICS:
            try:
                partition, result = pipeline.evaluate(
                    system_id, metric, output_dir=out_dir, extraction_path=extraction
                )
            except Exception as e:
                failures.append((system_id, metric, str(e)))
                continue
            missing = sorted(set(services) - set(partition.microservices))
            row["scored_services"] = partition.service_count
            row["classes"] = partition.total_classes
            row["services_without_classes"] = ";".join(missing)
            row["calls_touching_unscored_services"] = sum(
                c["src_service"] in missing or c["dst_service"] in missing for c in calls
            )
            row[metric] = round(result.score, 6)
            if metric == "ned":
                row["ned_relative"] = round(result.score_relative, 6)
            if metric == "sm":
                row["intra_edges"] = result.metadata.get("intra_edges_count")
                row["inter_edges"] = result.metadata.get("inter_edges_count")
        if "ned" not in row and out_dir.exists() and not any(out_dir.iterdir()):
            out_dir.rmdir()
        rows.append(row)
        print(system_id, {m: row.get(m) for m in METRICS}, flush=True)

    fields = [
        "system_id", "name", "language", "extraction", "manifest_services", "scored_services",
        "classes", "interfaces", "services_under_2_interfaces", "calls", "intra_edges", "inter_edges", "ned", "ned_relative",
        "chd", "chm", "ifn", "sm", "services_without_classes", "calls_touching_unscored_services",
    ]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "summary.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{len(rows)} systems")
    for metric in METRICS + ["ned_relative"]:
        values = [r[metric] for r in rows if metric in r]
        if values:
            print(
                f"{metric}: n={len(values)} mean={statistics.mean(values):.4f} "
                f"median={statistics.median(values):.4f} min={min(values):.4f} max={max(values):.4f}"
            )
    print(f"failures: {len(failures)}")
    for failure in failures:
        print("  ", *failure)


if __name__ == "__main__":
    main()
