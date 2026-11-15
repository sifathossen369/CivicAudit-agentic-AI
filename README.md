# 🏛️ CivicAudit AI - Agentic (v4.0.0)
### *Autonomous Public Procurement Oversight & Real-Time LLM Multi-Agent Tribunal*

<p align="center">
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="https://pydantic.dev"><img src="https://img.shields.io/badge/Pydantic-v2.0-E92063?style=for-the-badge&logo=pydantic&logoColor=white" alt="Pydantic v2"></a>
  <a href="https://pytest.org"><img src="https://img.shields.io/badge/Tests-37%20Passed%20(100%25)-brightgreen?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest"></a>
  <a href="https://openrouter.ai"><img src="https://img.shields.io/badge/Tribunal-Live%20LLM%20Multi--Agent-8B5CF6?style=for-the-badge" alt="Multi-Agent"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge" alt="License: MIT"></a>
</p>

---

## 📌 Executive Summary

Every year, governments spend trillions of dollars on public procurement. Anti-corruption bodies such as the United Nations Office on Drugs and Crime (UNODC) and the World Bank estimate that a significant share of that spending is lost to fraudulent price-gouging, collusive supplier cartels, and disguised over-invoicing hidden in voluminous Bill of Quantities (BOQ) spreadsheets.

**CivicAudit AI - Agentic (v4.0)** introduces a **True Autonomous Multi-Agent Cognitive Tribunal** where three specialized LLM agents debate each procurement line-item in real-time, cross-referencing fresh live web market telemetry, weighing statutory public procurement allowances (VAT, AIT, warranty), and issuing a consensus ruling for each line item.

---

## 🚀 Key Architectural Innovations (v4.0 Agentic)

### 1. 🏛️ True Cognitive 3-Agent Deliberation Tribunal
Unlike static prompt architectures, the Tribunal executes a multi-turn adversarial deliberation among three distinct AI agents:
* **🕵️‍♂️ Agent Scout (Market Data Investigator):** Calls the LLM with wholesale floor telemetry to vigorously challenge the vendor's quoted markup.
* **💼 Agent Advocate (Supplier Economics Counsel):** Counters Scout's challenge by presenting legitimate statutory cost additions under Public Procurement Rules (15% VAT, 7.5% Advance Income Tax, 3-year enterprise warranty, bank guarantees, delivery logistics)—granting a **25% statutory cushion**.
* **⚖️ Chief Forensic Auditor (Judicial Arbiter):** Weighs both arguments and returns a structured JSON verdict with a **Consensus Fair Ceiling**, accompanied by an authoritative tribunal declaration.

#### How the tribunal actually works (`core/agents/consensus_council.py`):
1. **Multi-Turn Debate:** Each line item triggers three real LLM calls, one per agent — Scout argues first, Advocate answers Scout's argument directly, and the Auditor reads both arguments before ruling.
2. **Strict Structured JSON Verdict:** The Auditor must reply with a strict JSON verdict: `consensus_price`, `verdict` (`COMPLIANT` | `ELEVATED ANOMALY` | `CRITICAL FRAUD/GOUGING RISK`), and `ruling_text`.
3. **Forensic Sanity Boundaries:** The consensus price is sanity-bounded: if the LLM's price falls outside 90%–200% of the verified wholesale floor, or the JSON is unparseable, the system falls back to the statutory formula ($\text{Floor} \times 1.22$).
4. **Zero-Crash Failover:** If the LLM is unavailable or any turn fails, the whole item falls back to the deterministic statutory calculation — the audit never crashes because of an AI failure.
5. **Debate Transcripts:** The full debate transcript is shown in the dashboard's transcript cards, with one card per agent.

### 2. 🎛️ Tri-Mode Council Architecture
Configurable via `COUNCIL_MODE` in `.env`, the Web UI Settings Modal, or the CLI `--mode` flag:
* **`llm` (Full Cognitive Mode):** Every line-item undergoes a complete multi-turn LLM debate.
* **`hybrid` (Intelligent Adaptive Mode - Recommended):** Suspected price-gouging items trigger full LLM tribunal debates; compliant items pass via millisecond statutory formulas (saving tokens and latency).
* **`deterministic` (Statutory Fallback Mode):** High-speed zero-token mathematical formula calculation, so the system keeps working in air-gapped environments or during API outages.

### 3. ⚡ Zero-Cache Contemporaneous Web Telemetry
Audits based on stale cached prices are easy to challenge. CivicAudit AI performs fresh, uncached live web inquiries using a 4-tier waterfall:
$$\text{DuckDuckGo Lite (Free Live)} \longrightarrow \text{Serper.dev (Google Shopping)} \longrightarrow \text{Tavily AI} \longrightarrow \text{Forensic Benchmark Index}$$

### 4. 🛡️ Forensic Price Sanity Guard
Industrial assets (e.g., \$58,000 hydraulic excavators, road rollers, dump trucks) often produce search results containing \$6,000 toy mini-models or 20-year-old scrap parts. Our proprietary Sanity Guard enforces:
$$\text{For Assets } \ge \$25,000 \implies \text{Scraped Rate must be } \ge \text{Quoted} \times 0.35$$
Accessory noise and toy models are automatically discarded, keeping baselines realistic.

### 5. 📂 Universal Multi-Format Document Ingestion
Equipped with a zero-crash extraction pipeline that processes:
* **PDF Documents:** Native text extraction via `pypdf`, with a zero-dependency fallback parser.
* **Excel & CSV Spreadsheets:** Header-agnostic, two-pass column discovery separating Item ID (`CIV-049`) from Product Name (`20-Ton Hydraulic Excavator`).
* **Unstructured / OCR Text:** AI semantic decomposition for scanned paper dockets.

### 6. 🧠 Universal Multi-Provider AI Cascade
* Integrated with **OpenRouter Free Tier** (automatically cycling through `meta-llama/llama-3.3-70b-instruct:free`, `google/gemini-2.0-flash-exp:free`, `deepseek/deepseek-r1:free`, `qwen/qwen-2.5-coder-32b-instruct:free`).
* Automatic failover across providers on HTTP 429 rate limits.
* Built-in support for **Groq Multi-Key Pool**, **DeepSeek**, **Google Gemini**, **OpenAI**, **Anthropic**, and **Local Offline LLMs** (Ollama / vLLM at `http://localhost:11434/v1`).

---

## 🔄 End-to-End Execution Pipeline

```text
   [ Tender Docket: PDF / Excel / CSV / JSON / OCR ]
                          │
                          ▼
   ┌─────────────────────────────────────────────────────────┐
   │  STAGE 1: Ingestion & Zero-Crash Normalization          │
   │  • Multi-stage extraction (LLM Semantic / Pandas Table) │
   │  • Separates Item ID ('CIV-049') from Product Name      │
   │  • Cleans currency symbols ($/€/৳), commas, dirty values│
   └──────────────────────────┬──────────────────────────────┘
                              │
                              ▼
   ┌─────────────────────────────────────────────────────────┐
   │  STAGE 2: Fresh Live Market Verification                │
   │  • Live Web Search (DuckDuckGo Lite / Google Serper)    │
   │  • Mandatory currency regex (Filters bare Lux/BTU specs)│
   │  • Forensic Sanity Guard (35% Floor Guard for Machinery)│
   └──────────────────────────┬──────────────────────────────┘
                              │
                              ▼
   ┌─────────────────────────────────────────────────────────┐
   │  STAGE 3: Adversarial Multi-Agent Deliberation Council  │
   │  • 🕵️‍♂️ Scout: Wholesale Factory Floor                   │
   │  • 💼 Advocate: Commercial Defense (25% Statutory Buffer)│
   │  • ⚖️ Arbiter: Final Consensus Ruling                   │
   └──────────────────────────┬──────────────────────────────┘
                              │
                              ▼
   ┌─────────────────────────────────────────────────────────┐
   │  STAGE 4: Statistical Anomaly & Fiscal Loss Engine      │
   │  • Gouging % = ((Quoted - Consensus) / Consensus) * 100 │
   │  • Risk Tiers: CRITICAL (>75%), WARNING (>30%), NORMAL  │
   │  • Cumulative Taxpayer Loss Computation                 │
   └──────────────────────────┬──────────────────────────────┘
                              │
                              ▼
   ┌─────────────────────────────────────────────────────────┐
   │  STAGE 5: Forensic Dossier Synthesis & Presentation     │
   │  • Real-time Glassmorphism Web Dashboard (Tailwind CSS) │
   │  • Multi-Agent Debate Transcript Cards with Avatars     │
   │  • Markdown Audit Dossier with Statutory Citations      │
   └─────────────────────────────────────────────────────────┘
```

---

## 📊 Core Mathematical & Forensic Formulas

### 1. Price Gouging Variance
$$\text{Gouging Percentage} = \left( \frac{\text{Quoted Unit Price} - \text{Consensus Fair Price}}{\text{Consensus Fair Price}} \right) \times 100$$

### 2. Taxpayer Fiscal Loss
$$\text{Taxpayer Loss} = \max\left(0, \; (\text{Quoted Unit Price} - \text{Consensus Fair Price}) \times \text{Quantity}\right)$$

### 3. Statutory Public Procurement Tolerance
$$\text{Fair Ceiling} = \text{Factory Wholesale Floor} \times 1.25 \quad (\text{15\% VAT} + \text{7.5\% AIT} + \text{Overhead})$$
$$\text{Consensus Price} = \text{Factory Wholesale Floor} \times 1.22$$
$$\text{If Quoted Price} \le \text{Fair Ceiling} \implies \mathbf{COMPLIANT}$$

### 4. Docket Composite Risk Score (0 to 100)
$$\text{Risk Score} = (N_{\text{critical}} \times 25) + (N_{\text{warning}} \times 10) + \left( \frac{\text{Total Loss}}{\text{Total Budget}} \times 40 \right)$$

---

## 💰 What Does the LLM Council Cost?

The tribunal is designed to be cheap enough for everyday use:
* **Hybrid mode (recommended):** Only flagged items — quotes above the 25% statutory cushion — get a full LLM debate. Compliant items cost zero tokens.
* **Budget models are enough:** The debate only needs short, structured arguments. GPT-4o-mini-class models (OpenAI, OpenRouter, DeepSeek, Gemini Flash) work well; there is no need for flagship reasoning models.
* **Typical cost:** A 50-item tender costs a few cents in hybrid mode and well under a dollar in full `llm` mode with a budget model. Exact cost depends on the model, the number of items, and how many items get flagged.
* **Free demos:** OpenRouter, Groq, and Gemini all offer free tiers that cover a competition demo at \$0.

---

## 🛠️ Project Structure

```text
CivicAudit-agentic-AI/
├── config.py                     # Central audit thresholds & AI provider settings
├── conftest.py                   # Pytest configuration
├── requirements.txt              # Production Python dependencies
├── run_audit.py                  # Headless Forensic CLI Entry Point
├── web_server.py                 # FastAPI Production Web Platform & UI
├── .env.example                  # Environment configuration template
├── .gitignore                    # Security exclusions (Secrets & Bytecode)
├── LICENSE                       # MIT Open Source License
├── core/
│   ├── models.py                 # Pydantic v2 schemas with safe type coercions
│   ├── llm_client.py             # Universal multi-provider AI waterfall cascade
│   ├── agents/
│   │   ├── auditor_orchestrator.py # Multi-stage pipeline orchestrator
│   │   └── consensus_council.py    # 3-Agent adversarial debate tribunal
│   ├── prompts/
│   │   └── system_prompts.py       # Specialized forensic persona prompts
│   └── tools/
│       ├── anomaly_engine.py       # Statistical variance & risk calculator
│       ├── dossier_generator.py    # Audit dossier markdown synthesizer
│       ├── file_extractor.py       # Multi-format document parser (PDF/XLSX/CSV)
│       ├── market_verifier.py      # Uncached web search, sanity guard & index
│       ├── procurement_parser.py   # Zero-crash BOQ table & semantic parser
│       └── type_utils.py           # Safe type converters (Currency, commas, blanks)
├── data/
│   └── sample_tenders/           # Ready-to-audit demo procurement dockets
│       ├── municipal_it_tender_2025.json
│       ├── civil_works_lighting_2025.json
│       └── real_world_tender.csv
├── reports/                      # Auto-generated audit dossiers (.md)
│   └── .gitkeep
└── tests/                        # Comprehensive automated test suite
    ├── test_anomaly_engine.py
    ├── test_dirty_data_edge_cases.py
    ├── test_file_extractor.py
    ├── test_groq_pool.py
    ├── test_llm_council.py
    ├── test_openrouter.py
    ├── test_orchestrator.py
    ├── test_procurement_parser.py
    └── test_real_world_domain_fixes.py
```

---

## ⚡ Quickstart Guide

### 1. Prerequisites
* **Python 3.11+** installed on your system.
* Git.

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/sifathossen369/CivicAudit-agentic-AI.git
cd CivicAudit-agentic-AI

# Install production dependencies
pip install -r requirements.txt
```

### 3. Environment Setup
```bash
# Copy the environment template
cp .env.example .env
```
Add your **OpenRouter**, **Groq**, or **Google Gemini** API keys to `.env`. You can also configure them from the Web Dashboard's Settings panel.

```env
# Council operating mode: llm | hybrid | deterministic
COUNCIL_MODE=hybrid
```

> **Tip:** `hybrid` is the recommended default: full LLM debates only where the numbers look suspicious. Use `llm` for a complete tribunal on every item, or `deterministic` for zero-token, offline-friendly runs.

> 🔒 **Never commit your `.env` file** — it holds your API keys. It is already covered by `.gitignore`.

### 4. Run the Web Dashboard
```bash
python web_server.py
```
Open your browser and navigate to **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.
* **Upload File:** Drag & drop any tender PDF, Excel (`.xlsx`), CSV, or JSON.
* **Paste Raw Text:** Paste unformatted Bill of Quantities text.
* **Preloaded Dockets:** Click to audit sample municipal dockets instantly.
* **AI Settings:** Configure providers, test connections, switch models and council modes in real-time.
* **Debate Transcripts:** Each finding shows the Scout / Advocate / Auditor debate cards behind the consensus price.

### 5. Run the Headless CLI
```bash
# Audit with Full Autonomous LLM Council
python run_audit.py --mode llm

# Audit with Smart Hybrid Council (LLM on anomalies, fast on compliant)
python run_audit.py --file data/sample_tenders/real_world_tender.csv --mode hybrid

# Audit with High-Speed Statutory Deterministic Formulas
python run_audit.py --file data/sample_tenders/real_world_tender.csv --mode deterministic
```

### 6. Run the Test Suite
```bash
# Execute all automated forensic & council verification tests
pytest -v -p no:cacheprovider tests
```
```text
============================= 37 passed in 3.67s ==============================
```
*(Note: Some tests hit the live web, so the full suite takes a couple of minutes depending on network conditions.)*

---

## 🔒 Security Notes
* **Local-First Design:** The dashboard is designed for local use. Run it on `127.0.0.1` and do not expose it on the public internet: the `/api/save_settings` endpoint currently has no authentication, and it writes API keys to the server's `.env` file.
* **Key Safety:** Keep API keys in your local `.env` only, and never commit that file.
* **Upload Boundaries:** Uploads are limited to 25 MB, and sample-file paths are restricted to the samples directory.

---

## 🛡️ Edge Cases Solved (The 10 Forensic Case Studies)

| # | Challenge | Root Cause | Engineering Solution |
|---|---|---|---|
| 1 | **Corrupt String Crashes** | Blank cells, `$`, `€`, `৳`, or commas in numbers. | Built `type_utils.py` and connected `@field_validator(..., mode='before')`. |
| 2 | **Code Masquerading as Name** | `CIV-049` searched on Google instead of `Excavator`. | Regex separates item codes from genuine product descriptions. |
| 3 | **Hyphenated Name Truncation** | `20-Ton Excavator` parsed as `Ton Excavator`. | Constrained code prefix stripping to require explicit spaces around hyphens (`\s+-\s+`). |
| 4 | **Specs Captured as Prices** | `160,000 Lux` light intensity captured as \$160,000. | Rewrote price regex to require mandatory currency markers (`$`, `USD`). |
| 5 | **Toy Machinery Matches** | \$58,000 Excavator matched \$6,000 toy mini-models. | Built 35% Sanity Guard: machinery $\ge \$25\text{k}$ rejects scraped prices $< 35\%$. |
| 6 | **Keyword Collisions** | \$82,000 Asphalt Paver matched \$1.75 Paving Block. | Magnitude boundary checks separating masonry blocks from heavy equipment. |
| 7 | **Packaging Unit Anomalies** | 1km Optical Fiber Cable (\$1,180) vs per-meter rate (\$1.20). | Indexed 1km spool packaging directly in the forensic benchmark catalog. |
| 8 | **False Positive Mitigation** | Honest vendors penalized for statutory VAT and taxes. | Multi-Agent Council grants 25% statutory procurement cushion. |
| 9 | **Double Sign Display Bug** | UI displayed `+-7.3%`. | Normalized signed string formatting across backend and frontend templates. |
| 10 | **Universal Model Resilience** | OpenRouter free model 429 rate limit errors. | Built a dynamic auto-cascade that cycles across free LLM providers on rate limits. |

---

## ⚖️ Legal & Anti-Corruption Citations

CivicAudit AI structures all audit dossiers according to internationally recognized procurement integrity standards:
* **United Nations Convention against Corruption (UNCAC):** Article 9 (Public Procurement and Management of Public Finances).
* **World Bank Procurement Framework:** Value for Money (VfM) and Integrity Compliance Guidelines.
* **Public Procurement Rules (PPR):** Statutory provisions for Contractor Overhead, VAT, Advance Income Tax (AIT), and Fair Market Ceilings.

> *Disclaimer: CivicAudit's rulings are algorithmic assessments for investigation support — they are not legal judgments.*

---

## 🤝 Contributing

We welcome contributions from public finance auditors, forensic accountants, and software engineers!
1. Fork the Project (`https://github.com/sifathossen369/CivicAudit-agentic-AI/fork`)
2. Create your Feature Branch (`git checkout -b feature/ForensicModule`)
3. Commit your Changes (`git commit -m 'feat: Add Vision OCR for handwritten receipts'`)
4. Push to the Branch (`git push origin feature/ForensicModule`)
5. Open a Pull Request

---

## 📜 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

---

<p align="center">
  <b>Built with public integrity in mind. Protect taxpayer money with autonomous intelligence. 🏛️</b>
</p>
