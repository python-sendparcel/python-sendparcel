"""Public API tests."""

import sendparcel


def test_public_api_exports_expected_symbols() -> None:
    exported = set(sendparcel.__all__)
    assert {
        "BaseProvider",
        "DummyProvider",
        "ShipmentFlow",
        "ShipmentStatus",
        "SendParcelException",
        "registry",
    }.issubset(exported)
