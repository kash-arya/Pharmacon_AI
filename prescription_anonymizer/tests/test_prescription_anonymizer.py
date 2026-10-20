"""
Unit and Integration Test Suite for Pharmacon Prescription Anonymizer.
"""

import os
import sys
import unittest
import json
import tempfile
import pymupdf
from PIL import Image

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.raster_checker import inspect_pdf_structure
from src.vector_redactor import VectorPDFRedactor
from src.image_redactor import LocalImageRedactor, resolve_tessdata_path
from src.forensics import ForensicAuditor
from src.vlm_grounder import MultimodalVisualGrounder
from benchmarks.benchmark import run_benchmark, BENCHMARK_CASES
from viewer.viewer import build_viewer_data, generate_html
from anonymize import process_file


class TestPrescriptionAnonymizer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.samples_dir = os.path.join(cls.repo_dir, "data", "samples")
        cls.vector_pdf = os.path.join(cls.samples_dir, "sample_digital_vector_prescription.pdf")
        cls.scanned_pdf_1 = os.path.join(cls.samples_dir, "sample_prescription_1.pdf")
        cls.scanned_pdf_2 = os.path.join(cls.samples_dir, "sample_prescription_2.pdf")
        cls.patient_pdf = os.path.join(cls.samples_dir, "sample_patient_details_1.pdf")
        cls.sample_image = os.path.join(cls.samples_dir, "extracted_images", "sample_prescription_1_p1.png")
        cls.temp_dir = tempfile.mkdtemp(prefix="test_pharmacon_")

    # -----------------------------------------------------------------------
    # Raster Checker Tests
    # -----------------------------------------------------------------------
    def test_raster_checker_digital_vector(self):
        struct = inspect_pdf_structure(self.vector_pdf)
        self.assertEqual(struct["format_type"], "VECTOR_DIGITAL")
        self.assertGreater(struct["total_char_count"], 100)

    def test_raster_checker_scanned_pdf(self):
        struct = inspect_pdf_structure(self.scanned_pdf_1)
        self.assertEqual(struct["format_type"], "SCANNED_RASTER")
        self.assertEqual(struct["total_char_count"], 0)

    def test_raster_checker_image_file(self):
        struct = inspect_pdf_structure(self.sample_image)
        self.assertEqual(struct["format_type"], "SCANNED_RASTER")
        self.assertEqual(struct["page_count"], 1)

    # -----------------------------------------------------------------------
    # Vector Redactor Tests
    # -----------------------------------------------------------------------
    def test_vector_redactor_execution(self):
        redactor = VectorPDFRedactor()
        out_pdf = os.path.join(self.temp_dir, "test_vector_out.pdf")
        report = redactor.redact(self.vector_pdf, out_pdf)

        self.assertGreaterEqual(report["total_entities_redacted"], 10)
        self.assertTrue(os.path.exists(out_pdf))

        # Verify no PII leak in output PDF
        doc = pymupdf.open(out_pdf)
        text = doc[0].get_text().lower()
        doc.close()

        for pii in ["rajesh sharma", "anita desai", "mci-44912", "98110 23456", "dr.sharma@"]:
            self.assertNotIn(pii, text)

        # Verify clinical pharmacology preserved
        for clin in ["telmisartan 40 mg", "amlodipine 5 mg", "paracetamol 650 mg"]:
            self.assertIn(clin, text)

    # -----------------------------------------------------------------------
    # Local Image Redactor Tests
    # -----------------------------------------------------------------------
    def test_tessdata_resolution(self):
        tessdata = resolve_tessdata_path()
        self.assertTrue(os.path.isdir(tessdata))
        self.assertTrue(os.path.exists(os.path.join(tessdata, "eng.traineddata")))

    def test_image_redactor_scanned_pdf(self):
        redactor = LocalImageRedactor()
        out_pdf = os.path.join(self.temp_dir, "test_scanned_out.pdf")
        report = redactor.redact(self.scanned_pdf_1, out_pdf)

        self.assertGreaterEqual(report["total_entities_redacted"], 5)
        self.assertTrue(os.path.exists(out_pdf))

        # Verify OCR on redacted document has zero PII leaks
        doc = pymupdf.open(out_pdf)
        page0 = doc[0]
        tp = page0.get_textpage_ocr(language="eng", dpi=150, tessdata=redactor.tessdata_dir)
        text = page0.get_text(textpage=tp).lower()
        doc.close()

        for pii in ["maria sharapova", "john smith", "non-important street", "5/11/2022"]:
            self.assertNotIn(pii, text)

        # Verify clinical preservation
        for clin in ["prednisone", "20 mg"]:
            self.assertIn(clin, text)
        self.assertTrue("lialda" in text or "liatda" in text or "2.4 gram" in text)

    def test_image_redactor_standalone_image(self):
        redactor = LocalImageRedactor()
        out_img = os.path.join(self.temp_dir, "test_image_out.png")
        report = redactor.redact(self.sample_image, out_img)

        self.assertGreaterEqual(report["total_entities_redacted"], 5)
        self.assertTrue(os.path.exists(out_img))

        # Check preserved dimensions
        with Image.open(self.sample_image) as orig_img, Image.open(out_img) as res_img:
            self.assertEqual(orig_img.size, res_img.size)

    # -----------------------------------------------------------------------
    # Benchmark Evaluation Tests
    # -----------------------------------------------------------------------
    def test_automated_benchmark_all_passed(self):
        out_json = os.path.join(self.temp_dir, "test_bench_results.json")
        out_dir = os.path.join(self.temp_dir, "bench_outputs")

        results = run_benchmark(
            samples_dir=self.samples_dir,
            output_dir=out_dir,
            results_json_path=out_json
        )

        self.assertEqual(results["summary"]["status"], "PASS")
        self.assertEqual(results["summary"]["pass_rate_pct"], 100.0)
        self.assertEqual(results["summary"]["average_pii_recall_pct"], 100.0)
        self.assertEqual(results["summary"]["total_pii_leaks"], 0)
        self.assertEqual(results["summary"]["average_clinical_preservation_pct"], 100.0)

    # -----------------------------------------------------------------------
    # Viewer Generation Tests
    # -----------------------------------------------------------------------
    def test_viewer_html_generation(self):
        temp_cache = os.path.join(self.temp_dir, "viewer_cache")
        data = build_viewer_data(self.samples_dir, temp_cache)
        self.assertGreaterEqual(len(data["documents"]), 4)

        html = generate_html(data)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Pharmacon Prescription Anonymizer", html)
        self.assertTrue("data:image/jpeg;base64," in html or "data:image/png;base64," in html)
        self.assertIn("Side-by-Side", html)
        self.assertIn("Interactive Slider", html)

    # -----------------------------------------------------------------------
    # Forensic Security & Multimodal Tests
    # -----------------------------------------------------------------------
    def test_forensic_auditor_compliance_certificate(self):
        redactor = VectorPDFRedactor()
        out_pdf = os.path.join(self.temp_dir, "test_forensic_out.pdf")
        redactor.redact(self.vector_pdf, out_pdf)

        auditor = ForensicAuditor()
        cert = auditor.generate_compliance_certificate(
            out_pdf,
            known_pii_strings=["Rajesh Sharma", "Anita Desai", "98110 23456", "MCI-44912"]
        )
        self.assertEqual(cert["compliance_status"], "CERTIFIED_SECURE")
        self.assertEqual(cert["byte_stream_leak_count"], 0)
        self.assertTrue(cert["metadata_sanitized"])

    def test_multimodal_visual_grounder(self):
        grounder = MultimodalVisualGrounder()
        # Test on real phone prescription image
        phone_img = os.path.join(self.repo_dir, "data", "real_phone_prescriptions", "Aryan March 25.jpg")
        if os.path.exists(phone_img):
            targets = grounder.detect_visual_pii(phone_img)
            self.assertIsInstance(targets, list)

    def test_batch_directory_processing_logic(self):
        out_batch_dir = os.path.join(self.temp_dir, "test_batch_run")
        os.makedirs(out_batch_dir, exist_ok=True)
        # Test process_file helper
        out_sample = os.path.join(out_batch_dir, "sample_out.pdf")
        rep = process_file(self.vector_pdf, out_sample)
        self.assertEqual(rep["format_type"], "VECTOR_DIGITAL")
        self.assertTrue(os.path.exists(out_sample))


if __name__ == "__main__":
    unittest.main()
