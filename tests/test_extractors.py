"""Unit tests for Java and Generic code extractors."""

from pathlib import Path
from fyp_cdq.extractors.java_extractor import JavaExtractor
from fyp_cdq.extractors.generic_extractor import GenericExtractor


def test_java_extractor_ast(tmp_path: Path):
    src_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
    src_dir.mkdir(parents=True)

    java_code = """
    package com.example;

    public class CustomerService {
        private String name;
        public class Address {
            private String street;
        }
    }

    interface CustomerRepository {
        void save();
    }
    """
    (src_dir / "CustomerService.java").write_text(java_code)

    extractor = JavaExtractor()
    classes = extractor.extract_classes(tmp_path)

    assert "com.example.CustomerService" in classes
    assert "com.example.CustomerRepository" in classes


def test_generic_extractor_python(tmp_path: Path):
    import textwrap
    py_code = textwrap.dedent("""
    class AccountManager:
        pass

    class TransactionValidator:
        pass
    """)
    (tmp_path / "accounts.py").write_text(py_code)

    extractor = GenericExtractor(language="Python")
    classes = extractor.extract_classes(tmp_path)

    assert "accounts.AccountManager" in classes
    assert "accounts.TransactionValidator" in classes


def test_generic_extractor_csharp(tmp_path: Path):
    cs_code = """
    namespace EShop.Orders;

    public class Order
    {
        public int Id { get; set; }
    }

    public record OrderItem(int ProductId, int Units);
    """
    (tmp_path / "Order.cs").write_text(cs_code)

    extractor = GenericExtractor(language="C#")
    classes = extractor.extract_classes(tmp_path)

    assert "EShop.Orders.Order" in classes
    assert "EShop.Orders.OrderItem" in classes
