#!/usr/bin/env python3
"""
Pharmacon Medical Prescription Anonymizer CLI.

Usage:
    python anonymize.py --input <path_to_prescription_pdf_or_image_or_directory> [--output <output_path>] [--json]
"""

import argparse
import os
import sys
import json
from typing import Dict, Any, List

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from prescription_anonymizer.src.raster_checker import inspect_pdf_structure
    from prescription_anonymizer.src.vector_redactor import VectorPDFRedactor
    from prescription_anonymizer.src.image_redactor import LocalImageRedactor
except ImportError:
    from src.raster_checker import inspect_pdf_structure
    from src.vector_redactor import VectorPDFRedactor
    from src.image_redactor import LocalImageRedactor

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}


def process_file(input_file: str, output_file: str, vector_redactor: VectorPDFRedactor = None, image_redactor: LocalImageRedactor = None) -> Dict[str, Any]:
    """Inspects and anonymizes a single document or image."""
    structure = inspect_pdf_structure(input_file)
    fmt = structure["format_type"]

    if fmt == "VECTOR_DIGITAL":
        redactor = vector_redactor or VectorPDFRedactor()
        engine_name = "Native Vector Stream Redactor (PyMuPDF)"
        report = redactor.redact(input_file, output_file)
    else:
        redactor = image_redactor or LocalImageRedactor()
        engine_name = "Scanned Raster Image Redactor (Local OCR Anchor Engine)"
        report = redactor.redact(input_file, output_file)

    report["format_type"] = fmt
    report["page_count"] = structure["page_count"]
    report["engine"] = engine_name
    return report


def main():
    parser = argparse.ArgumentParser(description="De-identify medical prescriptions (PDF/Image/Directory)")
    parser.add_argument("--input", "-i", required=True, help="Path to input prescription file or directory")
    parser.add_argument("--output", "-o", default=None, help="Path to output file or directory")
    parser.add_argument("--json", action="store_true", help="Print audit report as JSON")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        print(f"Error: Path not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # -------------------------------------------------------------------
    # Batch Processing: Directory Mode
    # -------------------------------------------------------------------
    if os.path.isdir(input_path):
        files_to_process: List[str] = []
        for root, _, filenames in os.walk(input_path):
            for fname in sorted(filenames):
                ext = os.path.splitext(fname)[1].lower()
                if ext in SUPPORTED_EXTENSIONS and not fname.endswith("_anonymized" + ext):
                    files_to_process.append(os.path.join(root, fname))

        if not files_to_process:
            print(f"No valid prescription files found in directory: {input_path}", file=sys.stderr)
            sys.exit(0)

        out_dir = os.path.abspath(args.output) if args.output else os.path.join(input_path, "anonymized_output")
        os.makedirs(out_dir, exist_ok=True)

        vec_redactor = VectorPDFRedactor()
        img_redactor = LocalImageRedactor()

        batch_reports = []
        for fpath in files_to_process:
            rel = os.path.relpath(fpath, input_path)
            base, ext = os.path.splitext(rel)
            out_file = os.path.join(out_dir, f"{base}_anonymized{ext}")
            os.makedirs(os.path.dirname(out_file), exist_ok=True)
            try:
                rep = process_file(fpath, out_file, vec_redactor, img_redactor)
                rep["status"] = "SUCCESS"
                batch_reports.append(rep)
            except Exception as e:
                batch_reports.append({
                    "input_file": fpath,
                    "output_file": out_file,
                    "status": "ERROR",
                    "error": str(e)
                })

        if args.json:
            print(json.dumps({
                "mode": "BATCH_DIRECTORY",
                "input_directory": input_path,
                "output_directory": out_dir,
                "total_files": len(files_to_process),
                "successful": sum(1 for r in batch_reports if r.get("status") == "SUCCESS"),
                "reports": batch_reports
            }, indent=2))
            return

        print("=" * 75)
        print("PHARMACON MEDICAL PRESCRIPTION ANONYMIZER: BATCH EXECUTION")
        print("=" * 75)
        print(f"Source Directory : {input_path}")
        print(f"Target Directory : {out_dir}")
        print(f"Total Prescriptions Processed: {len(files_to_process)}")
        print("-" * 75)
        for rep in batch_reports:
            fname = os.path.basename(rep["input_file"])
            if rep["status"] == "SUCCESS":
                print(f"  ✓ {fname:<35} | {rep['format_type']:<15} | Masked {rep['total_entities_redacted']} entities")
            else:
                print(f"  ✗ {fname:<35} | FAILED: {rep.get('error')}")
        print("=" * 75)
        print(f"All anonymized files safely stored in: {out_dir}\n")
        return

    # -------------------------------------------------------------------
    # Single File Mode
    # -------------------------------------------------------------------
    if args.output is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_anonymized{ext}"
    else:
        output_path = os.path.abspath(args.output)

    report = process_file(input_path, output_path)

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print("=" * 70)
    print("PHARMACON MEDICAL PRESCRIPTION ANONYMIZER")
    print("=" * 70)
    print(f"Input Document : {input_path}")
    print(f"Output Target  : {output_path}")
    print(f"Document Format: {report['format_type']} ({report['page_count']} pages)")
    print(f"Routing to     : {report['engine']}")
    print(f"Status         : SUCCESS")
    print(f"Redacted Units : {report['total_entities_redacted']} PII/PHI entities masked")
    for t in report["redacted_targets"][:20]:
        print(f"  - [{t['category']}] {repr(t.get('raw_text'))}")
    if len(report["redacted_targets"]) > 20:
        print(f"  ... and {len(report['redacted_targets']) - 20} more entities masked.")
    print("=" * 70)
    print(f"Saved anonymized document to: {output_path}\n")


if __name__ == "__main__":
    main()
