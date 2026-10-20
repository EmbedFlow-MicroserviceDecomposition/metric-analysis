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


def test_java_extractor_ignores_comments_and_handles_records(tmp_path: Path):
    java_code = '''
    package com.example;
    /**
     * This class defines a record that provides data to interface with clients.
     */
    public record CustomerDto(String name, int age) {}
    '''
    (tmp_path / "CustomerDto.java").write_text(java_code)
    extractor = JavaExtractor()
    classes = extractor.extract_classes(tmp_path)
    assert classes == ["com.example.CustomerDto"]


def test_csharp_extractor_ignores_generic_where_class_constraints(tmp_path: Path):
    cs_code = """
    namespace EShop.EventBus;
    // Redirect from class to handler
    public interface IEventBus
    {
        void Subscribe<T, TH>()
            where T : class
            where TH : class, IIntegrationEventHandler<T>;
    }
    """
    (tmp_path / "IEventBus.cs").write_text(cs_code)
    extractor = GenericExtractor(language="C#")
    classes = extractor.extract_classes(tmp_path)
    assert classes == ["EShop.EventBus.IEventBus"]

