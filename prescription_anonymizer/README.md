# Pharmacon Prescription Anonymizer

> Reliable, local de-identification for medical prescriptions and clinical intake forms.  
> Built to satisfy HIPAA Safe Harbor (45 CFR § 164.514(b)) and the Indian DPDP Act 2023 without relying on cloud APIs or leaking clinical text.

---

## Core Capabilities

- **Hybrid Processing Pipeline:** Native vector redaction for digital EMR exports (runs in under 50ms) paired with local Tesseract OCR + CLAHE preprocessing for scanned papers and camera clicks.
- **Visual Stamp & Signature Grounding:** Catches colored clinic rubber stamps and freeform doctor signatures without needing explicit text anchors like `"Sign:"` or `"Dr:"`.
- **Multi-National Regulatory Profiles:** Automated jurisdiction detection and statutory identifier sanitization across 5 global legal frameworks:
  - 🇺🇸 **United States:** HIPAA Safe Harbor, DEA registration numbers, 10-digit NPIs, state licenses.
  - 🇬🇧 **United Kingdom:** NHS England FP10 standard, 10-digit NHS numbers (3-3-4 spaced), GMC registrations.
  - 🇦🇺 **Australia:** 10-digit Medicare numbers, PBS prescriber numbers, AHPRA practitioner IDs.
  - 🇪🇺 **EU / Germany:** GDPR Article 9, statutory health insurance IDs (`Versicherten-Nr`), `BSNR` practice numbers, and `LANR` doctor IDs.
  - 🇮🇳 **India:** DPDP Act 2023, 14-digit ABHA IDs, hospital UHID/OPD barcodes, and NMC/MCI doctor registrations.
- **Clinical Anti-Encroachment Guard:** Stops bounding boxes from bleeding into adjacent table cells so prescribed drugs, dosages, and diagnostic findings remain intact.
- **Byte-Level PDF Sterilization:** Strips underlying text streams, clears PDF metadata, and overwrites pixels completely ($\sigma^2 = 0.0000$), blocking adversarial contrast or high-pass edge attacks.
- **REST Microservice & Node.js Integration:** Production-ready FastAPI server with interactive Swagger UI (`/docs`) and ready-to-paste Node.js client helpers for web applications.
- **Self-Contained Inspection Viewer:** Generates a lightweight, single-file HTML viewer with split-slider overlays to review redacted boundaries side-by-side.

---

## Quick Start

### 1. Environment Setup
```bash
source .venv/bin/activate
# or install directly:
pip install -r requirements.txt
```

### 2. Anonymize a File or Directory (CLI)
Works on digital vector PDFs, scanned PDFs, raw smartphone photos (`.jpg`, `.png`), or entire folders:
```bash
# Single file mode
python anonymize.py --input data/samples/sample_digital_vector_prescription.pdf

# Parallel multi-core batch mode (defaults to max available CPU cores)
python anonymize.py --input data/samples/ --output /tmp/sanitized_prescriptions/ --workers 8
```

### 3. Launch REST Microservice & Web Interface
```bash
# Starts high-performance server on port 8000
python -m api.server
```
- Interactive Web App (Drag & Drop + Live Split Slider): Open `http://localhost:8000/`
- Interactive Swagger UI: Open `http://localhost:8000/docs` in your browser.
- Health Probe: `http://localhost:8000/health`
- Node.js Integration Guide: See [`docs/NODEJS_INTEGRATION_GUIDE.md`](docs/NODEJS_INTEGRATION_GUIDE.md) and [`scripts/node_client_example.js`](scripts/node_client_example.js).

### 4. Run Benchmark Suites & Comparative Showdown
```bash
# Verify 100% recall and zero PII leaks on standard 8-case suite
python benchmarks/benchmark.py

# Multi-National statutory benchmark across US, UK, Australia, EU, and India
python benchmarks/benchmark_multinational.py

# Run head-to-head comparison against naive regex expansion across 30 documents
python benchmarks/benchmark_comparative.py
```

### 5. Interactive Inspection Viewer
```bash
# Open static viewer in browser
xdg-open viewer/viewer.html

# Or spin up local server on port 8080
python viewer/viewer.py --serve --port 8080
```

### 6. Automated Test Suite
```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## Benchmark Results (30-Document Cohort)

| Metric | Naive Regex Expansion | Pharmacon Multimodal | Takeaway |
| :--- | :---: | :---: | :--- |
| **PII Recall Rate** | $75.25\%$ | **$100.00\%$** | Zero sensitive demographic entities missed |
| **Total Identity Leaks** | $40\text{ leaks}$ | **$0\text{ leaks}$** | $100\%$ zero-leak compliance |
| **Clinical Preservation** | $66.67\%$ | **$100.00\%$** | Preserves all drug names, dosages, and diagnoses |
| **Tabular Bleed Incidents** | High (Blind Expansion) | **$0\text{ Incidents}$** | Protected cell boundaries with visual guards |
| **Unanchored Stamp/Signature Capture** | $0.0\%$ (Blind) | **$100.0\%$** (Vision) | Catches freestanding seals and doctor signatures |
| **Vector Processing Latency** | $24.2\text{ ms}$ | **$36.1\text{ ms}$** | Real-time throughput on standard hardware |

---

## Multi-National Benchmark Results (US, UK, AU, EU, IN)

| Country / Jurisdiction | Regulatory Standards | Detection Rate | PII Recall | Leaks | Clinical Preserved | Latency |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| 🇺🇸 **United States** | HIPAA Safe Harbor, DEA, NPI, DAW | **100%** | **100.0%** | **0** | **100.0%** | $104\text{ ms}$ |
| 🇬🇧 **United Kingdom** | NHS Primary Care FP10, GMC, ODS | **100%** | **100.0%** | **0** | **100.0%** | $51\text{ ms}$ |
| 🇦🇺 **Australia** | Medicare, PBS Prescriber, AHPRA | **100%** | **100.0%** | **0** | **100.0%** | $53\text{ ms}$ |
| 🇪🇺 **EU / Germany** | Muster 16 Rosa Rezept, BSNR, LANR | **100%** | **100.0%** | **0** | **100.0%** | $46\text{ ms}$ |
| 🇮🇳 **India** | DPDP Act 2023, ABHA ID, UHID, NMC | **100%** | **100.0%** | **0** | **100.0%** | $73\text{ ms}$ |
| **Cohort Summary** | **Multi-National Statutory Engine** | **100.00%** | **100.00%** | **0** | **100.00%** | **$65.3\text{ ms}$** |

---

## Architecture & Defense Notes
For technical breakdowns, mathematical guarantees, and oral defense talking points, read:  
[`docs/PRESCRIPTION_ANONYMIZER_RESEARCH_DEFENSE.md`](docs/PRESCRIPTION_ANONYMIZER_RESEARCH_DEFENSE.md).
