"""Unit tests for CHM (Cohesion at Message level) metric evaluator."""

import json
from pathlib import Path
import pytest
from fyp_cdq.metrics.chm import CHMMetric, calculate_chm
from fyp_cdq.metrics.common import Operation
from fyp_cdq.models import Partition


def test_calculate_chm_identical_signatures():
    def get_cluster(name):
        return "svc1" if "A" in name else "svc2"

    clusters = {"svc1", "svc2"}
    calls = [
        ("svc2_caller", Operation(cls="A", name="getFoo", params=("String", "int"), returns="Foo")),
        ("svc2_caller", Operation(cls="A", name="findFoo", params=("String", "int"), returns="Foo"))
    ]
    score, ms_scores = calculate_chm(get_cluster, clusters, calls)
    assert ms_scores["svc1"] == 1.0
    assert ms_scores["svc2"] == 1.0
    assert score == 1.0


def test_calculate_chm_disjoint_signatures():
    def get_cluster(name):
        return "svc1" if "A" in name else "svc2"

    clusters = {"svc1", "svc2"}
    calls = [
        ("svc2_caller", Operation(cls="A", name="getFoo", params=("String",), returns="Foo")),
        ("svc2_caller", Operation(cls="A", name="getBar", params=("int",), returns="Bar"))
    ]
    score, ms_scores = calculate_chm(get_cluster, clusters, calls)
    # Jaccard params: 0, Jaccard returns: 0 -> avg = 0.0 for svc1, 1.0 for svc2 -> overall = 0.5
    assert ms_scores["svc1"] == 0.0
    assert ms_scores["svc2"] == 1.0
    assert score == 0.5


def test_calculate_chm_single_op():
    def get_cluster(name):
        return "svc1" if "A" in name else "svc2"

    clusters = {"svc1", "svc2"}
    calls = [
        ("svc2_caller", Operation(cls="A", name="getFoo", params=("String",), returns="Foo"))
    ]
    score, ms_scores = calculate_chm(get_cluster, clusters, calls)
    assert score == 1.0
    assert ms_scores["svc1"] == 1.0
    assert ms_scores["svc2"] == 1.0


def test_chm_metric_evaluate_with_dataset(tmp_path: Path):
    dataset = {
        "methods": {
            "m1": {"package": "pkg", "class": "SvcA", "method_name": "op1", "parameters": ["int"], "return_type": "String"},
            "m2": {"package": "pkg", "class": "SvcA", "method_name": "op2", "parameters": ["int"], "return_type": "String"},
            "caller": {"package": "pkg", "class": "SvcB", "method_name": "call", "calls": ["m1", "m2"]}
        }
    }
    dataset_file = tmp_path / "dataset.json"
    with open(dataset_file, "w") as f:
        json.dump(dataset, f)

    partition = Partition(
        microservices={
            "svc1": ["pkg.SvcA"],
            "svc2": ["pkg.SvcB"]
        },
        system_name="TestSystem"
    )

    metric = CHMMetric()
    result = metric.evaluate(partition, ms_dir=tmp_path, output_dir=tmp_path)

    assert result.metric == "CHM"
    assert result.score == 1.0
    assert (tmp_path / "chm_score.json").exists()
