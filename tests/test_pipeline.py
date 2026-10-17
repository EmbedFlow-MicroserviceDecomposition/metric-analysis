"""Unit tests for EvaluationPipeline."""

from pathlib import Path
from typing import Optional
import pytest
from fyp_cdq.metrics.base import BaseMetric
from fyp_cdq.metrics.registry import registry
from fyp_cdq.models import MetricResult, Partition
from fyp_cdq.pipeline import EvaluationPipeline


def test_pipeline_evaluate_ms001(tmp_path: Path):
    pipeline = EvaluationPipeline(output_base_dir=tmp_path)
    partition, result = pipeline.evaluate("MS001", "ned", output_dir=tmp_path)
    assert partition.service_count > 0
    assert partition.total_classes > 0
    assert result.metric == "NED"
    assert result.score > 0.0
    assert (tmp_path / "output.json").exists()
    assert (tmp_path / "ned_score.json").exists()


def test_pipeline_evaluate_with_args(tmp_path: Path):
    pipeline = EvaluationPipeline(output_base_dir=tmp_path)
    partition, result = pipeline.evaluate("MS010", "ned", metric_args=["--lo", "3", "--eps", "0.25"], output_dir=tmp_path)
    assert partition.service_count == 5
    assert result.bounds["lo"] == 3
    assert result.bounds["eps"] == 0.25
    assert result.score == 1.0


def test_pipeline_unsupported_system():
    pipeline = EvaluationPipeline()
    with pytest.raises(FileNotFoundError, match="not found in"):
        pipeline.evaluate("MS999", "ned")


def test_pipeline_unsupported_metric():
    pipeline = EvaluationPipeline()
    with pytest.raises(ValueError, match="Unsupported metric"):
        pipeline.evaluate("MS001", "unknown_metric")


def test_pipeline_unrecognized_metric_arg():
    pipeline = EvaluationPipeline()
    with pytest.raises(ValueError, match="Unrecognized options for metric 'ned'"):
        pipeline.evaluate("MS001", "ned", metric_args=["--invalid-flag", "123"])


def test_pipeline_requires_monolith_missing():
    # Register a dummy metric that requires monolith
    class DummyDualMetric(BaseMetric):
        name = "DUAL_MOCK"
        needs_monolith = True
        def evaluate(self, partition: Partition, ms_dir: Path, mono_dir: Optional[Path] = None, output_dir: Optional[Path] = None, **kwargs) -> MetricResult:
            return MetricResult(metric="DUAL_MOCK", score=1.0)

    registry.register(DummyDualMetric())
    pipeline = EvaluationPipeline()
    with pytest.raises(ValueError, match="requires both monolith and microservice codebases"):
        pipeline.evaluate("MS001", "dual_mock")
