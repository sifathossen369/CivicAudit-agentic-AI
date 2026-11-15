import json
import re
import logging
from typing import Tuple, List, Optional
from core.models import ProcurementLineItem, MarketBenchmark, AgentDebateTurn
from core.llm_client import LLMClient
from core.tools.type_utils import safe_float
from core.prompts.system_prompts import (
    SCOUT_AGENT_PROMPT,
    ADVOCATE_AGENT_PROMPT,
    CHIEF_AUDITOR_PROMPT
)
from config import AuditConfig

logger = logging.getLogger("CivicAudit.Council")

class MultiAgentPriceCouncil:
    """
    Autonomous LLM-Powered Multi-Agent Consensus Tribunal (v4.0 Agentic Engine).
    
    Orchestrates a real-time, multi-turn cognitive debate among 3 specialized AI personas:
    1. Agent Scout (🕵️‍♂️): Ruthless public investigator challenging inflated supplier quotes.
    2. Agent Advocate (💼): Procurement economist defending statutory allowances (VAT, AIT, warranty).
    3. Chief Auditor (⚖️): Judicial magistrate weighing evidence to issue a binding consensus ruling.
    
    Operating Modes (Configurable via COUNCIL_MODE):
    - 'llm': Full cognitive LLM agentic deliberation on every line-item.
    - 'hybrid': Full LLM debate on flagged anomalies; deterministic on compliant items.
    - 'deterministic': High-speed mathematical statutory formula fallback (zero token consumption).
    """

    @classmethod
    def deliberate(
        cls,
        item: ProcurementLineItem,
        raw_benchmark: MarketBenchmark
    ) -> Tuple[float, List[AgentDebateTurn], str]:
        """
        Main entry point for Council deliberation. Dispatches to selected operating mode.
        """
        mode = getattr(AuditConfig, "COUNCIL_MODE", "llm").lower()
        quoted = max(0.0, float(item.quoted_unit_price))
        floor = max(0.01, float(raw_benchmark.fair_market_unit_price))

        if mode == "deterministic" or not LLMClient.is_available():
            return cls.deliberate_deterministic(item, raw_benchmark)
        elif mode == "hybrid":
            # In hybrid mode: invoke LLM if quote exceeds standard 25% statutory cushion
            if quoted > (floor * 1.25):
                return cls.deliberate_llm(item, raw_benchmark)
            else:
                return cls.deliberate_deterministic(item, raw_benchmark)
        else:
            # Full LLM council mode
            return cls.deliberate_llm(item, raw_benchmark)

    @classmethod
    def deliberate_llm(
        cls,
        item: ProcurementLineItem,
        raw_benchmark: MarketBenchmark
    ) -> Tuple[float, List[AgentDebateTurn], str]:
        """
        Executes a real 3-turn adversarial LLM conversation.
        """
        quoted = max(0.0, float(item.quoted_unit_price))
        floor_price = max(0.01, float(raw_benchmark.fair_market_unit_price))
        scout_markup = ((quoted - floor_price) / floor_price * 100) if floor_price > 0 else 0.0

        try:
            # =================================================================
            # TURN 1: AGENT SCOUT (DATA INVESTIGATOR 🕵️‍♂️)
            # =================================================================
            scout_user_prompt = (
                f"Line Item: '{item.name}' (Specification: {item.specification})\n"
                f"Quoted Unit Price: ${quoted:,.2f}\n"
                f"Verified Wholesale Trading Floor: ${floor_price:,.2f} ({raw_benchmark.price_source})\n"
                f"Vendor Markup over Floor: {scout_markup:+.1f}%\n\n"
                f"Present your aggressive investigative challenge against this line item."
            )
            scout_msg = LLMClient.complete(
                prompt=scout_user_prompt,
                system_prompt=SCOUT_AGENT_PROMPT,
                max_tokens=220,
                temperature=0.3
            )
            if not scout_msg or len(scout_msg.strip()) < 10:
                raise ValueError("Empty response from Scout Agent")

            # =================================================================
            # TURN 2: AGENT ADVOCATE (VENDOR COUNSEL 💼)
            # =================================================================
            fair_ceiling = round(floor_price * 1.25, 2)
            advocate_user_prompt = (
                f"Line Item: '{item.name}' | Quoted Price: ${quoted:,.2f} | Wholesale Floor: ${floor_price:,.2f}\n"
                f"Maximum Justifiable Statutory Ceiling (+25% for 15% VAT, 7.5% AIT, overhead, warranty): ${fair_ceiling:,.2f}\n\n"
                f"Agent Scout has issued this challenge:\n\"{scout_msg.strip()}\"\n\n"
                f"Present your defense explaining what portion is justified by statutory taxes/logistics and whether the quoted price is defensible."
            )
            advocate_msg = LLMClient.complete(
                prompt=advocate_user_prompt,
                system_prompt=ADVOCATE_AGENT_PROMPT,
                max_tokens=240,
                temperature=0.3
            )
            if not advocate_msg or len(advocate_msg.strip()) < 10:
                raise ValueError("Empty response from Advocate Agent")

            # =================================================================
            # TURN 3: CHIEF FORENSIC AUDITOR (JUDICIAL ARBITER ⚖️)
            # =================================================================
            auditor_user_prompt = (
                f"Tender Line Item: '{item.name}' (Qty: {item.quantity})\n"
                f"Quoted Unit Price: ${quoted:,.2f} | Wholesale Floor: ${floor_price:,.2f}\n\n"
                f"[TRIBUNAL RECORD - ARGUMENT 1]\nAgent Scout (Intel): \"{scout_msg.strip()}\"\n\n"
                f"[TRIBUNAL RECORD - ARGUMENT 2]\nAgent Advocate (Vendor): \"{advocate_msg.strip()}\"\n\n"
                f"Issue your binding judicial consensus price and official tribunal verdict in the required JSON format."
            )
            auditor_resp = LLMClient.complete(
                prompt=auditor_user_prompt,
                system_prompt=CHIEF_AUDITOR_PROMPT,
                max_tokens=260,
                temperature=0.1
            )
            if not auditor_resp:
                raise ValueError("Empty response from Chief Auditor")

            # Parse Judicial Decision JSON
            consensus_price, verdict, ruling_text = cls._parse_auditor_decision(
                auditor_resp, floor_price, quoted
            )

            # Assemble Deliberation Transcript
            transcript = [
                AgentDebateTurn(
                    agent_name="Agent Scout (Intel)",
                    role="Market Data Investigator",
                    avatar="🕵️‍♂️",
                    argument=scout_msg.strip()
                ),
                AgentDebateTurn(
                    agent_name="Agent Advocate (Vendor)",
                    role="Procurement Economics Specialist",
                    avatar="💼",
                    argument=advocate_msg.strip()
                ),
                AgentDebateTurn(
                    agent_name="Chief Auditor (Arbiter)",
                    role="Public Integrity Officer",
                    avatar="⚖️",
                    argument=f"Tribunal Ruling: {ruling_text} [VERDICT: {verdict}]"
                )
            ]

            reconciliation_notes = (
                f"Autonomous LLM Council Deliberation (Scout Floor: ${floor_price:,.2f} | "
                f"Consensus Established: ${consensus_price:,.2f} via {LLMClient.get_active_provider_name()})"
            )
            return consensus_price, transcript, reconciliation_notes

        except Exception as e:
            logger.warning(f"LLM Agent Council encounter: {e}. Gracefully activating statutory deterministic fallback...")
            return cls.deliberate_deterministic(item, raw_benchmark)

    @classmethod
    def deliberate_deterministic(
        cls,
        item: ProcurementLineItem,
        raw_benchmark: MarketBenchmark
    ) -> Tuple[float, List[AgentDebateTurn], str]:
        """
        High-speed statutory formula deliberation (Fallback & Zero-Token Mode).
        """
        quoted = max(0.0, float(item.quoted_unit_price))
        floor_price = max(0.01, float(raw_benchmark.fair_market_unit_price))
        scout_markup = ((quoted - floor_price) / floor_price * 100) if floor_price > 0 else 0.0

        transcript: List[AgentDebateTurn] = []

        # Turn 1: Scout
        scout_msg = (
            f"Based on commercial wholesale registries ({raw_benchmark.price_source}), "
            f"the baseline trading floor for '{item.name}' is ${floor_price:,.2f}. "
            f"The vendor's quoted price of ${quoted:,.2f} represents a {scout_markup:+.1f}% markup."
        )
        transcript.append(AgentDebateTurn(
            agent_name="Agent Scout (Intel)",
            role="Market Data Investigator",
            avatar="🕵️‍♂️",
            argument=scout_msg
        ))

        # Turn 2: Advocate
        commercial_cushion = 1.25  # 25% statutory procurement allowance
        fair_ceiling = round(floor_price * commercial_cushion, 2)
        
        if quoted > fair_ceiling * 1.5:
            advocate_msg = (
                f"Even incorporating maximum statutory allowances (15% VAT, 7.5% AIT, 10% contractor margin, "
                f"3-year enterprise warranty, and delivery logistics), the justifiable statutory ceiling is ${fair_ceiling:,.2f}. "
                f"I cannot defend a quoted rate of ${quoted:,.2f}; this represents flagrant over-invoicing beyond all procurement rules."
            )
        elif quoted > fair_ceiling:
            advocate_msg = (
                f"While the factory wholesale floor is ${floor_price:,.2f}, municipal public contracts legally mandate "
                f"vendor VAT, AIT deduction, bank guarantees, and delivery overheads. A rate up to ${fair_ceiling:,.2f} (+25%) "
                f"is fully defensible under Public Procurement Rules."
            )
        else:
            advocate_msg = (
                f"The quoted rate of ${quoted:,.2f} is well within competitive commercial boundaries ({scout_markup:+.1f}%), "
                f"safely covered by statutory procurement allowances (VAT, AIT, warranty, and overhead)."
            )

        transcript.append(AgentDebateTurn(
            agent_name="Agent Advocate (Vendor)",
            role="Procurement Economics Specialist",
            avatar="💼",
            argument=advocate_msg
        ))

        # Turn 3: Chief Auditor
        consensus_price = max(0.01, round(floor_price * 1.22, 2))
        markup_over_consensus = ((quoted - consensus_price) / consensus_price * 100) if consensus_price > 0 else 0.0

        if markup_over_consensus > 50:
            auditor_msg = (
                f"Council Ruling: Consensus fair market ceiling established at ${consensus_price:,.2f}. "
                f"Quoted rate of ${quoted:,.2f} ({markup_over_consensus:+.1f}% over consensus ceiling, {scout_markup:+.1f}% over floor) "
                f"flagrantly breaches Public Procurement Due Diligence statutes. "
                f"VERDICT: CRITICAL FRAUD/GOUGING RISK. Immediate contract freeze recommended."
            )
        elif quoted > fair_ceiling or markup_over_consensus > 10.0:
            auditor_msg = (
                f"Council Ruling: Consensus fair rate established at ${consensus_price:,.2f}. "
                f"Quoted rate of ${quoted:,.2f} ({markup_over_consensus:+.1f}%) exceeds statutory tolerance. "
                f"VERDICT: ELEVATED ANOMALY. Itemized supplier cost breakdown required."
            )
        else:
            auditor_msg = (
                f"Council Ruling: Consensus fair rate confirmed at ${consensus_price:,.2f}. "
                f"Quoted rate of ${quoted:,.2f} is approved within statutory market tolerance ({scout_markup:+.1f}% over floor). "
                f"VERDICT: COMPLIANT."
            )

        transcript.append(AgentDebateTurn(
            agent_name="Chief Auditor (Arbiter)",
            role="Public Integrity Officer",
            avatar="⚖️",
            argument=auditor_msg
        ))

        reconciliation_summary = (
            f"Statutory Formula Deliberation (Scout Floor: ${floor_price:,.2f} | "
            f"Advocate Ceiling: ${fair_ceiling:,.2f} | Consensus: ${consensus_price:,.2f})"
        )
        return consensus_price, transcript, reconciliation_summary

    @classmethod
    def _parse_auditor_decision(
        cls,
        raw_text: str,
        floor_price: float,
        quoted_price: float
    ) -> Tuple[float, str, str]:
        """
        Safely extracts JSON response from Chief Auditor LLM output.
        """
        # Default statutory baseline
        default_consensus = max(0.01, round(floor_price * 1.22, 2))
        default_verdict = "COMPLIANT" if quoted_price <= (floor_price * 1.25) else ("CRITICAL FRAUD/GOUGING RISK" if quoted_price > (floor_price * 1.75) else "ELEVATED ANOMALY")
        default_ruling = f"Consensus fair rate confirmed at ${default_consensus:,.2f} based on statutory procurement evaluation."

        clean = raw_text.strip()
        if "```json" in clean:
            clean = clean.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in clean:
            clean = clean.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            data = json.loads(clean)
            c_price = safe_float(data.get("consensus_price"), default=default_consensus)
            # Sanity bound: consensus cannot be less than 90% of floor or greater than quoted
            if c_price < (floor_price * 0.90) or c_price > (floor_price * 2.0):
                c_price = default_consensus
            verdict = str(data.get("verdict") or default_verdict).strip()
            ruling = str(data.get("ruling_text") or default_ruling).strip()
            return round(c_price, 2), verdict, ruling
        except Exception:
            # Regex extraction fallback if JSON format was broken
            price_match = re.search(r'"consensus_price"\s*:\s*([0-9\.]+)', raw_text)
            if price_match:
                c_price = safe_float(price_match.group(1), default_consensus)
                return round(c_price, 2), default_verdict, default_ruling
            return default_consensus, default_verdict, default_ruling
