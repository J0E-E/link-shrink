"""Scaffold smoke test.

Confirms the shared package is importable and gives pytest at least one test to
collect so the suite exits 0 (an empty collection would exit 5). Real tests
arrive with their respective epics.
"""


def test_import_linkshrink_shared():
    import linkshrink_shared

    assert linkshrink_shared.__version__ == "0.1.0"
