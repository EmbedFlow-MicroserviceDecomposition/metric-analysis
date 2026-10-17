"""Unit tests for data models."""

from pathlib import Path
from fyp_cdq.models import MicroserviceSystem, Partition, MetricResult


def test_microservice_system_model(tmp_path: Path):
    sys_obj = MicroserviceSystem(
        system_id="MS010",
        name="MS010_amazon-ecs",
        path=tmp_path
    )
    assert sys_obj.system_id == "MS010"
    assert sys_obj.name == "MS010_amazon-ecs"
    assert sys_obj.path == tmp_path
    assert sys_obj.monolith_path is None


def test_partition_metrics():
    p = Partition(
        microservices={
            "svc1": ["A", "B"],
            "svc2": ["C", "D", "E"]
        },
        system_name="Test"
    )
    assert p.total_classes == 5
    assert p.service_count == 2
    assert p.sizes == {"svc1": 2, "svc2": 3}


def test_metric_result_serialization(tmp_path: Path):
    mr = MetricResult(
        metric="NED",
        score=0.95,
        score_relative=0.43,
        bounds={"lo": 5, "hi": 20, "eps": 0.5},
        microservice_scores={"svc1": 1.0}
    )
    out_file = tmp_path / "ned_score.json"
    mr.save_json(out_file)
    assert out_file.exists()
