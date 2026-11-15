import pytest
from core.tools.procurement_parser import ProcurementParserTool

def test_parse_from_json():
    sample_json = {
        "items": [
            {
                "item_id": "TEST-001",
                "name": "Industrial Generator",
                "quantity": 2,
                "quoted_unit_price": 5000.0
            }
        ]
    }
    items = ProcurementParserTool.parse_from_json(sample_json)
    assert len(items) == 1
    assert items[0].item_id == "TEST-001"
    assert items[0].quantity == 2
    assert items[0].quoted_unit_price == 5000.0
    assert items[0].quoted_total_price == 10000.0

def test_parse_from_text():
    raw_text = """
    Ergonomic Office Chair, 10 units @ $450.00
    27-inch Monitor, 5 pcs at $200.00
    """
    items = ProcurementParserTool.parse_from_text(raw_text)
    assert len(items) == 2
    assert items[0].quantity == 10
    assert items[0].quoted_unit_price == 450.0
    assert items[1].quantity == 5
    assert items[1].quoted_unit_price == 200.0
