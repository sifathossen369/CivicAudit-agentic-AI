import pytest
from core.models import ProcurementLineItem, MarketBenchmark
from core.tools.procurement_parser import ProcurementParserTool
from core.agents.consensus_council import MultiAgentPriceCouncil
from core.tools.type_utils import safe_float, safe_int

def test_safe_type_converters_edge_cases():
    assert safe_float("") == 0.0
    assert safe_float("   ") == 0.0
    assert safe_float(None) == 0.0
    assert safe_float("N/A") == 0.0
    assert safe_float("-") == 0.0
    assert safe_float("None") == 0.0
    assert safe_float("$1,500.50") == 1500.50
    assert safe_float("৳ 1,20,000.00") == 120000.00
    assert safe_float("EUR 450.00") == 450.00
    assert safe_float("250.00/unit") == 250.00

    assert safe_int("") == 1
    assert safe_int("10.0") == 10
    assert safe_int("15 units") == 15
    assert safe_int(None) == 1
    assert safe_int("-") == 1

def test_pydantic_model_dirty_data_recovery():
    item = ProcurementLineItem(
        item_id="TEST-001",
        name="Emergency Generator",
        quantity="15.0",
        quoted_unit_price="",
        quoted_total_price="$15,000.00"
    )
    assert item.quantity == 15
    assert item.quoted_unit_price == 0.0
    assert item.quoted_total_price == 15000.0

def test_parser_dirty_json():
    dirty_json = {
        "items": [
            {
                "name": "Heavy Duty Router",
                "quantity": "5 units",
                "quoted_unit_price": "$1,200.00",
                "quoted_total_price": ""
            },
            {
                "name": "Subtotal",
                "quantity": "",
                "quoted_unit_price": "",
                "quoted_total_price": ""
            },
            {
                "name": "Firewall Appliance",
                "quantity": 2,
                "quoted_unit_price": "",
                "quoted_total_price": "6000.00"
            }
        ]
    }
    items = ProcurementParserTool.parse_from_json(dirty_json)
    assert len(items) == 2  # Subtotal must be filtered out
    assert items[0].name == "Heavy Duty Router"
    assert items[0].quantity == 5
    assert items[0].quoted_unit_price == 1200.0
    assert items[0].quoted_total_price == 6000.0
    # Second item cross-calculated unit price from total price
    assert items[1].name == "Firewall Appliance"
    assert items[1].quoted_unit_price == 3000.0
    assert items[1].quoted_total_price == 6000.0

def test_parser_dirty_csv_text():
    dirty_csv = (
        "Item Description,Quantity,Unit Rate ($)\n"
        "Dell PowerEdge Server,4,$4,500.00\n"
        ",,\n"
        "Cisco Core Switch,2,$1,800.00\n"
        "Grand Total,,$21,600.00\n"
    )
    items = ProcurementParserTool.parse_from_text(dirty_csv)
    assert len(items) == 2
    assert items[0].name == "Dell PowerEdge Server"
    assert items[0].quantity == 4
    assert items[0].quoted_unit_price == 4500.0

def test_council_zero_floor_safety():
    item = ProcurementLineItem(
        item_id="ZERO-01",
        name="Obscure Rare Widget",
        quantity=1,
        quoted_unit_price=500.0,
        quoted_total_price=500.0
    )
    benchmark = MarketBenchmark(
        item_name="Obscure Rare Widget",
        fair_market_unit_price=0.0,
        price_source="No Data Source",
        confidence_score=0.5
    )
    # Must not raise ZeroDivisionError
    consensus, transcript, notes = MultiAgentPriceCouncil.deliberate(item, benchmark)
    assert consensus > 0.0
    assert len(transcript) == 3
