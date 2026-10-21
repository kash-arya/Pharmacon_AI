#!/usr/bin/env python3
"""
Multi-National Healthcare De-Identification Benchmark Suite.

Evaluates Pharmacon across 5 major healthcare jurisdictions:
1. US (HIPAA California Security Rx Pad: DEA, NPI, DAW, street address)
2. UK (NHS Primary Care FP10: NHS Number, GMC Number, Surgery Address, Counter-sign)
3. Australia (PBS / Medicare Form: Medicare Card No, PBS Prescriber No, AHPRA ID)
4. EU / Germany (Muster 16 Rosa Rezept: Versicherten-Nr, BSNR, LANR, Krankenkasse)
5. India (DPDP Act Hospital OPD: ABHA ID, UHID, OPD No, NMC/MCI Registration)

Metrics Evaluated:
- Jurisdiction Auto-Detection Accuracy (Target: 100%)
- Statutory PII Identifier Recall Rate (Target: 100%)
- Overall PII Recall Rate (Target: 100%)
- PII Leakage Count (Target: 0)
- Clinical Pharmacology Preservation Rate (Target: 100%)
- Processing Latency (ms)
"""

import os
import sys
import re
import json
import time
from typing import Dict, Any, List
from tabulate import tabulate
import pymupdf

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.raster_checker import inspect_pdf_structure
from src.vector_redactor import VectorPDFRedactor
from src.image_redactor import LocalImageRedactor, resolve_tessdata_path
from src.jurisdiction import JurisdictionDetector


COHORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "multinational_cohort")
MANIFEST_PATH = os.path.join(COHORT_DIR, "manifest.json")
OUTPUT_DIR = os.path.join(COHORT_DIR, "redacted_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts all text from a PDF file."""
    doc = pymupdf.open(pdf_path)
    full_text = []
    for page in doc:
        full_text.append(page.get_text("text"))
    doc.close()
    return "\n".join(full_text)


def evaluate_specimen(case: Dict[str, Any], tessdata_dir: str = None) -> Dict[str, Any]:
    input_path = case["full_path"]
    filename = case["filename"]
    expected_jur = case["jurisdiction"]
    base_name, ext = os.path.splitext(filename)
    output_path = os.path.join(OUTPUT_DIR, f"{base_name}_redacted{ext}")

    start_time = time.perf_counter()

    # 1. Inspect format & detect text stream
    struct = inspect_pdf_structure(input_path)
    fmt = struct["format_type"]

    # 2. Test Auto-Detection
    raw_text = extract_text_from_pdf(input_path)
    detector = JurisdictionDetector()
    detected_jur = detector.detect(raw_text)

    # 3. Redact using AUTO jurisdiction
    if fmt == "VECTOR_DIGITAL":
        redactor = VectorPDFRedactor()
        report = redactor.redact(input_path, output_path, jurisdiction="AUTO")
    else:
        redactor = LocalImageRedactor(tessdata_dir=tessdata_dir)
        report = redactor.redact(input_path, output_path, jurisdiction="AUTO")

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # 4. Extract redacted text
    redacted_text = extract_text_from_pdf(output_path)
    redacted_text_lower = redacted_text.lower()
    norm_redacted = re.sub(r"[\s\-_:,./]+", "", redacted_text_lower)

    # 5. Check PII Recall
    gt_pii = case["ground_truth_pii"]
    leaked_pii: List[str] = []

    STOPWORDS = {
        "mr", "mrs", "ms", "miss", "dr", "or", "prof", "md", "mbbs",
        "of", "in", "the", "and", "at", "by", "for", "to",
        "street", "st", "rd", "road", "ave", "avenue", "blvd",
        "court", "drive", "no", "date", "reg", "phone", "tel"
    }

    for pii_item in gt_pii:
        norm_full = re.sub(r"[\s\-_:,./]+", "", pii_item.lower())
        if len(norm_full) >= 4 and norm_full in norm_redacted:
            leaked_pii.append(pii_item)
            continue

        tokens = [t for t in re.split(r"[\s\-_:,./]+", pii_item) if t]
        item_leaked = False
        for tok in tokens:
            tok_lower = tok.lower()
            if tok_lower in STOPWORDS:
                continue
            if re.match(r"^\d+$", tok):
                if len(tok) >= 4 and tok in norm_redacted:
                    item_leaked = True
                    break
            elif len(tok) >= 3:
                if tok_lower in norm_redacted or re.search(r"\b" + re.escape(tok) + r"\b", redacted_text, re.IGNORECASE):
                    item_leaked = True
                    break

        if item_leaked and pii_item not in leaked_pii:
            leaked_pii.append(pii_item)

    total_gt_pii = len(gt_pii)
    redacted_pii_count = total_gt_pii - len(leaked_pii)
    pii_recall_pct = (redacted_pii_count / total_gt_pii * 100.0) if total_gt_pii > 0 else 100.0

    # 6. Check Clinical Pharmacology Preservation
    gt_clinical = case["ground_truth_clinical"]
    preserved_clinical: List[str] = []
    missing_clinical: List[str] = []

    for med in gt_clinical:
        norm_med = re.sub(r"[\s\-_:,./]+", "", med.lower())
        if (norm_med in norm_redacted) or re.search(r"\b" + re.escape(med) + r"\b", redacted_text, re.IGNORECASE):
            preserved_clinical.append(med)
        else:
            missing_clinical.append(med)

    total_gt_clinical = len(gt_clinical)
    clinical_preserved_pct = (len(preserved_clinical) / total_gt_clinical * 100.0) if total_gt_clinical > 0 else 100.0

    jur_match = (detected_jur == expected_jur)
    passed = (pii_recall_pct == 100.0) and (clinical_preserved_pct == 100.0) and jur_match

    return {
        "filename": filename,
        "jurisdiction_expected": expected_jur,
        "jurisdiction_detected": detected_jur,
        "jurisdiction_match": jur_match,
        "entities_redacted_total": report.get("total_redactions_applied", 0),
        "total_gt_pii": total_gt_pii,
        "pii_leaks": len(leaked_pii),
        "leaked_pii_items": leaked_pii,
        "pii_recall_pct": round(pii_recall_pct, 2),
        "total_gt_clinical": total_gt_clinical,
        "preserved_clinical_count": len(preserved_clinical),
        "clinical_preserved_pct": round(clinical_preserved_pct, 2),
        "missing_clinical_items": missing_clinical,
        "elapsed_ms": round(elapsed_ms, 2),
        "status": "PASS" if passed else "FAIL"
    }


def run_multinational_benchmark() -> Dict[str, Any]:
    print("=" * 80)
    print("PHARMACON MULTI-NATIONAL HEALTHCARE DE-IDENTIFICATION BENCHMARK")
    print("=" * 80)
    print(f"Cohort Directory : {COHORT_DIR}")
    print(f"Output Directory : {OUTPUT_DIR}\n")

    if not os.path.exists(MANIFEST_PATH):
        raise FileNotFoundError(f"Manifest not found at {MANIFEST_PATH}. Run scripts/generate_multinational_cohort.py first.")

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    tessdata_dir = resolve_tessdata_path()

    for case in cases:
        print(f"Evaluating: {case['filename']} ({case['jurisdiction']} - {case['description']})...")
        res = evaluate_specimen(case, tessdata_dir)
        print(f" -> Jur Detect: {res['jurisdiction_detected']} [{'MATCH' if res['jurisdiction_match'] else 'MISMATCH'}] | "
              f"PII Recall: {res['pii_recall_pct']}% | "
              f"Clinical Preserved: {res['clinical_preserved_pct']}% "
              f"({res['elapsed_ms']} ms) -> {res['status']}")
        results.append(res)

    # Print Summary Table
    table_rows = []
    for r in results:
        table_rows.append([
            r["filename"],
            r["jurisdiction_expected"],
            r["jurisdiction_detected"],
            f"{r['pii_recall_pct']}% ({r['pii_leaks']} leaks)",
            f"{r['clinical_preserved_pct']}%",
            f"{r['elapsed_ms']} ms",
            r["status"]
        ])

    headers = ["Specimen", "Exp Jur", "Det Jur", "PII Recall", "Clin Preserved", "Latency", "Status"]
    print("\n" + "=" * 80)
    print("BENCHMARK MULTI-NATIONAL EVALUATION TABLE")
    print("=" * 80)
    print(tabulate(table_rows, headers=headers, tablefmt="fancy_grid"))

    # Aggregates
    total_cases = len(results)
    passed_cases = sum(1 for r in results if r["status"] == "PASS")
    avg_pii_recall = sum(r["pii_recall_pct"] for r in results) / total_cases if total_cases > 0 else 0
    total_leaks = sum(r["pii_leaks"] for r in results)
    avg_clinical_preserved = sum(r["clinical_preserved_pct"] for r in results) / total_cases if total_cases > 0 else 0
    jur_accuracy = sum(1 for r in results if r["jurisdiction_match"]) / total_cases * 100.0 if total_cases > 0 else 0
    total_latency = sum(r["elapsed_ms"] for r in results)

    print("\n" + "=" * 80)
    print("MULTI-NATIONAL BENCHMARK AGGREGATE SUMMARY")
    print("=" * 80)
    print(f"Total Jurisdictions Tested    : {total_cases} (US, UK, AU, EU, IN)")
    print(f"Jurisdiction Detection Rate   : {jur_accuracy:.2f}% (Target: 100.0%)")
    print(f"Average PII Recall Rate       : {avg_pii_recall:.2f}% (Target: 100.0%)")
    print(f"Total Statutory PII Leaks     : {total_leaks} (Target: 0)")
    print(f"Average Clinical Preserved    : {avg_clinical_preserved:.2f}% (Target: 100.0%)")
    print(f"Overall Pass Rate             : {passed_cases} / {total_cases} ({passed_cases / total_cases * 100:.1f}%)")
    print(f"Total Processing Latency      : {total_latency:.2f} ms (Avg: {total_latency / total_cases:.2f} ms/doc)")
    print("=" * 80 + "\n")

    summary_data = {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "jurisdiction_detection_accuracy": jur_accuracy,
        "avg_pii_recall": avg_pii_recall,
        "total_pii_leaks": total_leaks,
        "avg_clinical_preserved": avg_clinical_preserved,
        "total_latency_ms": total_latency,
        "results": results
    }

    results_file = os.path.join(COHORT_DIR, "benchmark_multinational_results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print(f"Saved benchmark results to: {results_file}")
    return summary_data


if __name__ == "__main__":
    summary = run_multinational_benchmark()
    if summary["passed_cases"] != summary["total_cases"]:
        sys.exit(1)
