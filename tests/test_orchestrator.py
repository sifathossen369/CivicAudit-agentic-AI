import pytest
from core.agents.auditor_orchestrator import CivicAuditOrchestrator

def test_full_audit_pipeline():
    sample_data = {
        "tender_id": "TEST-TND-99",
        "title": "Unit Test Tender",
        "procuring_entity": "Test Entity",
        "items": [
            {
                "item_id": "T-1",
                "name": "High-Speed 4K HDMI Cable",
                "quantity": 20,
                "quoted_unit_price": 90.0
            },
            {
                "item_id": "T-2",
                "name": "27-inch Monitor",
                "quantity": 10,
                "quoted_unit_price": 185.0
            }
        ]
    }

    orchestrator = CivicAuditOrchestrator()
    dossier = orchestrator.audit_tender(
        tender_id="TEST-TND-99",
        title="Unit Test Tender",
        procuring_entity="Test Entity",
        tender_source_data=sample_data
    )

    assert dossier.tender_id == "TEST-TND-99"
    assert len(dossier.findings) == 2
    assert dossier.risk_score > 0
    assert dossier.potential_taxpayer_loss > 0
