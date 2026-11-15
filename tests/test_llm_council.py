import pytest
from unittest.mock import patch
from core.models import ProcurementLineItem, MarketBenchmark
from core.agents.consensus_council import MultiAgentPriceCouncil
from config import AuditConfig

@pytest.fixture
def sample_item():
    return ProcurementLineItem(
        item_id="TEST-001",
        name="Dell OptiPlex Enterprise Workstation",
        specification="Core i7, 16GB RAM, 512GB SSD",
        quantity=10,
        quoted_unit_price=1850.00,
        quoted_total_price=18500.00
    )

@pytest.fixture
def sample_benchmark():
    return MarketBenchmark(
        item_name="Dell OptiPlex Enterprise Workstation",
        fair_market_unit_price=800.00,
        price_source="State IT Framework Pricing",
        confidence_score=0.95
    )

def test_council_deterministic_mode(sample_item, sample_benchmark):
    AuditConfig.COUNCIL_MODE = "deterministic"
    consensus_price, transcript, notes = MultiAgentPriceCouncil.deliberate(sample_item, sample_benchmark)
    
    assert consensus_price == round(800.0 * 1.22, 2)
    assert len(transcript) == 3
    assert transcript[0].agent_name == "Agent Scout (Intel)"
    assert transcript[1].agent_name == "Agent Advocate (Vendor)"
    assert transcript[2].agent_name == "Chief Auditor (Arbiter)"
    assert "Statutory Formula Deliberation" in notes

@patch("core.llm_client.LLMClient.is_available", return_value=True)
@patch("core.llm_client.LLMClient.complete")
def test_council_live_llm_mode(mock_complete, mock_is_available, sample_item, sample_benchmark):
    AuditConfig.COUNCIL_MODE = "llm"
    
    # Scout argument, Advocate defense, Chief Auditor JSON ruling
    mock_complete.side_effect = [
        "The verified wholesale floor for Dell OptiPlex is $800.00. The quoted rate of $1,850.00 represents a massive +131.2% markup, posing extreme fiscal risk.",
        "Under Public Procurement Rules, contractors bear 15% VAT, 7.5% AIT, and 3-year warranty logistics. However, the legal ceiling is $1,000.00. $1,850.00 is beyond commercial norms.",
        '{"consensus_price": 976.00, "verdict": "CRITICAL FRAUD/GOUGING RISK", "ruling_text": "The tribunal confirms consensus ceiling at $976.00. Quoted rate of $1,850 is a critical violation."}'
    ]
    
    consensus_price, transcript, notes = MultiAgentPriceCouncil.deliberate(sample_item, sample_benchmark)
    
    assert consensus_price == 976.00
    assert len(transcript) == 3
    assert "The verified wholesale floor" in transcript[0].argument
    assert "15% VAT, 7.5% AIT" in transcript[1].argument
    assert "CRITICAL FRAUD/GOUGING RISK" in transcript[2].argument
    assert "Autonomous LLM Council Deliberation" in notes

@patch("core.llm_client.LLMClient.is_available", return_value=True)
@patch("core.llm_client.LLMClient.complete", side_effect=Exception("API Timeout"))
def test_council_llm_graceful_fallback(mock_complete, mock_is_available, sample_item, sample_benchmark):
    AuditConfig.COUNCIL_MODE = "llm"
    # When LLM fails, it should seamlessly fallback to deterministic without raising exceptions
    consensus_price, transcript, notes = MultiAgentPriceCouncil.deliberate(sample_item, sample_benchmark)
    
    assert consensus_price == round(800.0 * 1.22, 2)
    assert len(transcript) == 3
    assert "Statutory Formula Deliberation" in notes
