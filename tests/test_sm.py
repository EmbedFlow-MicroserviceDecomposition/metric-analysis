"""Unit tests for SM (Structural Modularity) decomposition quality metric evaluator."""

import json
from pathlib import Path
import pytest
from fyp_cdq.metrics.common import Edge, resolve_partition_with_clusters
from fyp_cdq.metrics.sm import SMMetric, calculate_sm
from fyp_cdq.models import Partition


def test_calculate_sm_pure_intra_cohesion():
    partition_map = {
        "svc1": ["pkg.A1", "pkg.A2"],
        "svc2": ["pkg.B1", "pkg.B2"],
    }
    clusters, get_cluster = resolve_partition_with_clusters(partition_map)
    edges = [
        Edge(src="pkg.A1", dst="pkg.A2", type="CALL"),
        Edge(src="pkg.B1", dst="pkg.B2", type="CALL"),
    ]
    score, ms_scores = calculate_sm(get_cluster, clusters, edges)
    # Each cluster has n_k=2, mu=1 -> intra = 1/4 = 0.25, inter = 0 -> SM = 0.25
    assert ms_scores["svc1"] == pytest.approx(0.25)
    assert ms_scores["svc2"] == pytest.approx(0.25)
    assert score == pytest.approx(0.25)


def test_calculate_sm_inter_coupling_penalty():
    partition_map = {
        "svc1": ["pkg.A1", "pkg.A2"],
        "svc2": ["pkg.B1", "pkg.B2"],
    }
    clusters, get_cluster = resolve_partition_with_clusters(partition_map)
    edges = [
        Edge(src="pkg.A1", dst="pkg.B1", type="CALL"),
    ]
    score, ms_scores = calculate_sm(get_cluster, clusters, edges)
    # No intra edges (intra=0), 1 inter edge -> inter_k = 1 / (2 * 2 * 2) = 1/8 = 0.125 -> SM = -0.125
    assert ms_scores["svc1"] == pytest.approx(-0.125)
    assert ms_scores["svc2"] == pytest.approx(-0.125)
    assert score == pytest.approx(-0.125)


def test_sm_metric_evaluate_with_monolith_source(tmp_path: Path):
    mono_dir = tmp_path / "monolith"
    mono_dir.mkdir()
    (mono_dir / "OrderController.java").write_text(
        "package com.app.order;\n"
        "import com.app.payment.PaymentService;\n"
        "public class OrderController {\n"
        "    private OrderService orderService;\n"
        "    private PaymentService paymentService;\n"
        "    public void createOrder() {\n"
        "        this.orderService.saveOrder();\n"
        "        this.paymentService.charge();\n"
        "    }\n"
        "}\n"
    )
    (mono_dir / "OrderService.java").write_text(
        "package com.app.order;\n"
        "public class OrderService {\n"
        "    public void saveOrder() {}\n"
        "}\n"
    )
    (mono_dir / "PaymentService.java").write_text(
        "package com.app.payment;\n"
        "public class PaymentService {\n"
        "    public void charge() {}\n"
        "}\n"
    )

    partition = Partition(
        microservices={
            "order-ms": ["com.app.order.OrderController", "com.app.order.OrderService"],
            "payment-ms": ["com.app.payment.PaymentService"],
        },
        system_name="TestMono",
    )

    out_dir = tmp_path / "out"
    metric = SMMetric()
    assert metric.needs_monolith is True
    result = metric.evaluate(partition, ms_dir=mono_dir, mono_dir=mono_dir, output_dir=out_dir)

    assert result.metric == "SM"
    # order-ms has n=2, mu=1 (intra=1/4=0.25), sigma=1 with payment-ms (n=1) -> inter=1/(2*2*1)=0.25 -> SM=0.0
    # payment-ms has n=1, mu=0 (intra=0), inter=1/(2*1*2)=0.25 -> SM=-0.25
    assert result.microservice_scores["order-ms"] == pytest.approx(0.0)
    assert result.microservice_scores["payment-ms"] == pytest.approx(-0.25)
    assert result.score == pytest.approx(-0.125)
    assert (out_dir / "sm_score.json").exists()
