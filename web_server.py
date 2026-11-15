import os
import json
import base64
import traceback
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

from config import AuditConfig
from core.agents.auditor_orchestrator import CivicAuditOrchestrator
from core.tools.dossier_generator import DossierGeneratorTool
from core.tools.procurement_parser import ProcurementParserTool
from core.tools.file_extractor import FileExtractor
from core.llm_client import LLMClient

logger = logging.getLogger("CivicAudit.WebServer")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="CivicAudit AI Server")

class CustomTenderRequest(BaseModel):
    title: str = "Real-World Procurement Tender"
    procuring_entity: str = "Public Works & Procurement Directorate"
    tender_id: str = "REAL-TND-2025"
    raw_text: str

class FileUploadRequest(BaseModel):
    filename: str
    file_base64: str
    title: str = "Uploaded Tender Document"
    procuring_entity: str = "Public Procurement Authority"
    tender_id: str = "UPLOAD-TND-2025"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CivicAudit AI - Multi-Agent Procurement Forensic Engine</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #0b1120; color: #f8fafc; }
    </style>
</head>
<body class="p-6 max-w-7xl mx-auto">
    <!-- Header -->
    <header class="flex justify-between items-center pb-6 border-b border-slate-800">
        <div>
            <div class="flex items-center gap-3">
                <span class="text-3xl">🏛️</span>
                <h1 class="text-2xl font-bold text-white tracking-tight">CivicAudit <span class="text-blue-500">AI</span></h1>
                <span class="bg-purple-500/20 text-purple-400 text-xs px-2.5 py-1 rounded-full font-mono font-semibold">v4.0 Autonomous Council</span>
            </div>
            <p class="text-slate-400 text-sm mt-1">Autonomous Public Procurement Oversight & Real-Time LLM Multi-Agent Tribunal</p>
        </div>
        <div class="flex items-center gap-3">
            <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-purple-500/10 text-purple-300 border border-purple-500/20 font-mono">
                <span>🧠 Brain:</span> <strong id="headerBrainBadge">{{ACTIVE_BRAIN}}</strong>
            </span>
            <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                <span>🏛️ Council:</span> <strong id="headerCouncilBadge">{{COUNCIL_MODE}}</strong>
            </span>
            <button onclick="openSettingsModal()" class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition cursor-pointer shadow-sm">
                <span>⚙️ Settings & Engine</span>
            </button>
        </div>
    </header>

    <!-- Tender Source Tabs -->
    <div class="my-6 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
        <div class="flex border-b border-slate-800 pb-3 gap-6 text-sm font-semibold">
            <button onclick="switchTab('uploadTab')" id="btnUpload" class="text-blue-400 border-b-2 border-blue-500 pb-2 flex items-center gap-2">
                <span>📁 Upload File (PDF / Excel / CSV / JSON)</span>
            </button>
            <button onclick="switchTab('pasteTab')" id="btnPaste" class="text-slate-400 hover:text-white pb-2 flex items-center gap-2">
                <span>📝 Paste Raw Text</span>
            </button>
            <button onclick="switchTab('sampleTab')" id="btnSample" class="text-slate-400 hover:text-white pb-2 flex items-center gap-2">
                <span>📂 Preloaded Dockets</span>
            </button>
        </div>

        <!-- Tab 1: Upload File (PDF / Excel / CSV / JSON) -->
        <div id="uploadTab" class="pt-4 space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                    <label class="text-xs text-slate-400 block mb-1">Tender Title</label>
                    <input id="upTitle" type="text" value="Municipal Official Procurement Docket" class="w-full bg-slate-800 border border-slate-700 text-white rounded-lg p-2 text-sm">
                </div>
                <div>
                    <label class="text-xs text-slate-400 block mb-1">Procuring Authority</label>
                    <input id="upEntity" type="text" value="City Corporation Procurement Directorate" class="w-full bg-slate-800 border border-slate-700 text-white rounded-lg p-2 text-sm">
                </div>
                <div>
                    <label class="text-xs text-slate-400 block mb-1">Tender Reference ID</label>
                    <input id="upId" type="text" value="GOV-TND-2025-UP" class="w-full bg-slate-800 border border-slate-700 text-white rounded-lg p-2 text-sm">
                </div>
            </div>

            <!-- Drag and drop zone -->
            <div id="dropZone" class="border-2 border-dashed border-slate-700 hover:border-blue-500 rounded-xl p-8 text-center bg-slate-950/50 transition-all cursor-pointer">
                <input type="file" id="fileInput" accept=".pdf,.xlsx,.xls,.csv,.json,.txt" class="hidden" onchange="handleFileSelect(event)">
                <div class="flex flex-col items-center justify-center gap-2" onclick="document.getElementById('fileInput').click()">
                    <span class="text-4xl">📄</span>
                    <p class="text-sm font-semibold text-slate-200">Click to upload or drag and drop your procurement tender</p>
                    <p class="text-xs text-slate-400">Supports <span class="text-blue-400 font-semibold">PDF (.pdf)</span>, <span class="text-emerald-400 font-semibold">Excel (.xlsx, .csv)</span>, and <span class="text-amber-400 font-semibold">JSON (.json)</span></p>
                    <div id="fileSelectedBadge" class="hidden mt-2 bg-blue-500/20 text-blue-300 border border-blue-500/30 px-3 py-1.5 rounded-lg text-xs font-mono">
                    </div>
                </div>
            </div>

            <button onclick="runFileUploadAudit()" id="uploadAuditBtn" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2.5 px-6 rounded-lg shadow-md transition-all flex items-center justify-center gap-2">
                <span>🚀 Audit Uploaded Procurement Document</span>
            </button>
        </div>

        <!-- Tab 2: Paste Real Tender Text -->
        <div id="pasteTab" class="hidden pt-4 space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                    <label class="text-xs text-slate-400 block mb-1">Tender Title</label>
                    <input id="customTitle" type="text" value="City Corporation Hospital Equipment Tender" class="w-full bg-slate-800 border border-slate-700 text-white rounded-lg p-2 text-sm">
                </div>
                <div>
                    <label class="text-xs text-slate-400 block mb-1">Procuring Authority</label>
                    <input id="customEntity" type="text" value="Ministry of Health Procurement Directorate" class="w-full bg-slate-800 border border-slate-700 text-white rounded-lg p-2 text-sm">
                </div>
                <div>
                    <label class="text-xs text-slate-400 block mb-1">Tender ID / Ref</label>
                    <input id="customId" type="text" value="MOH-2025-MED-09" class="w-full bg-slate-800 border border-slate-700 text-white rounded-lg p-2 text-sm">
                </div>
            </div>

            <div>
                <label class="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-1">
                    Paste Real Tender Text or BOQ Table copied from your PDF:
                </label>
                <textarea id="customRawText" rows="5" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 font-mono text-xs text-white placeholder-slate-600 focus:ring-2 focus:ring-blue-500">Core i7 Executive Laptop, 30 units @ $2700.00
High-Back Ergonomic Office Chair, 25 units @ $850.00
27-inch Monitor, 30 units @ $190.00
48-Port Network Switch, 5 units @ $1200.00</textarea>
            </div>

            <button onclick="runAudit('custom')" id="customAuditBtn" class="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-2.5 px-6 rounded-lg shadow-md transition-all flex items-center justify-center gap-2">
                <span>⚡ Run AI Forensic Audit on Real Tender Text</span>
            </button>
        </div>

        <!-- Tab 3: Preloaded Dockets -->
        <div id="sampleTab" class="hidden pt-4 grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div>
                <label class="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-2">Select Docket:</label>
                <select id="tenderSelect" class="w-full bg-slate-800 border border-slate-700 text-white rounded-lg p-2.5 text-sm mb-4">
                    <option value="municipal_it_tender_2025.json">Municipal IT Workstations Tender 2025</option>
                    <option value="civil_works_lighting_2025.json">Highway Solar Lighting & Generator Project</option>
                    <option value="real_world_tender.csv">Real-World Government BOQ Spreadsheet (.csv)</option>
                </select>
                <button onclick="runAudit('sample')" id="auditBtn" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2.5 px-4 rounded-lg shadow-md transition-all flex items-center justify-center gap-2">
                    <span>🚀 Audit Selected Docket</span>
                </button>
            </div>
            <div class="lg:col-span-2">
                <label class="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-2">Live Agent Stream & Council Debate</label>
                <div id="agentStream" class="h-28 overflow-y-auto bg-slate-950 rounded-lg p-3 font-mono text-xs text-slate-300 space-y-1 border border-slate-800">
                    <div class="text-slate-500">// System ready. Click audit to convene the 3-agent council.</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Live Execution Stream (Always visible below tabs) -->
    <div id="streamSection" class="my-4 bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg">
        <div class="flex justify-between items-center mb-2">
            <span class="text-xs font-semibold text-slate-300 uppercase tracking-wider">Multi-Agent Deliberation Live Stream</span>
            <span class="text-[11px] font-mono text-emerald-400">Agent Scout ⇄ Advocate ⇄ Arbiter</span>
        </div>
        <div id="mainAgentStream" class="h-24 overflow-y-auto bg-slate-950 rounded-lg p-3 font-mono text-xs text-slate-300 space-y-1 border border-slate-800">
            <div class="text-slate-500">// Ready. Upload a PDF/Excel file or choose a docket above to initiate audit.</div>
        </div>
    </div>

    <!-- Results Section (Hidden initially) -->
    <div id="resultsArea" class="hidden space-y-6">
        <!-- Top Metrics Cards -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <p class="text-xs font-semibold text-slate-400 uppercase">Total Quoted Budget</p>
                <p id="totalQuoted" class="text-2xl font-bold text-white mt-1">$0.00</p>
            </div>
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <p class="text-xs font-semibold text-slate-400 uppercase">Consensus Fair Market Value</p>
                <p id="fairBudget" class="text-2xl font-bold text-emerald-400 mt-1">$0.00</p>
            </div>
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <p class="text-xs font-semibold text-slate-400 uppercase">Taxpayer Money at Risk</p>
                <p id="taxpayerLoss" class="text-2xl font-bold text-red-500 mt-1">$0.00</p>
            </div>
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <p class="text-xs font-semibold text-slate-400 uppercase">Corruption Risk Score</p>
                <p id="riskScore" class="text-2xl font-bold text-amber-400 mt-1">0 / 100</p>
            </div>
        </div>

        <!-- Alert Summary -->
        <div id="alertBox" class="p-4 rounded-xl border flex items-start gap-3">
            <span class="text-2xl" id="alertIcon">⚠️</span>
            <div>
                <h3 class="font-bold text-sm" id="alertTitle">Forensic Risk Finding</h3>
                <p class="text-xs text-slate-300 mt-0.5" id="alertSummary"></p>
            </div>
        </div>

        <!-- Visual Chart -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
            <h3 class="text-base font-bold text-white mb-4">Quoted Rate vs. Multi-Agent Consensus Benchmark</h3>
            <div class="h-72">
                <canvas id="auditChart"></canvas>
            </div>
        </div>

        <!-- Anomaly Matrix Table -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg overflow-x-auto">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-base font-bold text-white">Bill of Quantities (BOQ) Discrepancy Matrix</h3>
                <button onclick="downloadDossier()" class="text-xs bg-slate-800 hover:bg-slate-700 text-blue-400 px-3 py-1.5 rounded-lg border border-slate-700 font-semibold">
                    📥 Download Audit Dossier (.md)
                </button>
            </div>
            <table class="w-full text-left text-xs text-slate-300">
                <thead class="text-slate-400 uppercase bg-slate-950 border-b border-slate-800">
                    <tr>
                        <th class="p-3">Item ID</th>
                        <th class="p-3">Description</th>
                        <th class="p-3 text-right">Qty</th>
                        <th class="p-3 text-right">Quoted Rate</th>
                        <th class="p-3 text-right">Council Consensus</th>
                        <th class="p-3 text-right">Fiscal Loss</th>
                        <th class="p-3 text-right">Gouging %</th>
                        <th class="p-3 text-center">Status</th>
                    </tr>
                </thead>
                <tbody id="findingsBody" class="divide-y divide-slate-800">
                </tbody>
            </table>
        </div>

        <!-- Multi-Agent Debate Transcripts -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
            <div class="flex items-center gap-2 mb-4">
                <span class="text-xl">🏛️</span>
                <h3 class="text-base font-bold text-white">Multi-Agent Price Deliberation Council Transcripts</h3>
                <span class="bg-purple-500/20 text-purple-400 text-xs px-2.5 py-0.5 rounded font-mono">Agent Scout vs Advocate vs Arbiter</span>
            </div>
            <div id="debatesContainer" class="space-y-4"></div>
        </div>
    </div>

    <script>
        let auditChart = null;
        let lastDossier = null;
        let currentUploadedFile = null;

        function switchTab(tabId) {
            ['uploadTab', 'pasteTab', 'sampleTab'].forEach(t => {
                document.getElementById(t).classList.add('hidden');
            });
            document.getElementById(tabId).classList.remove('hidden');

            document.getElementById('btnUpload').className = 'text-slate-400 hover:text-white pb-2 flex items-center gap-2';
            document.getElementById('btnPaste').className = 'text-slate-400 hover:text-white pb-2 flex items-center gap-2';
            document.getElementById('btnSample').className = 'text-slate-400 hover:text-white pb-2 flex items-center gap-2';

            if (tabId === 'uploadTab') {
                document.getElementById('btnUpload').className = 'text-blue-400 border-b-2 border-blue-500 pb-2 flex items-center gap-2';
            } else if (tabId === 'pasteTab') {
                document.getElementById('btnPaste').className = 'text-blue-400 border-b-2 border-blue-500 pb-2 flex items-center gap-2';
            } else {
                document.getElementById('btnSample').className = 'text-blue-400 border-b-2 border-blue-500 pb-2 flex items-center gap-2';
            }
        }

        function handleFileSelect(event) {
            const file = event.target.files[0];
            if (file) {
                currentUploadedFile = file;
                const badge = document.getElementById('fileSelectedBadge');
                badge.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
                badge.classList.remove('hidden');
            }
        }

        const dropZone = document.getElementById('dropZone');
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => { e.preventDefault(); dropZone.classList.add('border-blue-400'); });
        });
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => { e.preventDefault(); dropZone.classList.remove('border-blue-400'); });
        });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-blue-400');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                currentUploadedFile = files[0];
                const badge = document.getElementById('fileSelectedBadge');
                badge.textContent = `Selected: ${currentUploadedFile.name} (${(currentUploadedFile.size / 1024).toFixed(1)} KB)`;
                badge.classList.remove('hidden');
            }
        });

        async function runFileUploadAudit() {
            if (!currentUploadedFile) {
                alert('Please select or drop a PDF, Excel, CSV, or JSON file first.');
                return;
            }

            const btn = document.getElementById('uploadAuditBtn');
            btn.disabled = true;
            btn.innerHTML = `<span class="animate-spin">⚙️</span> Processing & Auditing ${currentUploadedFile.name}...`;

            const stream = document.getElementById('mainAgentStream');
            stream.innerHTML = `<div class="text-blue-400">⚡ Extracting document streams from ${currentUploadedFile.name}...</div>`;

            const reader = new FileReader();
            reader.onload = async function(e) {
                const base64Data = e.target.result;
                const payload = {
                    filename: currentUploadedFile.name,
                    file_base64: base64Data,
                    title: document.getElementById('upTitle').value,
                    procuring_entity: document.getElementById('upEntity').value,
                    tender_id: document.getElementById('upId').value
                };

                try {
                    const response = await fetch('/api/upload_tender', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(payload)
                    });
                    
                    if (!response.ok) {
                        let errText = await response.text();
                        try {
                            const errJson = JSON.parse(errText);
                            errText = errJson.error || errText;
                        } catch (p) {}
                        alert('Audit Failed: ' + errText);
                        return;
                    }

                    const data = await response.json();
                    renderAuditResults(data);
                } catch (err) {
                    alert('Upload error: ' + err);
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = `<span>🚀 Audit Uploaded Procurement Document</span>`;
                }
            };
            reader.readAsDataURL(currentUploadedFile);
        }

        async function runAudit(type) {
            const btn = type === 'custom' ? document.getElementById('customAuditBtn') : document.getElementById('auditBtn');
            btn.disabled = true;
            btn.innerHTML = `<span class="animate-spin">⚙️</span> Auditing...`;

            try {
                let response;
                if (type === 'sample') {
                    const select = document.getElementById('tenderSelect');
                    response = await fetch(`/api/audit?sample=${select.value}`);
                } else {
                    const payload = {
                        title: document.getElementById('customTitle').value,
                        procuring_entity: document.getElementById('customEntity').value,
                        tender_id: document.getElementById('customId').value,
                        raw_text: document.getElementById('customRawText').value
                    };
                    response = await fetch('/api/audit_custom', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(payload)
                    });
                }

                if (!response.ok) {
                    let errText = await response.text();
                    try {
                        const errJson = JSON.parse(errText);
                        errText = errJson.error || errText;
                    } catch (p) {}
                    alert('Audit Failed: ' + errText);
                    return;
                }

                const data = await response.json();
                renderAuditResults(data);
            } catch (err) {
                alert('Audit error: ' + err);
            } finally {
                btn.disabled = false;
                btn.innerHTML = type === 'custom' ? `<span>⚡ Run AI Forensic Audit on Real Tender Text</span>` : `<span>🚀 Audit Selected Docket</span>`;
            }
        }

        function renderAuditResults(data) {
            lastDossier = data;
            const stream = document.getElementById('mainAgentStream');
            stream.innerHTML = '';

            data.logs.forEach(log => {
                const line = document.createElement('div');
                if (log.includes('ALERT')) line.className = 'text-red-400 font-bold';
                else if (log.includes('DEBATE')) line.className = 'text-purple-400 font-semibold';
                else if (log.includes('STAGE')) line.className = 'text-amber-400';
                else line.className = 'text-slate-300';
                line.textContent = log;
                stream.appendChild(line);
            });
            stream.scrollTop = stream.scrollHeight;

            document.getElementById('totalQuoted').textContent = '$' + data.dossier.total_quoted_budget.toLocaleString('en-US', {minimumFractionDigits: 2});
            document.getElementById('fairBudget').textContent = '$' + data.dossier.fair_market_estimated_budget.toLocaleString('en-US', {minimumFractionDigits: 2});
            document.getElementById('taxpayerLoss').textContent = '$' + data.dossier.potential_taxpayer_loss.toLocaleString('en-US', {minimumFractionDigits: 2});
            document.getElementById('riskScore').textContent = data.dossier.risk_score + ' / 100';

            const alertBox = document.getElementById('alertBox');
            if (data.dossier.risk_score >= 60) {
                alertBox.className = 'p-4 rounded-xl border flex items-start gap-3 bg-red-500/10 border-red-500/30 text-red-300';
                document.getElementById('alertIcon').textContent = '🚨';
                document.getElementById('alertTitle').textContent = 'CRITICAL CORRUPTION & PRICE-GOUGING RISK';
            } else {
                alertBox.className = 'p-4 rounded-xl border flex items-start gap-3 bg-emerald-500/10 border-emerald-500/30 text-emerald-300';
                document.getElementById('alertIcon').textContent = '✅';
                document.getElementById('alertTitle').textContent = 'NORMAL PROCUREMENT INTEGRITY COMPLIANCE';
            }
            document.getElementById('alertSummary').textContent = data.dossier.executive_summary;

            const tbody = document.getElementById('findingsBody');
            const debatesContainer = document.getElementById('debatesContainer');
            tbody.innerHTML = '';
            debatesContainer.innerHTML = '';

            const labels = [];
            const quotedData = [];
            const fairData = [];

            if (!data.dossier.findings || data.dossier.findings.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="p-6 text-center text-amber-400">⚠️ No structured procurement items could be detected from this document. If this was a scanned PDF, please verify selectable text or use the "Paste Raw Text" tab to paste the item lines directly.</td></tr>';
            }

            data.dossier.findings.forEach(f => {
                labels.push(f.item_name.substring(0, 20));
                quotedData.push(f.quoted_unit_price);
                fairData.push(f.fair_market_unit_price);

                const tr = document.createElement('tr');
                const badgeClass = f.risk_level === 'CRITICAL_RED_FLAG' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 
                                  (f.risk_level === 'SUSPICIOUS_WARNING' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30');

                tr.innerHTML = `
                    <td class="p-3 font-mono text-slate-400">${f.item_id}</td>
                    <td class="p-3 font-medium text-white">${f.item_name}</td>
                    <td class="p-3 text-right">${f.quantity}</td>
                    <td class="p-3 text-right font-bold text-white">$${f.quoted_unit_price.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                    <td class="p-3 text-right text-emerald-400 font-semibold">$${f.fair_market_unit_price.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                    <td class="p-3 text-right text-red-400 font-bold">$${f.variance_total.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                    <td class="p-3 text-right font-bold ${f.gouging_percentage > 0 ? 'text-amber-400' : 'text-emerald-400'}">${f.gouging_percentage > 0 ? '+' : ''}${f.gouging_percentage.toFixed(1)}%</td>
                    <td class="p-3 text-center"><span class="px-2 py-0.5 rounded text-[11px] font-bold ${badgeClass}">${f.risk_level.replace('_', ' ')}</span></td>
                `;
                tbody.appendChild(tr);

                const debateCard = document.createElement('div');
                debateCard.className = 'border border-slate-800 rounded-lg p-4 bg-slate-950/50';
                let turnsHtml = '';
                (f.debate_transcript || []).forEach(turn => {
                    turnsHtml += `
                        <div class="flex items-start gap-3 text-xs bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
                            <span class="text-xl">${turn.avatar}</span>
                            <div>
                                <div class="font-semibold text-slate-200">${turn.agent_name} <span class="text-slate-500 text-[10px]">(${turn.role})</span></div>
                                <p class="text-slate-400 mt-0.5 leading-relaxed">${turn.argument}</p>
                            </div>
                        </div>
                    `;
                });

                debateCard.innerHTML = `
                    <div class="flex justify-between items-center mb-3">
                        <span class="font-bold text-sm text-white">${f.item_id}: ${f.item_name}</span>
                        <span class="text-xs text-slate-400">Quoted: <b>$${f.quoted_unit_price.toLocaleString('en-US')}</b> | Council Consensus: <b class="text-emerald-400">$${f.fair_market_unit_price.toLocaleString('en-US')}</b></span>
                    </div>
                    <div class="space-y-2">${turnsHtml}</div>
                `;
                debatesContainer.appendChild(debateCard);
            });

            renderChart(labels, quotedData, fairData);
            document.getElementById('resultsArea').classList.remove('hidden');
        }

        function renderChart(labels, quoted, fair) {
            const ctx = document.getElementById('auditChart').getContext('2d');
            if (auditChart) auditChart.destroy();

            auditChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        { label: 'Quoted Unit Rate ($)', data: quoted, backgroundColor: '#ef4444', borderRadius: 4 },
                        { label: 'Council Consensus Benchmark ($)', data: fair, backgroundColor: '#10b981', borderRadius: 4 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#94a3b8' } } },
                    scales: {
                        x: { ticks: { color: '#64748b' }, grid: { color: '#1e293b' } },
                        y: { ticks: { color: '#64748b' }, grid: { color: '#1e293b' } }
                    }
                }
            });
        }

        function downloadDossier() {
            if (!lastDossier) return;
            const blob = new Blob([lastDossier.markdown], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `CivicAudit_Dossier_${lastDossier.dossier.tender_id}.md`;
            a.click();
        }

        async function openSettingsModal() {
            document.getElementById('settingsModal').classList.remove('hidden');
            try {
                const res = await fetch('/api/settings');
                if (res.ok) {
                    const data = await res.json();
                    document.getElementById('modalProvider').value = data.llm_provider || 'openrouter';
                    if (data.council_mode) {
                        document.getElementById('modalCouncilMode').value = data.council_mode;
                    }
                    if (data.openrouter_model) {
                        document.getElementById('modalOpenRouterModel').value = data.openrouter_model;
                    }
                    document.getElementById('modalAutoFree').checked = data.openrouter_auto_free !== false;
                    onProviderChange();
                }
            } catch (e) {}
        }

        function closeSettingsModal() {
            document.getElementById('settingsModal').classList.add('hidden');
            document.getElementById('testStatus').classList.add('hidden');
        }

        function onProviderChange() {
            const p = document.getElementById('modalProvider').value;
            const orOpt = document.getElementById('openrouterOptions');
            const keyLabel = document.getElementById('keyLabel');
            const keyHint = document.getElementById('keyHint');

            if (p === 'openrouter') {
                orOpt.classList.remove('hidden');
                keyLabel.textContent = 'OpenRouter API Key (sk-or-v1-...)';
                keyHint.textContent = 'Get your free key at openrouter.ai/keys (no credit card required for free models)';
            } else if (p === 'groq') {
                orOpt.classList.add('hidden');
                keyLabel.textContent = 'Groq API Key (gsk_...)';
                keyHint.textContent = 'Get your free high-speed key at console.groq.com';
            } else if (p === 'deepseek') {
                orOpt.classList.add('hidden');
                keyLabel.textContent = 'DeepSeek API Key (sk-...)';
                keyHint.textContent = 'Direct API key from platform.deepseek.com';
            } else if (p === 'gemini') {
                orOpt.classList.add('hidden');
                keyLabel.textContent = 'Google Gemini API Key (AIzaSy...)';
                keyHint.textContent = 'Get your free key at aistudio.google.com';
            } else if (p === 'openai') {
                orOpt.classList.add('hidden');
                keyLabel.textContent = 'OpenAI API Key (sk-...)';
                keyHint.textContent = 'Platform key from platform.openai.com';
            } else {
                orOpt.classList.add('hidden');
                keyLabel.textContent = 'Provider API Key / URL';
                keyHint.textContent = 'Saved to your local .env configuration.';
            }
        }

        function onModelSelectChange() {
            const val = document.getElementById('openrouterModelSelect').value;
            if (val !== 'custom') {
                document.getElementById('modalOpenRouterModel').value = val;
            }
        }

        async function saveAISettings() {
            const btn = document.getElementById('btnSaveSettings');
            btn.disabled = true;
            btn.textContent = 'Saving...';

            const payload = {
                llm_provider: document.getElementById('modalProvider').value,
                council_mode: document.getElementById('modalCouncilMode').value,
                openrouter_model: document.getElementById('modalOpenRouterModel').value,
                openrouter_auto_free: document.getElementById('modalAutoFree').checked,
                api_key: document.getElementById('modalApiKey').value
            };

            try {
                const res = await fetch('/api/save_settings', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (res.ok) {
                    document.getElementById('headerBrainBadge').textContent = data.active_brain;
                    if (data.council_mode) {
                        document.getElementById('headerCouncilBadge').textContent = data.council_mode.toUpperCase();
                    }
                    alert('Settings updated successfully! Active Engine: ' + data.active_brain + ' | Council Mode: ' + (data.council_mode || 'LLM').toUpperCase());
                    closeSettingsModal();
                } else {
                    alert('Save failed: ' + (data.error || 'Unknown error'));
                }
            } catch (err) {
                alert('Error saving settings: ' + err);
            } finally {
                btn.disabled = false;
                btn.textContent = '💾 Save & Apply';
            }
        }

        async function testCurrentAI() {
            const statusBox = document.getElementById('testStatus');
            statusBox.classList.remove('hidden');
            statusBox.className = 'text-xs p-3 rounded-lg border bg-blue-500/10 border-blue-500/30 text-blue-300';
            statusBox.textContent = '⏳ Testing live AI response...';

            try {
                const res = await fetch('/api/test_ai', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    statusBox.className = 'text-xs p-3 rounded-lg border bg-emerald-500/10 border-emerald-500/30 text-emerald-300';
                    statusBox.innerHTML = `✅ <strong>Connected:</strong> ${data.provider} | Response: "${data.response}"`;
                } else {
                    statusBox.className = 'text-xs p-3 rounded-lg border bg-red-500/10 border-red-500/30 text-red-300';
                    statusBox.innerHTML = `❌ <strong>Failed:</strong> ${data.error || 'No response returned'}`;
                }
            } catch (err) {
                statusBox.className = 'text-xs p-3 rounded-lg border bg-red-500/10 border-red-500/30 text-red-300';
                statusBox.textContent = 'Test failed: ' + err;
            }
        }
    </script>

    <!-- AI Settings Modal -->
    <div id="settingsModal" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
        <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl p-6 shadow-2xl space-y-4">
            <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                <div class="flex items-center gap-2">
                    <span class="text-xl">⚙️</span>
                    <div>
                        <h3 class="text-base font-bold text-white">AI Provider & Multi-Model Engine</h3>
                        <p class="text-xs text-slate-400">Add or switch OpenRouter (with all Free models), Groq, DeepSeek, Gemini, etc.</p>
                    </div>
                </div>
                <button onclick="closeSettingsModal()" class="text-slate-400 hover:text-white text-2xl font-bold">&times;</button>
            </div>

            <div class="space-y-4">
                <div>
                    <label class="text-xs font-semibold text-slate-300 block mb-1">🏛️ Council Deliberation Mode</label>
                    <select id="modalCouncilMode" class="w-full bg-slate-800 border border-slate-700 text-white rounded-lg p-2.5 text-xs">
                        <option value="llm">🧠 Full Autonomous LLM Council (Real-Time 3-Agent Live Debate)</option>
                        <option value="hybrid">⚡ Smart Hybrid Council (LLM on Suspected Gouging; Fast on Normal)</option>
                        <option value="deterministic">⏱️ Statutory Deterministic Formula (Zero Token Consumption)</option>
                    </select>
                    <p class="text-[11px] text-slate-500 mt-1">Select whether line-item price debates are conducted by real-time LLM agents or fast statutory formulas.</p>
                </div>

                <div>
                    <label class="text-xs font-semibold text-slate-300 block mb-1">Select AI Provider</label>
                    <select id="modalProvider" onchange="onProviderChange()" class="w-full bg-slate-800 border border-slate-700 text-white rounded-lg p-2.5 text-xs">
                        <option value="openrouter">OpenRouter (Access 200+ Models with Free-Tier Cascade)</option>
                        <option value="groq">Groq (Ultra-fast Llama-3.3 70B & 8B)</option>
                        <option value="deepseek">DeepSeek Direct API (DeepSeek V3 / R1)</option>
                        <option value="gemini">Google Gemini Direct (Gemini 2.0 Flash / 1.5 Pro)</option>
                        <option value="openai">OpenAI Direct (GPT-4o / GPT-4o-mini)</option>
                        <option value="anthropic">Anthropic Claude (Claude 3.5 Sonnet / Haiku)</option>
                        <option value="mistral">Mistral AI (Mistral Small / Codestral)</option>
                        <option value="local">Local Private LLM (Ollama / LM Studio)</option>
                        <option value="auto">Auto-Cascade (Intelligent Automated Failover)</option>
                    </select>
                </div>

                <!-- OpenRouter Options -->
                <div id="openrouterOptions" class="space-y-3 bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                    <div>
                        <label class="text-xs text-slate-400 block mb-1">OpenRouter Model (Free or Paid)</label>
                        <select id="openrouterModelSelect" onchange="onModelSelectChange()" class="w-full bg-slate-800 border border-slate-700 text-white rounded-lg p-2 text-xs mb-2">
                            <option value="meta-llama/llama-3.3-70b-instruct:free">⭐ Llama-3.3 70B Instruct (Free)</option>
                            <option value="google/gemini-2.0-flash-exp:free">⚡ Google Gemini 2.0 Flash (Free)</option>
                            <option value="deepseek/deepseek-r1:free">🧠 DeepSeek R1 Reasoning (Free)</option>
                            <option value="meta-llama/llama-3.1-8b-instruct:free">🚀 Llama-3.1 8B Instant (Free)</option>
                            <option value="mistralai/mistral-small-24b-instruct-2501:free">🔬 Mistral Small 24B (Free)</option>
                            <option value="qwen/qwen-2.5-coder-32b-instruct:free">💻 Qwen 2.5 Coder 32B (Free)</option>
                            <option value="google/gemini-2.0-pro-exp-02-05:free">✨ Gemini 2.0 Pro Experimental (Free)</option>
                            <option value="custom">✏️ Custom Model ID...</option>
                        </select>
                        <input id="modalOpenRouterModel" type="text" placeholder="meta-llama/llama-3.3-70b-instruct:free" class="w-full bg-slate-800 border border-slate-700 text-white rounded-lg p-2 text-xs font-mono">
                    </div>
                    <div class="flex items-center gap-2">
                        <input type="checkbox" id="modalAutoFree" checked class="rounded border-slate-700 bg-slate-800 text-blue-500">
                        <label for="modalAutoFree" class="text-xs text-slate-300">
                            <strong>Automatic Free-Tier Cascade:</strong> If one free model is rate-limited or busy, automatically cycle to the next free model.
                        </label>
                    </div>
                </div>

                <!-- API Key Input -->
                <div>
                    <label class="text-xs font-semibold text-slate-300 block mb-1" id="keyLabel">API Key</label>
                    <input id="modalApiKey" type="password" placeholder="Paste your API key here (leave blank to keep existing key)" class="w-full bg-slate-800 border border-slate-700 text-white rounded-lg p-2.5 text-xs font-mono">
                    <p class="text-[11px] text-slate-500 mt-1" id="keyHint">Keys are securely stored in your local .env file.</p>
                </div>

                <div id="testStatus" class="hidden text-xs p-3 rounded-lg border"></div>
            </div>

            <div class="flex justify-between items-center pt-3 border-t border-slate-800">
                <button onclick="testCurrentAI()" id="btnTestAI" class="bg-slate-800 hover:bg-slate-700 text-blue-400 px-4 py-2 rounded-lg text-xs font-semibold border border-slate-700 transition">
                    🧪 Test Connection
                </button>
                <div class="flex gap-2">
                    <button onclick="closeSettingsModal()" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-lg text-xs font-semibold">
                        Cancel
                    </button>
                    <button onclick="saveAISettings()" id="btnSaveSettings" class="bg-blue-600 hover:bg-blue-500 text-white px-5 py-2 rounded-lg text-xs font-semibold shadow-md transition">
                        💾 Save & Apply
                    </button>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

class SettingsPayload(BaseModel):
    llm_provider: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    openrouter_model: Optional[str] = None
    openrouter_auto_free: Optional[bool] = None
    api_key: Optional[str] = None
    council_mode: Optional[str] = None

@app.get("/api/settings")
def get_settings():
    return {
        "active_brain": LLMClient.get_active_provider_name(),
        "llm_provider": AuditConfig.LLM_PROVIDER,
        "council_mode": getattr(AuditConfig, "COUNCIL_MODE", "llm"),
        "openrouter_model": AuditConfig.OPENROUTER_MODEL,
        "openrouter_auto_free": AuditConfig.OPENROUTER_AUTO_FREE,
        "has_openrouter_key": bool(AuditConfig.OPENROUTER_API_KEY),
        "has_groq_key": bool(AuditConfig.GROQ_API_KEY),
        "free_models": LLMClient.OPENROUTER_FREE_MODELS
    }

@app.post("/api/save_settings")
def save_settings(data: SettingsPayload):
    try:
        env_path = AuditConfig.DATA_DIR.parent / ".env"
        env_lines = []
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                env_lines = f.readlines()

        def update_or_add_env(key, val):
            nonlocal env_lines
            found = False
            for idx, line in enumerate(env_lines):
                if line.strip().startswith(f"{key}="):
                    env_lines[idx] = f"{key}={val}\n"
                    found = True
                    break
            if not found:
                env_lines.append(f"{key}={val}\n")

        if data.council_mode:
            c_mode = data.council_mode.lower().strip()
            AuditConfig.COUNCIL_MODE = c_mode
            os.environ["COUNCIL_MODE"] = c_mode
            update_or_add_env("COUNCIL_MODE", c_mode)

        if data.llm_provider:
            AuditConfig.LLM_PROVIDER = data.llm_provider
            os.environ["LLM_PROVIDER"] = data.llm_provider
            update_or_add_env("LLM_PROVIDER", data.llm_provider)

        if data.openrouter_model:
            AuditConfig.OPENROUTER_MODEL = data.openrouter_model
            os.environ["OPENROUTER_MODEL"] = data.openrouter_model
            update_or_add_env("OPENROUTER_MODEL", data.openrouter_model)

        if data.openrouter_auto_free is not None:
            AuditConfig.OPENROUTER_AUTO_FREE = data.openrouter_auto_free
            os.environ["OPENROUTER_AUTO_FREE"] = str(data.openrouter_auto_free).lower()
            update_or_add_env("OPENROUTER_AUTO_FREE", str(data.openrouter_auto_free).lower())

        if data.api_key and data.api_key.strip():
            k = data.api_key.strip()
            p = (data.llm_provider or AuditConfig.LLM_PROVIDER).lower()
            if p == "openrouter":
                AuditConfig.OPENROUTER_API_KEY = k
                os.environ["OPENROUTER_API_KEY"] = k
                update_or_add_env("OPENROUTER_API_KEY", k)
            elif p == "groq":
                AuditConfig.GROQ_API_KEY = k
                os.environ["GROQ_API_KEY"] = k
                update_or_add_env("GROQ_API_KEY", k)
            elif p == "deepseek":
                AuditConfig.DEEPSEEK_API_KEY = k
                os.environ["DEEPSEEK_API_KEY"] = k
                update_or_add_env("DEEPSEEK_API_KEY", k)
            elif p == "gemini":
                AuditConfig.GEMINI_API_KEY = k
                os.environ["GEMINI_API_KEY"] = k
                update_or_add_env("GEMINI_API_KEY", k)
            elif p == "openai":
                AuditConfig.OPENAI_API_KEY = k
                os.environ["OPENAI_API_KEY"] = k
                update_or_add_env("OPENAI_API_KEY", k)
            elif p == "anthropic":
                AuditConfig.ANTHROPIC_API_KEY = k
                os.environ["ANTHROPIC_API_KEY"] = k
                update_or_add_env("ANTHROPIC_API_KEY", k)

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(env_lines)

        return {
            "status": "success",
            "active_brain": LLMClient.get_active_provider_name(),
            "council_mode": getattr(AuditConfig, "COUNCIL_MODE", "llm")
        }
    except Exception as e:
        logger.error(f"Save settings error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"Failed to save settings: {str(e)}"})

@app.post("/api/test_ai")
def test_ai():
    try:
        active = LLMClient.get_active_provider_name()
        res = LLMClient.complete("Respond strictly with 'Audit Brain Online' and nothing else.")
        if res:
            return {"status": "success", "provider": active, "response": res.strip()}
        else:
            return {"status": "error", "provider": active, "error": "No response returned. Please verify your API key."}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/", response_class=HTMLResponse)
def index():
    brain_name = LLMClient.get_active_provider_name()
    council_mode = getattr(AuditConfig, "COUNCIL_MODE", "llm").upper()
    return HTML_TEMPLATE.replace("{{ACTIVE_BRAIN}}", brain_name).replace("{{COUNCIL_MODE}}", council_mode)

@app.get("/api/audit")
def execute_audit(sample: str = "municipal_it_tender_2025.json"):
    try:
        # Security hardening: Prevent path traversal by isolating basename and enforcing directory boundary
        clean_filename = Path(sample).name
        sample_path = (AuditConfig.SAMPLES_DIR / clean_filename).resolve()
        samples_dir_resolved = AuditConfig.SAMPLES_DIR.resolve()

        if not sample_path.is_relative_to(samples_dir_resolved) or not sample_path.exists():
            sample_path = AuditConfig.SAMPLES_DIR / "municipal_it_tender_2025.json"

        logs = []
        def log_capture(phase, msg, data=None):
            logs.append(f"[{phase}] {msg}")

        orchestrator = CivicAuditOrchestrator(step_callback=log_capture)

        if sample_path.suffix.lower() == ".csv":
            items = ProcurementParserTool.parse_from_csv(sample_path)
            tender_data = {
                "tender_id": f"CSV-{sample_path.stem.upper()}",
                "title": f"Government Bill of Quantities ({sample_path.name})",
                "procuring_entity": "Municipal Public Works Department",
                "items": [it.model_dump() for it in items]
            }
        else:
            with open(sample_path, "r", encoding="utf-8") as f:
                tender_data = json.load(f)

        dossier = orchestrator.audit_tender(
            tender_id=tender_data.get("tender_id", "TND-999"),
            title=tender_data.get("title", "Public Municipal Tender"),
            procuring_entity=tender_data.get("procuring_entity", "Government Municipal Board"),
            tender_source_data=tender_data
        )

        markdown_dossier = DossierGeneratorTool.render_markdown(dossier)

        return JSONResponse(content={
            "dossier": dossier.model_dump(),
            "logs": logs,
            "markdown": markdown_dossier
        })
    except Exception as e:
        logger.error(f"Audit error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"Audit execution failed: {str(e)}"})

@app.post("/api/audit_custom")
def execute_custom_audit(req: CustomTenderRequest):
    try:
        logs = []
        def log_capture(phase, msg, data=None):
            logs.append(f"[{phase}] {msg}")

        orchestrator = CivicAuditOrchestrator(step_callback=log_capture)
        tender_data = {
            "tender_id": req.tender_id,
            "title": req.title,
            "procuring_entity": req.procuring_entity,
            "raw_text": req.raw_text
        }

        dossier = orchestrator.audit_tender(
            tender_id=req.tender_id,
            title=req.title,
            procuring_entity=req.procuring_entity,
            tender_source_data=tender_data
        )

        markdown_dossier = DossierGeneratorTool.render_markdown(dossier)

        return JSONResponse(content={
            "dossier": dossier.model_dump(),
            "logs": logs,
            "markdown": markdown_dossier
        })
    except Exception as e:
        logger.error(f"Custom audit error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"Custom audit execution failed: {str(e)}"})

@app.post("/api/upload_tender")
def upload_and_audit(req: FileUploadRequest):
    """
    Synchronous threadpool endpoint: Handles large uploads safely without event-loop blocking.
    """
    try:
        # Security hardening: Reject payloads larger than 25MB (approx 35MB base64)
        if len(req.file_base64) > 35 * 1024 * 1024:
            return JSONResponse(status_code=413, content={"error": "Uploaded file exceeds the maximum 25MB security limit."})

        logs = []
        def log_capture(phase, msg, data=None):
            logs.append(f"[{phase}] {msg}")

        logs.append(f"[INIT] Ingesting uploaded file: {req.filename}")

        # Decode base64
        base64_str = req.file_base64
        if "," in base64_str:
            base64_str = base64_str.split(",", 1)[1]
        file_bytes = base64.b64decode(base64_str)

        # Extract text from PDF / Excel / CSV
        extracted_text = FileExtractor.process_uploaded_file(req.filename, file_bytes)
        logs.append(f"[STAGE_1] Successfully processed {req.filename} ({len(extracted_text)} characters extracted)")

        tender_data = {
            "tender_id": req.tender_id,
            "title": req.title,
            "procuring_entity": req.procuring_entity,
            "raw_text": extracted_text
        }

        # If it's a JSON file, parse directly
        if req.filename.lower().endswith(".json"):
            try:
                json_obj = json.loads(extracted_text)
                if "items" in json_obj:
                    tender_data = json_obj
            except Exception:
                pass

        orchestrator = CivicAuditOrchestrator(step_callback=log_capture)
        dossier = orchestrator.audit_tender(
            tender_id=req.tender_id,
            title=req.title,
            procuring_entity=req.procuring_entity,
            tender_source_data=tender_data
        )

        markdown_dossier = DossierGeneratorTool.render_markdown(dossier)

        return JSONResponse(content={
            "dossier": dossier.model_dump(),
            "logs": logs,
            "markdown": markdown_dossier
        })
    except Exception as e:
        logger.error(f"Upload and audit error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"Document processing failed: {str(e)}"})

if __name__ == "__main__":
    print(f"Starting CivicAudit AI Web Platform on http://127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
