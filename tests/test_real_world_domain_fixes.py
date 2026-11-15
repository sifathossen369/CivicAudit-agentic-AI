import pytest
from core.tools.procurement_parser import ProcurementParserTool
from core.tools.market_verifier import MarketVerifierTool
from core.agents.consensus_council import MultiAgentPriceCouncil
from core.models import ProcurementLineItem, MarketBenchmark

def test_csv_item_code_vs_description_separation():
    """
    Verifies that when a CSV has 'Item ID' and 'Item Description',
    the item code is NOT assigned as the product name.
    """
    csv_data = (
        "Item ID,Item Description,Specification,Category,Quantity,Unit Rate ($),Total Amount ($)\n"
        "CIV-049,20-Ton Hydraulic Excavator,Crawler Mounted Heavy Duty,Heavy Equipment,3,$58,000.00,$174,000.00\n"
        "MED-061,ICU Mechanical Ventilator,Turbine Driven High End,Medical Hardware,4,$41,000.00,$164,000.00\n"
        "CIV-052,Precast Concrete Paving Block,60mm M40 Heavy Traffic,Civil Materials,10000,$2.00,$20,000.00\n"
        "IT-005,Cat6 Network Patch Cord 2m,Molded Snagless RJ45,Networking,500,$6.00,$3,000.00\n"
    )
    items = ProcurementParserTool.parse_from_csv(csv_data)
    assert len(items) == 4

    # Item 1: CIV-049
    assert items[0].item_id == "CIV-049"
    assert items[0].name == "20-Ton Hydraulic Excavator"
    assert "CIV-049" not in items[0].name
    assert items[0].quantity == 3
    assert items[0].quoted_unit_price == 58000.0

    # Item 2: MED-061
    assert items[1].item_id == "MED-061"
    assert items[1].name == "ICU Mechanical Ventilator"
    assert "MED-061" not in items[1].name
    assert items[1].quantity == 4
    assert items[1].quoted_unit_price == 41000.0

    # Item 3: CIV-052 (Low cost, high quantity)
    assert items[2].item_id == "CIV-052"
    assert items[2].name == "Precast Concrete Paving Block"
    assert items[2].quantity == 10000
    assert items[2].quoted_unit_price == 2.0
    assert items[2].quoted_total_price == 20000.0

    # Item 4: IT-005 (Consumable)
    assert items[3].item_id == "IT-005"
    assert items[3].name == "Cat6 Network Patch Cord 2m"
    assert items[3].quantity == 500
    assert items[3].quoted_unit_price == 6.0

def test_text_tabular_parsing_with_code():
    """
    Verifies that text/pdf lines formatted as 'ID | Name | Qty | Rate' cleanly extract ID and Name.
    """
    raw_lines = """
    CIV-049 | 20-Ton Hydraulic Excavator | 3 | $58,000.00
    MED-061 | ICU Mechanical Ventilator | 4 | $41,000.00
    """
    items = ProcurementParserTool.parse_from_text(raw_lines)
    assert len(items) == 2
    assert items[0].item_id == "CIV-049"
    assert items[0].name == "20-Ton Hydraulic Excavator"
    assert items[0].quoted_unit_price == 58000.0

    assert items[1].item_id == "MED-061"
    assert items[1].name == "ICU Mechanical Ventilator"
    assert items[1].quoted_unit_price == 41000.0

def test_market_verifier_search_query_builder():
    """
    Verifies that _build_search_query strips item codes and incorporates specifications.
    """
    # Case 1: Item name has code prefix
    query1 = MarketVerifierTool._build_search_query("CIV-049 - 20-Ton Hydraulic Excavator", "Crawler Mounted 150HP")
    assert "CIV-049" not in query1
    assert "20-Ton Hydraulic Excavator" in query1
    assert "Crawler Mounted" in query1

    # Case 2: Item name is purely a code, spec has real name
    query2 = MarketVerifierTool._build_search_query("MED-061", "ICU Mechanical Ventilator High-End")
    assert "MED-061" not in query2
    assert "ICU Mechanical Ventilator" in query2

    # Case 3: Item name is clean
    query3 = MarketVerifierTool._build_search_query("Cat6 Patch Cord", "2-meter RJ45 molded")
    assert "Cat6 Patch Cord" in query3
    assert "2-meter RJ45" in query3

def test_forensic_price_sanity_guard():
    """
    Verifies that _is_price_sane rejects accessory/carton noise artifacts.
    """
    # An ICU Ventilator quoted at $41,000 should NOT accept a $66.69 accessory price
    assert MarketVerifierTool._is_price_sane(66.69, 41000.0) is False

    # An Excavator quoted at $58,000 should NOT accept a $50 manual/toy price
    assert MarketVerifierTool._is_price_sane(50.0, 58000.0) is False

    # A concrete paving block quoted at $2.00 should NOT accept a $7,386 system price
    assert MarketVerifierTool._is_price_sane(7386.93, 2.0) is False

    # A normal laptop quoted at $950 accepting an $880-$1,050 market price is valid
    assert MarketVerifierTool._is_price_sane(880.0, 950.0) is True

def test_expanded_benchmark_index_civil_and_medical():
    """
    Verifies that heavy machinery and medical hardware are correctly matched in the benchmark catalog.
    """
    # Test Excavator benchmark
    bm_excavator = MarketVerifierTool.query_benchmark("Hydraulic Excavator 20 Ton", "Heavy Duty Earthmover", 58000.0)
    assert bm_excavator.fair_market_unit_price >= 40000.0
    assert "Heavy Equipment" in bm_excavator.price_source or "PWD" in bm_excavator.price_source or "Intel" in bm_excavator.price_source

    # Test ICU Ventilator benchmark
    bm_vent = MarketVerifierTool.query_benchmark("ICU Mechanical Ventilator", "Turbine Grade Respiratory", 41000.0)
    assert bm_vent.fair_market_unit_price >= 25000.0
    assert "Health" in bm_vent.price_source or "Medical" in bm_vent.price_source or "Intel" in bm_vent.price_source

def test_public_procurement_council_statutory_allowance():
    """
    Verifies that the Multi-Agent Council factors in 20-25% statutory procurement cushions (VAT, AIT, warranty).
    """
    item = ProcurementLineItem(
        item_id="CIV-049",
        name="20-Ton Hydraulic Excavator",
        quantity=3,
        quoted_unit_price=58000.0,
        quoted_total_price=174000.0
    )
    benchmark = MarketBenchmark(
        item_name="20-Ton Hydraulic Excavator",
        fair_market_unit_price=50000.0,
        price_source="PWD Schedule of Rates",
        confidence_score=0.95
    )
    consensus, transcript, notes = MultiAgentPriceCouncil.deliberate(item, benchmark)

    # Factory floor is $50,000. Statutory procurement ceiling (+22%) is $61,000.
    # Quoted rate of $58,000 is +16% over floor, which is within the statutory 20-25% allowance!
    assert consensus >= 60000.0  # 50,000 * 1.22 = 61,000
    assert "COMPLIANT" in transcript[2].argument  # Must NOT be flagged as fraud!

def test_fraud_test_brackets_stripped_and_no_mid_word_truncation():
    """
    Verifies that [FRAUD TEST] tags are stripped and spec does not get chopped mid-word.
    """
    query = MarketVerifierTool._build_search_query(
        "Ergonomic Mesh Office Chair [FRAUD TEST]",
        "High-Back Standard Office Mesh Chair with Adjustable Lumbar"
    )
    assert "[FRAUD TEST]" not in query
    assert "Ergonomic Mesh Office Chair" in query
    # Check no half-word like 'Adjustable Lumba'
    assert not query.endswith("Lumba")

def test_asphalt_paver_vs_concrete_block_no_collision():
    """
    Verifies that $88,000 Automatic Asphalt Concrete Paver machine NEVER collides with $1.75 block.
    """
    bm = MarketVerifierTool.query_benchmark(
        item_name="Automatic Asphalt Concrete Paver",
        specification="Paving Width 2.5m - 6.0m Electric Heated Screed",
        quoted_unit_price=88000.0
    )
    # Must NOT be $1.75! It must be heavy equipment tier (>= $40,000)
    assert bm.fair_market_unit_price >= 40000.0
    assert "Paving Block" not in bm.price_source

def test_negative_markup_formatting_no_plus_minus():
    """
    Verifies that negative markup does not print '+-' in transcripts.
    """
    item = ProcurementLineItem(
        item_id="LOW-01",
        name="Discounted Computer Monitor",
        quantity=5,
        quoted_unit_price=150.0,
        quoted_total_price=750.0
    )
    benchmark = MarketBenchmark(
        item_name="Discounted Computer Monitor",
        fair_market_unit_price=180.0,
        price_source="State IT Framework",
        confidence_score=0.95
    )
    consensus, transcript, notes = MultiAgentPriceCouncil.deliberate(item, benchmark)
    for t in transcript:
        assert "+-" not in t.argument

def test_optical_fiber_1km_roll_pricing():
    """
    Verifies that IT-012 Single-Mode Armored Fiber Cable 1km resolves to 1km roll pricing ($950),
    preventing the +80,000% False Positive caused by per-meter pricing ($1.20).
    """
    bm = MarketVerifierTool.query_benchmark(
        item_name="Single-Mode Armored Fiber Cable 1km",
        specification="12-Core Heavy Duty Outdoor Underground Armored Optical Fiber",
        quoted_unit_price=1180.0
    )
    # Floor must be ~$950 (1km roll tier), NOT $1.20!
    assert bm.fair_market_unit_price >= 700.0
    assert bm.fair_market_unit_price <= 1500.0

    item = ProcurementLineItem(
        item_id="IT-012",
        name="Single-Mode Armored Fiber Cable 1km",
        quantity=5,
        quoted_unit_price=1180.0,
        quoted_total_price=5900.0
    )
    consensus, transcript, notes = MultiAgentPriceCouncil.deliberate(item, bm)
    # Quoted $1,180 vs floor $950 is within statutory 20-25% procurement cushion
    assert "COMPLIANT" in transcript[2].argument

def test_heavy_machinery_sanity_guard_35_percent_threshold():
    """
    Verifies that the 35% Sanity Guard rejects used salvage, mini-models, and parts:
    - $58k Excavator rejects $6,182 mini-excavator
    - $41k Road Roller rejects $7,150 mini-roller
    - $52k Dump Truck rejects $7,250 used tipper
    - $74k Bucket Truck rejects $13,000 used crane
    """
    # 1. Excavator ($58k): $6,182 is ~10.6% of quoted -> must be rejected (< 35%)
    assert MarketVerifierTool._is_price_sane(6182.0, 58000.0) is False
    assert MarketVerifierTool._is_price_sane(52000.0, 58000.0) is True

    # 2. Road Roller ($41k): $7,150 is ~17.4% of quoted -> must be rejected (< 35%)
    assert MarketVerifierTool._is_price_sane(7150.0, 41000.0) is False
    assert MarketVerifierTool._is_price_sane(38000.0, 41000.0) is True

    # 3. Dump Truck ($52k): $7,250 is ~13.9% of quoted -> must be rejected (< 35%)
    assert MarketVerifierTool._is_price_sane(7250.0, 52000.0) is False
    assert MarketVerifierTool._is_price_sane(48000.0, 52000.0) is True

    # 4. Bucket Truck ($74k): $13,000 is ~17.5% of quoted -> must be rejected (< 35%)
    assert MarketVerifierTool._is_price_sane(13000.0, 74000.0) is False
    assert MarketVerifierTool._is_price_sane(68000.0, 74000.0) is True
