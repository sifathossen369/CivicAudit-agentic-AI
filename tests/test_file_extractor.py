import base64
import json
import pytest
from core.tools.file_extractor import FileExtractor
from web_server import upload_and_audit, FileUploadRequest

def test_file_extractor_csv():
    csv_content = b"item,quantity,unit_price\nExecutive Laptop,10,2500\nErgonomic Chair,20,500\n"
    extracted = FileExtractor.process_uploaded_file("tender.csv", csv_content)
    assert "Executive Laptop" in extracted
    assert "2500" in extracted

def test_file_extractor_json():
    json_data = {"items": [{"name": "Cisco Switch", "quantity": 5, "quoted_unit_price": 1200.0}]}
    json_bytes = json.dumps(json_data).encode("utf-8")
    extracted = FileExtractor.process_uploaded_file("tender.json", json_bytes)
    assert "Cisco Switch" in extracted

def test_upload_and_audit_json_endpoint():
    json_data = {
        "tender_id": "TEST-UPLOAD-01",
        "title": "IT Equipment Docket",
        "procuring_entity": "Municipal Council",
        "items": [
            {
                "item_id": "IT-01",
                "name": "Dell OptiPlex Desktop",
                "specification": "Intel Core i7 16GB RAM 512GB SSD",
                "category": "Computers",
                "quantity": 10,
                "quoted_unit_price": 2800.0,
                "quoted_total_price": 28000.0
            }
        ]
    }
    b64_content = base64.b64encode(json.dumps(json_data).encode("utf-8")).decode("utf-8")
    req = FileUploadRequest(
        filename="docket.json",
        file_base64=f"data:application/json;base64,{b64_content}",
        title="IT Equipment Docket",
        procuring_entity="Municipal Council",
        tender_id="TEST-UPLOAD-01"
    )
    response = upload_and_audit(req)
    assert response.status_code == 200
    res_body = json.loads(response.body.decode("utf-8"))
    assert "dossier" in res_body
    assert "logs" in res_body
    assert res_body["dossier"]["tender_id"] == "TEST-UPLOAD-01"
