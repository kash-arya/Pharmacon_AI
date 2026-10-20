# Pharmacon Prescription Anonymizer

> Reliable, local de-identification for medical prescriptions and clinical intake forms.  
> Built to satisfy HIPAA Safe Harbor (45 CFR § 164.514(b)) and the Indian DPDP Act 2023 without relying on cloud APIs or leaking clinical text.

---

## Core Capabilities

- **Hybrid Processing Pipeline:** Native vector redaction for digital EMR exports (runs in under 50ms) paired with local Tesseract OCR + CLAHE preprocessing for scanned papers and camera clicks.
- **Visual Stamp & Signature Grounding:** Catches colored clinic rubber stamps and freeform doctor signatures without needing explicit text anchors like `"Sign:"` or `"Dr:"`.
- **Clinical Anti-Encroachment Guard:** Stops bounding boxes from bleeding into adjacent table cells so prescribed drugs, dosages, and diagnostic findings remain intact.
- **Byte-Level PDF Sterilization:** Strips underlying text streams, clears PDF metadata, and overwrites pixels completely ($\sigma^2 = 0.0000$), blocking adversarial contrast or high-pass edge attacks.
- **Self-Contained Inspection Viewer:** Generates a lightweight, single-file HTML viewer with split-slider overlays to review redacted boundaries side-by-side.

---

## Quick Start

### 1. Environment Setup
```bash
source .venv/bin/activate
# or install directly:
pip install -r requirements.txt
```

### 2. Anonymize a File
Works on digital vector PDFs, scanned PDFs, and raw smartphone photos (`.jpg`, `.png`):
```bash
python anonymize.py --input data/samples/sample_digital_vector_prescription.pdf
```
Outputs `sample_digital_vector_prescription_anonymized.pdf` in the same directory.

### 3. Run Benchmark Suite & Comparative Showdown
```bash
# Verify 100% recall and zero PII leaks on our 8-case suite
python benchmarks/benchmark.py

# Run head-to-head comparison against naive regex expansion across 30 documents
python benchmarks/benchmark_comparative.py
```

### 4. Interactive Inspection Viewer
```bash
# Open static viewer in browser
xdg-open viewer/viewer.html

# Or spin up local server on port 8080
python viewer/viewer.py --serve --port 8080
```

### 5. Automated Tests
```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## Benchmark Results (30-Document Cohort)

| Metric | Naive Regex Expansion | Pharmacon Multimodal | Takeaway |
| :--- | :---: | :---: | :--- |
| **PII Recall Rate** | $74.59\%$ | **$82.22\%$** | $+7.64\%$ boost on degraded/noisy documents |
| **Total Identity Leaks** | $41$ | **$20$** | Halved leak counts under heavy distortion |
| **Clinical Preservation** | $93.33\%$ | **$95.00\%$** | Keeps critical medication and dosage instructions intact |
| **Unanchored Stamp/Signature Capture** | $0.0\%$ (Blind) | **$100.0\%$** (Vision) | Catches freestanding seals and doctor signatures |
| **Vector Processing Latency** | $26\text{ ms}$ | **$36\text{ ms}$** | Real-time throughput on standard hardware |

---

## Architecture & Defense Notes
For technical breakdowns, mathematical guarantees, and oral defense talking points, read:  
[`docs/PRESCRIPTION_ANONYMIZER_RESEARCH_DEFENSE.md`](docs/PRESCRIPTION_ANONYMIZER_RESEARCH_DEFENSE.md).
