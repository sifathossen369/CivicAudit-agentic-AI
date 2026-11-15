import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

class AuditConfig:
    PROJECT_NAME: str = "CivicAudit AI - Agentic"
    VERSION: str = "4.0.0-Autonomous-Council"
    TAGLINE: str = "Autonomous Public Procurement Oversight with Real-Time LLM Multi-Agent Tribunal"
    
    # Council Operating Mode:
    # 'llm': Full live LLM multi-turn debate between Scout, Advocate, and Arbiter
    # 'hybrid': Live LLM debate on flagged anomalies; deterministic on compliant items
    # 'deterministic': High-speed mathematical statutory formula fallback
    COUNCIL_MODE: str = os.getenv("COUNCIL_MODE", "llm").lower()
    
    # Paths
    DATA_DIR: Path = BASE_DIR / "data"
    SAMPLES_DIR: Path = BASE_DIR / "data" / "sample_tenders"
    REPORTS_DIR: Path = BASE_DIR / "reports"
    
    # Financial Audit Thresholds
    WARNING_THRESHOLD_PERCENT: float = float(os.getenv("WARNING_THRESHOLD_PERCENT", 30.0))
    CRITICAL_THRESHOLD_PERCENT: float = float(os.getenv("CRITICAL_THRESHOLD_PERCENT", 75.0))
    
    # Currency
    DEFAULT_CURRENCY: str = os.getenv("DEFAULT_CURRENCY", "$")
    
    # Universal Multi-Provider LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto")  # auto, openrouter, groq, deepseek, gemini, openai, anthropic, mistral, local, custom
    
    # 1. OpenRouter (Access 200+ AI models including all free models)
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_AUTO_FREE: bool = os.getenv("OPENROUTER_AUTO_FREE", "true").lower() in ("true", "1", "yes")
    
    # 2. Groq (Ultra-fast inference with Multi-Key Rotation Pool)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_API_KEYS: str = os.getenv("GROQ_API_KEYS", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    @classmethod
    def get_groq_api_keys(cls) -> list:
        """
        Collects all configured Groq API keys from:
        - GROQ_API_KEYS (comma-separated list)
        - GROQ_API_KEY (comma-separated or single)
        - GROQ_API_KEY_1 through GROQ_API_KEY_10
        Returns a deduplicated list of non-empty, valid key strings.
        """
        candidates = []
        if cls.GROQ_API_KEYS:
            candidates.extend(cls.GROQ_API_KEYS.split(","))
        if cls.GROQ_API_KEY:
            candidates.extend(cls.GROQ_API_KEY.split(","))
        
        for i in range(1, 11):
            k = os.getenv(f"GROQ_API_KEY_{i}")
            if k:
                candidates.extend(k.split(","))

        clean_keys = []
        seen = set()
        for k in candidates:
            s = str(k).strip()
            if len(s) > 8 and not s.lower().startswith("your_") and s not in seen:
                seen.add(s)
                clean_keys.append(s)
        return clean_keys
    
    # 3. DeepSeek Direct API
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    # 4. Google Gemini Direct API
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    # 5. OpenAI Direct API
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # 6. Anthropic Claude Direct API
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
    
    # 7. Mistral AI Direct API
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
    
    # 8. Local Offline LLM (Ollama, LM Studio, vLLM)
    LOCAL_LLM_URL: str = os.getenv("LOCAL_LLM_URL", "")  # e.g. http://localhost:11434/v1
    LOCAL_LLM_MODEL: str = os.getenv("LOCAL_LLM_MODEL", "llama3")
    
    # 9. Generic Custom OpenAI-Compatible Provider (Together, Sambanova, Fireworks, etc.)
    CUSTOM_LLM_BASE_URL: str = os.getenv("CUSTOM_LLM_BASE_URL", "")
    CUSTOM_LLM_API_KEY: str = os.getenv("CUSTOM_LLM_API_KEY", "")
    CUSTOM_LLM_MODEL: str = os.getenv("CUSTOM_LLM_MODEL", "")

    # Live Search Engine API Keys (Optional - Free tier available)
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")

# Ensure directories exist
AuditConfig.DATA_DIR.mkdir(parents=True, exist_ok=True)
AuditConfig.SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
AuditConfig.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
