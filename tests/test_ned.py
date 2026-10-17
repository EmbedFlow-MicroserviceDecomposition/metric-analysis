"""Unit tests for NED metric evaluator."""

import pytest
from fyp_cdq.metrics.ned import NEDMetric, calculate_ned
from fyp_cdq.models import Partition


def test_calculate_ned_balanced():
    # 3 clusters of sizes 10, 10, 10 (all within [5, 20])
    partition = {}
    for i in range(10):
        partition[f"c1_{i}"] = "svc1"
    for i in range(10):
        partition[f"c2_{i}"] = "svc2"
    for i in range(10):
        partition[f"c3_{i}"] = "svc3"

    score, score_rel, ms_scores = calculate_ned(partition, lo=5, hi=20, eps=0.5)
    assert score == 1.0
    assert score_rel == 1.0
    assert ms_scores == {"svc1": 1.0, "svc2": 1.0, "svc3": 1.0}


def test_calculate_ned_all_extreme():
    # 2 singletons (size 1 < 5) and 1 god service (size 30 > 20)
    partition = {
        "s1": "svc1",
        "s2": "svc2",
    }
    for i in range(30):
        partition[f"g_{i}"] = "svc3"

    score, score_rel, ms_scores = calculate_ned(partition, lo=5, hi=20, eps=0.5)
    # Total = 32, all extreme, so fixed NED = 0.0
    assert score == 0.0
    assert ms_scores == {"svc1": 0.0, "svc2": 0.0, "svc3": 0.0}


def test_calculate_ned_empty():
    score, score_rel, ms_scores = calculate_ned({}, lo=5, hi=20, eps=0.5)
    assert score == 0.0
    assert score_rel == 0.0
    assert ms_scores == {}


def test_ned_metric_evaluate(tmp_path):
    metric = NEDMetric(lo=5, hi=20, eps=0.5)
    partition = Partition(
        microservices={
            "svc1": [f"ClassA_{i}" for i in range(10)], # non-extreme (10)
            "svc2": ["ClassB_0"]                         # extreme (1)
        },
        system_name="TestSystem"
    )
    result = metric.evaluate(partition, ms_dir=tmp_path, output_dir=tmp_path)
    # Total classes = 11, extreme count = 1 -> fixed NED = 1 - 1/11 = 10/11 ≈ 0.9091
    assert pytest.approx(result.score, 0.0001) == 10 / 11
    assert result.microservice_scores["svc1"] == 1.0
    assert result.microservice_scores["svc2"] == 0.0

    # Verify JSON files saved
    assert (tmp_path / "output.json").exists()
    assert (tmp_path / "ned_score.json").exists()
