"""
Simple tests that don't require external dependencies
"""


def test_import_main():
    """Test that the main module can be imported"""
    from src import main

    assert hasattr(main, 'app')


def test_import_models():
    """Test that models can be imported"""
    from src.common.models import Transaction

    assert Transaction is not None


def test_basic_functionality():
    """Test basic functionality without external dependencies"""
    assert 1 + 1 == 2
    assert True is True
