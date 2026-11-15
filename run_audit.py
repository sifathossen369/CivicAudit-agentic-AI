import argparse
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from core.agents.auditor_orchestrator import CivicAuditOrchestrator
from core.tools.dossier_generator import DossierGeneratorTool
from core.tools.procurement_parser import ProcurementParserTool
from core.tools.file_extractor import FileExtractor
from config import AuditConfig

console = Console()

def cli_callback(phase: str, message: str, data=None):
    if phase == "INIT":
        console.print(f"[bold cyan]🔍 [INIT][/bold cyan] {message}")
    elif phase == "STAGE_1":
        console.print(f"[bold blue]📄 [STAGE 1 - EXTRACTION][/bold blue] {message}")
    elif phase == "STAGE_2":
        console.print(f"[bold magenta]🌐 [STAGE 2 - MARKET INTEL][/bold magenta] {message}")
    elif phase == "ALERT":
        console.print(f"[bold red]{message}[/bold red]")
    elif phase == "STAGE_4":
        console.print(f"[bold yellow]⚖️ [STAGE 4 - DOSSIER SYNTHESIS][/bold yellow] {message}")
    elif phase == "COMPLETED":
        console.print(f"[bold green]✅ [COMPLETED][/bold green] {message}")

def main():
    parser = argparse.ArgumentParser(description="CivicAudit AI - Autonomous Procurement Auditor")
    parser.add_argument(
        "--file",
        type=str,
        default=str(AuditConfig.SAMPLES_DIR / "municipal_it_tender_2025.json"),
        help="Path to tender file (.json, .csv, .pdf, .xlsx, .txt)"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["llm", "hybrid", "deterministic"],
        default=AuditConfig.COUNCIL_MODE,
        help="Council operating mode: 'llm' (Full LLM debate), 'hybrid' (LLM on anomalies), 'deterministic' (Fast formulas)"
    )
    args = parser.parse_args()
    AuditConfig.COUNCIL_MODE = args.mode

    console.print(Panel(
        Text(f"{AuditConfig.PROJECT_NAME} v{AuditConfig.VERSION}\n{AuditConfig.TAGLINE}\n[ Council Mode: {args.mode.upper()} ]", justify="center", style="bold white on blue"),
        border_style="cyan"
    ))

    file_path = Path(args.file)
    if not file_path.exists():
        console.print(f"[red]Error: Tender file not found at {file_path}[/red]")
        return

    ext = file_path.suffix.lower()

    if ext == ".csv":
        # Direct CSV BOQ parsing
        items = ProcurementParserTool.parse_from_csv(file_path)
        tender_data = {
            "tender_id": f"CSV-{file_path.stem.upper()}",
            "title": f"Procurement Bill of Quantities ({file_path.name})",
            "procuring_entity": "Municipal Public Works Department",
            "items": [it.model_dump() for it in items]
        }
    elif ext in [".pdf", ".xlsx", ".xls", ".txt"]:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        extracted_text = FileExtractor.process_uploaded_file(file_path.name, file_bytes)
        tender_data = {
            "tender_id": f"DOC-{file_path.stem.upper()}",
            "title": f"Procurement Tender Document ({file_path.name})",
            "procuring_entity": "Public Procurement Authority",
            "raw_text": extracted_text
        }
    else:
        # Default JSON docket
        with open(file_path, "r", encoding="utf-8") as f:
            tender_data = json.load(f)

    orchestrator = CivicAuditOrchestrator(step_callback=cli_callback)
    dossier = orchestrator.audit_tender(
        tender_id=tender_data.get("tender_id", "TND-999"),
        title=tender_data.get("title", "Public Municipal Tender"),
        procuring_entity=tender_data.get("procuring_entity", "Government Municipal Board"),
        tender_source_data=tender_data
    )

    # Display Rich Table Summary
    table = Table(title="⚠️ DETAILED FORENSIC ANOMALY MATRIX", border_style="bright_blue")
    table.add_column("Item ID", style="cyan")
    table.add_column("Item Name", style="white")
    table.add_column("Qty", justify="right")
    table.add_column("Quoted Rate", justify="right", style="bold")
    table.add_column("Market Fair Rate", justify="right", style="green")
    table.add_column("Discrepancy / Loss", justify="right", style="red")
    table.add_column("Gouging %", justify="right", style="bold yellow")
    table.add_column("Risk Flag", justify="center")

    for f in dossier.findings:
        flag_style = "[bold red]CRITICAL[/bold red]" if f.risk_level == "CRITICAL_RED_FLAG" else ("[yellow]WARNING[/yellow]" if f.risk_level == "SUSPICIOUS_WARNING" else "[green]NORMAL[/green]")
        gouging_display = f"{'+' if f.gouging_percentage > 0 else ''}{f.gouging_percentage:.1f}%"
        table.add_row(
            f.item_id,
            f.item_name[:32],
            str(f.quantity),
            f"${f.quoted_unit_price:,.2f}",
            f"${f.fair_market_unit_price:,.2f}",
            f"${f.variance_total:,.2f}",
            gouging_display,
            flag_style
        )

    console.print("\n")
    console.print(table)

    # Save Markdown Dossier
    output_md_path = AuditConfig.REPORTS_DIR / f"Audit_Dossier_{dossier.tender_id}.md"
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(DossierGeneratorTool.render_markdown(dossier))

    console.print(f"\n[bold green]📁 Full Forensic Dossier exported to:[/bold green] [underline]{output_md_path}[/underline]\n")

if __name__ == "__main__":
    main()
