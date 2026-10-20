"""
Native Vector PDF Redaction Engine.

Extracts PII bounding boxes directly from PDF text streams and applies
cryptographic/physical text deletion + black-box visual masking using PyMuPDF.
"""

from typing import List, Dict, Any, Tuple
import re
import pymupdf

try:
    from prescription_anonymizer.src.entities import (
        BoundingBox,
        RedactionTarget,
        PATIENT_NAME_ANCHORS,
        DEMOGRAPHIC_ANCHORS,
        IDENTIFIER_ANCHORS,
        CONTACT_ANCHORS,
        DOCTOR_ANCHORS,
        ADDRESS_ANCHORS,
        DATE_ANCHORS
    )
except ImportError:
    from src.entities import (
        BoundingBox,
        RedactionTarget,
        PATIENT_NAME_ANCHORS,
        DEMOGRAPHIC_ANCHORS,
        IDENTIFIER_ANCHORS,
        CONTACT_ANCHORS,
        DOCTOR_ANCHORS,
        ADDRESS_ANCHORS,
        DATE_ANCHORS
    )



class VectorPDFRedactor:
    """
    High-precision redactor for digitally generated PDFs with selectable text layers.
    """

    def __init__(self, expand_box: bool = True, padding_x: float = 4.0, padding_y: float = 2.0):
        self.expand_box = expand_box
        self.padding_x = padding_x
        self.padding_y = padding_y

    def find_pii_targets(self, doc: pymupdf.Document) -> List[RedactionTarget]:
        """Scan all pages and return bounding boxes of identified PII entities."""
        targets: List[RedactionTarget] = []

        all_rules = [
            ("PATIENT_NAME", PATIENT_NAME_ANCHORS),
            ("DEMOGRAPHIC", DEMOGRAPHIC_ANCHORS),
            ("IDENTIFIER", IDENTIFIER_ANCHORS),
            ("CONTACT", CONTACT_ANCHORS),
            ("DOCTOR_INFO", DOCTOR_ANCHORS),
            ("DATE", DATE_ANCHORS),
            ("ADDRESS", ADDRESS_ANCHORS),
        ]

        for page_idx, page in enumerate(doc):
            # Extract word-level text with bboxes: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
            words = page.get_text("words")
            text = page.get_text()

            # 1. Regex pattern scanning on line-level text
            for category, patterns in all_rules:
                for pattern in patterns:
                    for match in re.finditer(pattern, text):
                        matched_str = match.group(0).strip()
                        # Search for instances of the matched phrase on the page
                        rects = page.search_for(matched_str)
                        for r in rects:
                            bbox = BoundingBox(x0=r.x0, y0=r.y0, x1=r.x1, y1=r.y1)
                            targets.append(RedactionTarget(
                                page_number=page_idx + 1,
                                category=category,
                                raw_text=matched_str,
                                bbox=bbox,
                                confidence=0.98,
                                engine="vector_rule"
                            ))

            # 2. Specific field-value boundary expansion:
            # When "Patient Name:" or "Name:" is matched, redact the value immediately following it
            name_label_rects = page.search_for("Patient Name:") + page.search_for("Name:")
            for n_rect in name_label_rects:
                # Value area: from end of label up to 200 pts rightward on same line
                val_rect = pymupdf.Rect(n_rect.x1 + 2, n_rect.y0 - 2, min(page.rect.width - 40, n_rect.x1 + 180), n_rect.y1 + 2)
                targets.append(RedactionTarget(
                    page_number=page_idx + 1,
                    category="PATIENT_NAME_VALUE",
                    raw_text="[NAME_FIELD_VALUE]",
                    bbox=BoundingBox(x0=val_rect.x0, y0=val_rect.y0, x1=val_rect.x1, y1=val_rect.y1),
                    confidence=0.99,
                    engine="vector_geometry"
                ))

        return targets

    def redact(self, input_pdf_path: str, output_pdf_path: str) -> Dict[str, Any]:
        """
        Executes complete text-deletion and visual masking on the PDF.
        Returns audit summary with redacted entities.
        """
        doc = pymupdf.open(input_pdf_path)
        targets = self.find_pii_targets(doc)

        # Apply redactions page by page
        for t in targets:
            page = doc[t.page_number - 1]
            rect = pymupdf.Rect(
                max(0, t.bbox.x0 - self.padding_x),
                max(0, t.bbox.y0 - self.padding_y),
                t.bbox.x1 + self.padding_x,
                t.bbox.y1 + self.padding_y
            )
            # Add redaction annotation (solid black fill, zero stroke)
            page.add_redact_annot(rect, fill=(0, 0, 0))

        # Physically erase text streams and render black rectangles
        for page in doc:
            page.apply_redactions()

        # Wipe document metadata to prevent file-property leaks
        doc.set_metadata({
            "title": "Redacted Medical Document",
            "author": "Pharmacon Anonymizer",
            "subject": "De-identified Prescription",
            "keywords": "anonymized, de-identified",
            "creator": "Pharmacon Anonymizer Engine",
            "producer": "PyMuPDF",
            "creationDate": "",
            "modDate": ""
        })

        doc.save(output_pdf_path, garbage=4, deflate=True)
        doc.close()

        return {
            "input_file": input_pdf_path,
            "output_file": output_pdf_path,
            "total_entities_redacted": len(targets),
            "redacted_targets": [t.model_dump() for t in targets]
        }
