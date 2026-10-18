"""Unit tests for IFN (Interface Number) metric evaluator."""

import json
from pathlib import Path
import pytest
from fyp_cdq.metrics.common import Edge
from fyp_cdq.metrics.ifn import IFNMetric, calculate_ifn
from fyp_cdq.models import Partition


def test_calculate_ifn_no_cross_edges():
    def get_cluster(name):
        return "svc1"

    clusters = {"svc1"}
    edges = [
        Edge(src="A.m1", dst="A.m2", type="CALL")
    ]
    score, ms_scores = calculate_ifn(get_cluster, clusters, edges)
    assert score == 0.0
    assert ms_scores["svc1"] == 0.0


def test_calculate_ifn_multiple_interfaces():
    def get_cluster(name):
        if "svc1" in name:
            return "svc1"
        return "svc2"

    clusters = {"svc1", "svc2"}
    edges = [
        # 2 different operations of svc1 called by svc2
        Edge(src="svc2_caller1", dst="svc1_op1", type="CALL"),
        Edge(src="svc2_caller2", dst="svc1_op2", type="CALL"),
        # duplicate call to op1 should not increase interface count
        Edge(src="svc2_caller3", dst="svc1_op1", type="CALL"),
        # 1 operation of svc2 called by svc1
        Edge(src="svc1_caller1", dst="svc2_op1", type="CALL"),
    ]
    score, ms_scores = calculate_ifn(get_cluster, clusters, edges)
    assert ms_scores["svc1"] == 2.0
    assert ms_scores["svc2"] == 1.0
    # Average over 2 services: (2 + 1) / 2 = 1.5
    assert score == 1.5


def test_ifn_metric_evaluate_with_dataset(tmp_path: Path):
    dataset = {
        "edges": [
            {"src": "pkg.SvcB", "dst": "pkg.SvcA.op1", "type": "CALL"},
            {"src": "pkg.SvcB", "dst": "pkg.SvcA.op2", "type": "CALL"}
        ]
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

    metric = IFNMetric()
    result = metric.evaluate(partition, ms_dir=tmp_path, output_dir=tmp_path)

    assert result.metric == "IFN"
    # svc1 exposes 2 ops, svc2 exposes 0 -> avg = 1.0
    assert result.score == 1.0
    assert result.microservice_scores["svc1"] == 2.0
    assert result.microservice_scores["svc2"] == 0.0
    assert (tmp_path / "ifn_score.json").exists()
