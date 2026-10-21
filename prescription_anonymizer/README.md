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

### 4. Run Benchmark Suite
```bash
# Verify recall and zero PII leaks on genuine baseline and smartphone cohort
python benchmarks/benchmark.py
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

## Baseline Evaluation Results (Authentic Clinical Documents)

| Document Category | Document Specimen | Format Type | PII Fields | Leaks | Clinical Preservation | Latency | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Digital Vector EMR** | Apollo Hospitals EMR Slip | Vector PDF | 9 | **0** | **100.0%** | $43\text{ ms}$ | **PASS** |
| **Scanned Intake Slip** | Doctor Intake Slip #1 | Scanned PDF | 7 | **0** | **100.0%** | $4.3\text{ s}$ | **PASS** |
| **Scanned Intake Slip** | Doctor Intake Slip #2 | Scanned PDF | 7 | **0** | **100.0%** | $4.6\text{ s}$ | **PASS** |
| **Multi-page Intake** | Scanned Multi-page Record | Scanned PDF | 8 | **0** | **100.0%** | $3.9\text{ s}$ | **PASS** |
| **Smartphone Photo** | SIMSS Hospital OPD Click (S23) | JPEG Camera | 11 | **0** | **100.0%** | $31.5\text{ s}$ | **PASS** |
| **Smartphone Photo** | Akash Imaging Ultrasound (S23) | JPEG Camera | 13 | **0** | **100.0%** | $16.8\text{ s}$ | **PASS** |
| **Smartphone Photo** | Akash Imaging Report 2 (S23) | JPEG Camera | 12 | **0** | **100.0%** | $20.6\text{ s}$ | **PASS** |
| **Aggregate Summary** | **Authentic Document Cohort** | **Hybrid Pipeline** | **100.0% Recall** | **0 Leaks** | **100.0% Preserved** | - | **PASS** |

---

## Architecture & Defense Notes
For technical breakdowns, mathematical guarantees, and oral defense talking points, read:  
[`docs/PRESCRIPTION_ANONYMIZER_RESEARCH_DEFENSE.md`](docs/PRESCRIPTION_ANONYMIZER_RESEARCH_DEFENSE.md).
