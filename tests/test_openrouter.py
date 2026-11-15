import os
import pytest
from unittest.mock import patch, MagicMock
from core.llm_client import LLMClient
from config import AuditConfig
from web_server import get_settings, save_settings, SettingsPayload

def test_openrouter_availability():
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-v1-abcdef1234567890abcdef"}):
        assert LLMClient.is_available() is True

def test_openrouter_call_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '[{"name": "Dell Server", "quantity": 2, "quoted_unit_price": 5000.0}]'
                }
            }
        ]
    }

    with patch("requests.post", return_value=mock_response), \
         patch.object(AuditConfig, "OPENROUTER_API_KEY", "sk-or-v1-abcdef1234567890abcdef"):
        res = LLMClient._call_openrouter("test prompt", "system instruction")
        assert res is not None
        assert "Dell Server" in res

def test_openrouter_auto_cascade_on_rate_limit():
    # Simulate first model returning 429 rate-limited, second model returning 200 OK
    resp_429 = MagicMock()
    resp_429.status_code = 429

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "choices": [{"message": {"content": "Cascade Free Model Success!"}}]
    }

    with patch("requests.post", side_effect=[resp_429, resp_200]), \
         patch.object(AuditConfig, "OPENROUTER_API_KEY", "sk-or-v1-abcdef1234567890abcdef"), \
         patch.object(AuditConfig, "OPENROUTER_AUTO_FREE", True):
        res = LLMClient._call_openrouter("test prompt", "system")
        assert res == "Cascade Free Model Success!"

def test_provider_order_preference():
    with patch.object(AuditConfig, "LLM_PROVIDER", "openrouter"), \
         patch.object(LLMClient, "_call_openrouter", return_value="OpenRouter Response"), \
         patch.object(LLMClient, "_call_groq", return_value="Groq Response"):
        res = LLMClient.complete("test prompt")
        assert res == "OpenRouter Response"

def test_web_settings_endpoints():
    settings = get_settings()
    assert "free_models" in settings
    assert len(settings["free_models"]) >= 5
    assert "active_brain" in settings
