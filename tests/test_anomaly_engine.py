import pytest
from core.models import ProcurementLineItem, MarketBenchmark
from core.tools.anomaly_engine import AnomalyEngineTool

def test_anomaly_classification_critical():
    item = ProcurementLineItem(
        item_id="BOQ-01",
        name="Executive Chair",
        specification="Standard",
        category="Furniture",
        quantity=10,
        quoted_unit_price=1000.0,
        quoted_total_price=10000.0
    )
    benchmark = MarketBenchmark(
        item_name="Executive Chair",
        fair_market_unit_price=200.0,
        price_source="Test Index",
        confidence_score=1.0
    )
    
    finding = AnomalyEngineTool.evaluate_item(item, benchmark)
    assert finding.gouging_percentage == 400.0
    assert finding.risk_level == "CRITICAL_RED_FLAG"
    assert finding.variance_total == 8000.0

def test_anomaly_classification_normal():
    item = ProcurementLineItem(
        item_id="BOQ-02",
        name="Display Monitor",
        specification="Standard",
        category="IT",
        quantity=5,
        quoted_unit_price=210.0,
        quoted_total_price=1050.0
    )
    benchmark = MarketBenchmark(
        item_name="Display Monitor",
        fair_market_unit_price=200.0,
        price_source="Test Index",
        confidence_score=1.0
    )
    
    finding = AnomalyEngineTool.evaluate_item(item, benchmark)
    assert finding.gouging_percentage == 5.0
    assert finding.risk_level == "NORMAL"
    assert finding.variance_total == 50.0
