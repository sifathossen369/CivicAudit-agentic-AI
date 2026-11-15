import pytest
from unittest.mock import MagicMock, patch
import os
from config import AuditConfig
from core.llm_client import LLMClient

def test_groq_keys_parsing_single(monkeypatch):
    monkeypatch.setattr(AuditConfig, "GROQ_API_KEYS", "")
    monkeypatch.setattr(AuditConfig, "GROQ_API_KEY", "gsk_single_test_key_123456789")
    for i in range(1, 11):
        monkeypatch.delenv(f"GROQ_API_KEY_{i}", raising=False)
    
    keys = AuditConfig.get_groq_api_keys()
    assert len(keys) == 1
    assert keys[0] == "gsk_single_test_key_123456789"

def test_groq_keys_parsing_comma_separated(monkeypatch):
    monkeypatch.setattr(AuditConfig, "GROQ_API_KEYS", "gsk_key_one_123456789, gsk_key_two_123456789, gsk_key_three_123456789")
    monkeypatch.setattr(AuditConfig, "GROQ_API_KEY", "")
    for i in range(1, 11):
        monkeypatch.delenv(f"GROQ_API_KEY_{i}", raising=False)
    
    keys = AuditConfig.get_groq_api_keys()
    assert len(keys) == 3
    assert keys[0] == "gsk_key_one_123456789"
    assert keys[1] == "gsk_key_two_123456789"
    assert keys[2] == "gsk_key_three_123456789"

def test_groq_keys_parsing_numbered_env_vars(monkeypatch):
    monkeypatch.setattr(AuditConfig, "GROQ_API_KEYS", "")
    monkeypatch.setattr(AuditConfig, "GROQ_API_KEY", "gsk_main_key_123456789")
    monkeypatch.setenv("GROQ_API_KEY_2", "gsk_second_key_123456789")
    monkeypatch.setenv("GROQ_API_KEY_3", "gsk_third_key_123456789")
    monkeypatch.setenv("GROQ_API_KEY_4", "your_api_key_placeholder")  # Should be filtered out
    monkeypatch.setenv("GROQ_API_KEY_5", "short")  # Should be filtered out (< 8 chars)
    
    keys = AuditConfig.get_groq_api_keys()
    assert len(keys) == 3
    assert "gsk_main_key_123456789" in keys
    assert "gsk_second_key_123456789" in keys
    assert "gsk_third_key_123456789" in keys
    assert "your_api_key_placeholder" not in keys

def test_provider_name_reflects_pool_size(monkeypatch):
    monkeypatch.setattr(AuditConfig, "LLM_PROVIDER", "auto")
    monkeypatch.setattr(AuditConfig, "OPENROUTER_API_KEY", "")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    
    mock_keys = ["gsk_key_1_123456789", "gsk_key_2_123456789", "gsk_key_3_123456789"]
    monkeypatch.setattr(AuditConfig, "get_groq_api_keys", classmethod(lambda cls: mock_keys))
    
    name = LLMClient.get_active_provider_name()
    assert "Groq" in name
    assert "3 Keys Pool" in name

def test_groq_failover_on_429_rate_limit(monkeypatch):
    mock_keys = ["gsk_rate_limited_key_1", "gsk_healthy_key_2"]
    monkeypatch.setattr(AuditConfig, "get_groq_api_keys", classmethod(lambda cls: mock_keys))
    LLMClient._groq_active_key_index = 0

    call_records = []

    class MockCompletion:
        def __init__(self, content):
            self.choices = [MagicMock(message=MagicMock(content=content))]

    def mock_create(*args, **kwargs):
        api_key = mock_groq_client_factory.current_key
        call_records.append(api_key)
        if api_key == "gsk_rate_limited_key_1":
            # Simulate Groq 429 rate limit error
            raise Exception("Error 429: Rate limit reached for model llama-3.3-70b on TPM/RPM limits.")
        return MockCompletion("Council Verdict: Fair Market Value Approved.")

    class MockGroqClient:
        def __init__(self, api_key, **kwargs):
            self.api_key = api_key
            mock_groq_client_factory.current_key = api_key
            self.chat = MagicMock()
            self.chat.completions.create = mock_create

    class MockGroqModule:
        Groq = MockGroqClient

    mock_groq_client_factory = MagicMock()

    with patch.dict("sys.modules", {"groq": MockGroqModule}):
        result = LLMClient._call_groq("Audit line item", "System Prompt")

    assert result == "Council Verdict: Fair Market Value Approved."
    # Verify both keys were called: Key 1 hit rate limit, then Key 2 succeeded
    assert call_records == ["gsk_rate_limited_key_1", "gsk_healthy_key_2"]
    # Verify the active index rotated to Key 2 (index 1)
    assert LLMClient._groq_active_key_index == 1
