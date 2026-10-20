"""Unit tests for CHD (Cohesion at Domain level) metric evaluator."""

import json
from pathlib import Path
import pytest
from fyp_cdq.metrics.chd import CHDMetric, calculate_chd, extract_terms
from fyp_cdq.metrics.common import Operation
from fyp_cdq.models import Partition


def test_extract_terms():
    op = Operation(cls="AccountService", name="findUserAccount", params=("int",), returns="void")
    terms = extract_terms(op)
    assert "user" in terms
    assert "account" in terms
    assert "find" in terms
    # primitives and generic container types are filtered
    assert "int" not in terms
    assert "void" not in terms


def test_calculate_chd_fewer_than_two_ops():
    def get_cluster(name):
        return "svc1"

    clusters = {"svc1"}
    calls = [
        ("svc2_caller", Operation(cls="OrderService", name="getOrder", params=("int",), returns="Order"))
    ]
    score, ms_scores = calculate_chd(get_cluster, clusters, calls)
    assert score == 1.0
    assert ms_scores["svc1"] == 1.0


def test_calculate_chd_similar_terms():
    def get_cluster(name):
        return "svc1" if "Order" in name else "svc2"

    clusters = {"svc1", "svc2"}
    calls = [
        ("svc2_caller", Operation(cls="OrderService", name="createOrder", params=("OrderRequest",), returns="OrderResponse")),
        ("svc2_caller", Operation(cls="OrderService", name="updateOrder", params=("OrderRequest",), returns="OrderResponse")),
    ]
    score, ms_scores = calculate_chd(get_cluster, clusters, calls)
    assert ms_scores["svc1"] > 0.5
    assert ms_scores["svc2"] == 1.0


def test_chd_metric_evaluate_with_dataset(tmp_path: Path):
    dataset = {
        "methods": {
            "m1": {"package": "com.example", "class": "SvcA", "method_name": "doSomething", "parameters": ["int"], "return_type": "void"},
            "m2": {"package": "com.example", "class": "SvcA", "method_name": "doAnother", "parameters": ["int"], "return_type": "void"},
            "caller": {"package": "com.example", "class": "SvcB", "method_name": "call", "calls": ["m1", "m2"]}
        }
    }
    dataset_file = tmp_path / "dataset.json"
    with open(dataset_file, "w") as f:
        json.dump(dataset, f)

    partition = Partition(
        microservices={
            "svc1": ["com.example.SvcA"],
            "svc2": ["com.example.SvcB"]
        },
        system_name="TestSystem"
    )

    metric = CHDMetric()
    result = metric.evaluate(partition, ms_dir=tmp_path, output_dir=tmp_path)

    assert result.metric == "CHD"
    assert 0.0 <= result.score <= 1.0
    assert (tmp_path / "chd_score.json").exists()


def test_chd_metric_standalone_microservices_published_ops(tmp_path: Path):
    svc1 = tmp_path / "order-service"
    svc1.mkdir()
    (svc1 / "OrderController.java").write_text(
        "package com.shop.order;\n"
        "import org.springframework.web.bind.annotation.*;\n"
        "import java.util.List;\n"
        "@RestController\n"
        "public class OrderController {\n"
        "    @PostMapping\n"
        "    public Order createOrder(OrderRequest req) { return null; }\n"
        "    @GetMapping\n"
        "    public List<Order> findOrders() { return null; }\n"
        "}\n"
    )
    (svc1 / "Order.java").write_text(
        "package com.shop.order;\n"
        "import jakarta.persistence.Entity;\n"
        "@Entity\n"
        "public class Order {\n"
        "    public Long getId() { return 1L; }\n"
        "    public void setId(Long id) {}\n"
        "}\n"
    )

    partition = Partition(
        microservices={
            "order-service": ["com.shop.order.OrderController", "com.shop.order.Order"],
        },
        system_name="ShopMS",
    )

    result = CHDMetric().evaluate(partition, ms_dir=tmp_path)
    # Only the 2 @RestController endpoints (createOrder, findOrders) are published ops; @Entity getters/setters are excluded
    assert result.metadata["published_operations_count"] == 2
    assert 0.0 < result.score <= 1.0

