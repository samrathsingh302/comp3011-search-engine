"""Smoke tests that prove the test runner and src package load correctly."""


def test_python_arithmetic_works() -> None:
    assert 1 + 1 == 2


def test_src_package_is_importable() -> None:
    import src  # noqa: F401
    from src import cli, crawler, indexer, main, search, storage  # noqa: F401
