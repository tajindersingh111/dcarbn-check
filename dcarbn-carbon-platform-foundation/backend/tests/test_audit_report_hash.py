from app.integrations.data.hashing import canonical_json_sha256


def test_audit_report_hash_is_deterministic() -> None:
    first = canonical_json_sha256(
        {
            "inventory": {"id": "inventory-1", "version": 1},
            "totals": {"total_kg_co2e": "100.000"},
        }
    )
    second = canonical_json_sha256(
        {
            "totals": {"total_kg_co2e": "100.000"},
            "inventory": {"version": 1, "id": "inventory-1"},
        }
    )

    assert first == second
