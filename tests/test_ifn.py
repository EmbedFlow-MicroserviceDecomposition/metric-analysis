"""Unit tests for IFN (Interface Number) decomposition quality metric evaluator."""

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
        Edge(src="A", dst="B", type="CALL")
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
        # 2 different classes of svc1 called by svc2
        Edge(src="svc2_caller1", dst="svc1_cls1", type="CALL"),
        Edge(src="svc2_caller2", dst="svc1_cls2", type="CALL"),
        # duplicate call to cls1 should not increase interface count
        Edge(src="svc2_caller3", dst="svc1_cls1", type="CALL"),
        # 1 class of svc2 called by svc1
        Edge(src="svc1_caller1", dst="svc2_cls1", type="CALL"),
    ]
    score, ms_scores = calculate_ifn(get_cluster, clusters, edges)
    assert ms_scores["svc1"] == 2.0
    assert ms_scores["svc2"] == 1.0
    # Average over 2 services: (2 + 1) / 2 = 1.5
    assert score == 1.5


def test_ifn_metric_evaluate_with_dataset(tmp_path: Path):
    dataset = {
        "edges": [
            {"src": "pkg.SvcB", "dst": "pkg.SvcA1", "type": "CALL"},
            {"src": "pkg.SvcB", "dst": "pkg.SvcA2", "type": "CALL"}
        ]
    }
    dataset_file = tmp_path / "dataset.json"
    with open(dataset_file, "w") as f:
        json.dump(dataset, f)

    partition = Partition(
        microservices={
            "svc1": ["pkg.SvcA1", "pkg.SvcA2"],
            "svc2": ["pkg.SvcB"]
        },
        system_name="TestSystem"
    )

    metric = IFNMetric()
    assert metric.needs_monolith is True
    result = metric.evaluate(partition, ms_dir=tmp_path, output_dir=tmp_path)

    assert result.metric == "IFN"
    # svc1 exposes 2 class interfaces, svc2 exposes 0 -> avg = 1.0
    assert result.score == 1.0
    assert result.microservice_scores["svc1"] == 2.0
    assert result.microservice_scores["svc2"] == 0.0
    assert (tmp_path / "ifn_score.json").exists()


def test_ifn_metric_evaluate_with_monolith_source(tmp_path: Path):
    mono_dir = tmp_path / "monolith"
    mono_dir.mkdir()
    (mono_dir / "OrderService.java").write_text(
        "package com.app.order;\n"
        "import com.app.billing.BillingService;\n"
        "import com.app.inventory.InventoryService;\n"
        "public class OrderService {\n"
        "    private BillingService billing;\n"
        "    private InventoryService inventory;\n"
        "    public void checkout() {\n"
        "        billing.charge();\n"
        "        inventory.reserve();\n"
        "    }\n"
        "}\n"
    )
    (mono_dir / "BillingService.java").write_text(
        "package com.app.billing;\n"
        "public class BillingService {\n"
        "    public void charge() {}\n"
        "}\n"
    )
    (mono_dir / "InventoryService.java").write_text(
        "package com.app.inventory;\n"
        "public class InventoryService {\n"
        "    public void reserve() {}\n"
        "}\n"
    )

    partition = Partition(
        microservices={
            "order-ms": ["com.app.order.OrderService"],
            "billing-ms": ["com.app.billing.BillingService"],
            "inventory-ms": ["com.app.inventory.InventoryService"],
        },
        system_name="TestMono",
    )

    out_dir = tmp_path / "out"
    metric = IFNMetric()
    result = metric.evaluate(partition, ms_dir=mono_dir, mono_dir=mono_dir, output_dir=out_dir)

    assert result.metric == "IFN"
    assert result.microservice_scores["order-ms"] == 0.0
    assert result.microservice_scores["billing-ms"] == 1.0
    assert result.microservice_scores["inventory-ms"] == 1.0
    assert result.score == pytest.approx(2.0 / 3.0)
