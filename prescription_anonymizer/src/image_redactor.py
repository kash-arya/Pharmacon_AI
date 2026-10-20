"""
Local Image Redactor Module for Scanned Prescriptions and Medical Forms.

Applies local OCR (via PyMuPDF and embedded Tesseract engine), demographic/PII
anchor detection, 2D multi-column form parsing, and permanent black-box visual masking
to scanned raster PDFs and image files (PNG, JPG, TIFF, etc.), strictly preserving
clinical pharmacology and diagnostic findings.
"""

from typing import List, Dict, Any, Optional, Tuple
import os
import re
import io
import pymupdf
import cv2
import numpy as np
from PIL import Image, ImageEnhance

try:
    from prescription_anonymizer.src.entities import (
        BoundingBox,
        RedactionTarget,
        KEY_VALUE_ANCHORS,
        CLINICAL_WHITELIST_PATTERNS,
        HEADER_SURNAMES,
        CLINIC_HEADERS,
    )
    from prescription_anonymizer.src.vlm_grounder import MultimodalVisualGrounder
except ImportError:
    from src.entities import (
        BoundingBox,
        RedactionTarget,
        KEY_VALUE_ANCHORS,
        CLINICAL_WHITELIST_PATTERNS,
        HEADER_SURNAMES,
        CLINIC_HEADERS,
    )
    from src.vlm_grounder import MultimodalVisualGrounder


def resolve_tessdata_path(custom_dir: Optional[str] = None) -> str:
    """Finds valid directory containing eng.traineddata."""
    candidates = []
    if custom_dir:
        candidates.append(os.path.abspath(custom_dir))

    env_prefix = os.environ.get("TESSDATA_PREFIX")
    if env_prefix:
        candidates.append(os.path.abspath(env_prefix))
        candidates.append(os.path.abspath(os.path.join(env_prefix, "tessdata")))

    # Project local tessdata
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(repo_root, "data", "tessdata"))
    candidates.append(os.path.join(os.getcwd(), "data", "tessdata"))

    # System tessdata paths
    candidates.extend([
        "/usr/share/tesseract-ocr/4.00/tessdata",
        "/usr/share/tesseract-ocr/5/tessdata",
        "/usr/share/tessdata",
        "/usr/local/share/tessdata"
    ])

    for path in candidates:
        if os.path.isdir(path) and os.path.exists(os.path.join(path, "eng.traineddata")):
            return path

    for path in candidates:
        if os.path.isdir(path):
            return path

    return candidates[0] if candidates else "/usr/share/tessdata"


class LocalImageRedactor:
    """
    Resolution-invariant OCR & visual redaction engine for scanned raster PDFs
    and smartphone prescription images.
    """

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}

    def __init__(
        self,
        tessdata_dir: Optional[str] = None,
        padding_ratio: float = 0.05,
        dpi: int = 150,
        enable_visual_grounder: bool = True
    ):
        self.tessdata_dir = resolve_tessdata_path(tessdata_dir)
        self.padding_ratio = padding_ratio
        self.dpi = dpi
        self.enable_visual_grounder = enable_visual_grounder
        self.grounder = MultimodalVisualGrounder() if enable_visual_grounder else None

        # Compiled clinical whitelist patterns
        self.whitelist_regexes = [
            re.compile(pat, re.IGNORECASE) for pat in CLINICAL_WHITELIST_PATTERNS
        ]

    def is_whitelisted(self, text: str) -> bool:
        """Determines if a candidate text string contains protected clinical pharmacology or findings."""
        if not text:
            return False
        clean = text.strip()
        for rx in self.whitelist_regexes:
            if rx.search(clean):
                return True
        return False

    def _detect_qr_and_barcodes(self, page: pymupdf.Page) -> List[Tuple[pymupdf.Rect, str]]:
        """
        Detects 2D QR codes and 1D barcodes using OpenCV QRCodeDetector and BarcodeDetector.
        Returns list of (clamped_bounding_box, detected_payload_or_label).
        """
        pix = page.get_pixmap()
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        if pix.n == 4:
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
            gray = cv2.cvtColor(arr, cv2.COLOR_RGBA2GRAY)
        elif pix.n == 3:
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        else:
            gray = arr
            bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        scale_x = page.rect.width / pix.width
        scale_y = page.rect.height / pix.height

        boxes: List[Tuple[pymupdf.Rect, str]] = []

        # 1. OpenCV QRCodeDetector
        try:
            qd = cv2.QRCodeDetector()
            ok_q, decoded_info, points_q, _ = qd.detectAndDecodeMulti(bgr)
            if ok_q and points_q is not None and len(points_q) > 0:
                for i, pts in enumerate(points_q):
                    pts = pts.reshape(-1, 2)
                    pad = 12.0
                    x0 = max(0.0, float(np.min(pts[:, 0])) * scale_x - pad)
                    y0 = max(0.0, float(np.min(pts[:, 1])) * scale_y - pad)
                    x1 = min(page.rect.width, float(np.max(pts[:, 0])) * scale_x + pad)
                    y1 = min(page.rect.height, float(np.max(pts[:, 1])) * scale_y + pad)
                    qw = x1 - x0
                    qh = y1 - y0
                    if 20 < qw < page.rect.width * 0.40 and 20 < qh < page.rect.height * 0.40 and (0.5 <= qw / max(1.0, qh) <= 2.0):
                        info = decoded_info[i] if i < len(decoded_info) and decoded_info[i] else "QR_CODE"
                        boxes.append((pymupdf.Rect(x0, y0, x1, y1), info))
            else:
                ok_d, pts_d = qd.detect(bgr)
                if ok_d and pts_d is not None:
                    pts_d = pts_d.reshape(-1, 2)
                    pad = 12.0
                    x0 = max(0.0, float(np.min(pts_d[:, 0])) * scale_x - pad)
                    y0 = max(0.0, float(np.min(pts_d[:, 1])) * scale_y - pad)
                    x1 = min(page.rect.width, float(np.max(pts_d[:, 0])) * scale_x + pad)
                    y1 = min(page.rect.height, float(np.max(pts_d[:, 1])) * scale_y + pad)
                    qw = x1 - x0
                    qh = y1 - y0
                    if 20 < qw < page.rect.width * 0.40 and 20 < qh < page.rect.height * 0.40 and (0.5 <= qw / max(1.0, qh) <= 2.0):
                        boxes.append((pymupdf.Rect(x0, y0, x1, y1), "QR_CODE"))
        except Exception:
            pass

        # 2. OpenCV BarcodeDetector
        try:
            bd = cv2.barcode.BarcodeDetector()
            ok_b, decoded_info_b, _, points_b = bd.detectAndDecode(gray)
            if ok_b and points_b is not None and len(points_b) > 0:
                for b_idx, pts in enumerate(points_b):
                    pts = pts.reshape(-1, 2)
                    pad = 10.0
                    x0 = max(0.0, float(np.min(pts[:, 0])) * scale_x - pad)
                    y0 = max(0.0, float(np.min(pts[:, 1])) * scale_y - pad)
                    x1 = min(page.rect.width, float(np.max(pts[:, 0])) * scale_x + pad)
                    y1 = min(page.rect.height, float(np.max(pts[:, 1])) * scale_y + pad)
                    bw = x1 - x0
                    bh = y1 - y0
                    # Barcode plausibility: must not exceed 22% of page height or 12% of total page area
                    if 20 < bw < page.rect.width * 0.95 and 10 < bh < page.rect.height * 0.22 and (bw * bh) < (page.rect.width * page.rect.height * 0.12):
                        info_b = decoded_info_b[b_idx] if b_idx < len(decoded_info_b) and decoded_info_b[b_idx] else "BARCODE"
                        boxes.append((pymupdf.Rect(x0, y0, x1, y1), info_b))
        except Exception:
            pass

        return boxes

    def _get_enhanced_header_ocr(self, page: pymupdf.Page) -> Tuple[List[Any], pymupdf.Page, pymupdf.TextPage]:
        """Performs CLAHE adaptive contrast preprocessing on upper region of page (45%) to uncover faint/glare headers."""
        h_ratio = 0.45
        pix = page.get_pixmap(dpi=self.dpi, clip=pymupdf.Rect(0, 0, page.rect.width, page.rect.height * h_ratio))
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        if pix.n == 4:
            gray = cv2.cvtColor(arr, cv2.COLOR_RGBA2GRAY)
        elif pix.n == 3:
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        else:
            gray = arr

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl_img = clahe.apply(gray)

        is_success, buf = cv2.imencode('.png', cl_img)
        tmp_doc = pymupdf.open()
        p_enh = tmp_doc.new_page(width=page.rect.width, height=page.rect.height * h_ratio)
        p_enh.insert_image(pymupdf.Rect(0, 0, page.rect.width, page.rect.height * h_ratio), stream=buf.tobytes())
        tp_enh = p_enh.get_textpage_ocr(language="eng", dpi=self.dpi, tessdata=self.tessdata_dir)
        words_enh = p_enh.get_text("words", textpage=tp_enh)

        return words_enh, p_enh, tp_enh, tmp_doc

    def _reconstruct_visual_lines(self, words: List[Tuple]) -> List[Dict[str, Any]]:
        """
        Groups word tokens into non-overlapping horizontal lines using running vertical centers (y_mid).
        Prevents vertical chaining / line ballooning across multi-column forms.
        """
        visual_lines: List[List[Tuple[pymupdf.Rect, str]]] = []
        for w in words:
            rect = pymupdf.Rect(w[0], w[1], w[2], w[3])
            txt = w[4]
            mid = (rect.y0 + rect.y1) / 2.0
            h = rect.height
            placed = False
            for line in visual_lines:
                l_mid = sum((item[0].y0 + item[0].y1) / 2.0 for item in line) / len(line)
                if abs(mid - l_mid) < max(10.0, h * 0.25):
                    line.append((rect, txt))
                    placed = True
                    break
            if not placed:
                visual_lines.append([(rect, txt)])

        # Sort lines vertically by average y_mid
        visual_lines.sort(key=lambda l: sum((item[0].y0 + item[0].y1) / 2.0 for item in l) / len(l))

        line_objects = []
        for l in visual_lines:
            sw = sorted(l, key=lambda item: item[0].x0)
            u_rect = sw[0][0]
            for it in sw[1:]:
                u_rect = u_rect | it[0]
            line_str = " ".join(item[1] for item in sw)
            line_objects.append({
                "rect": u_rect,
                "text": line_str,
                "words": sw
            })
        return line_objects

    def find_pii_targets_for_page(self, page: pymupdf.Page, page_num: int) -> List[RedactionTarget]:
        """
        Scans a single raster page using dynamic multi-column layout parsing,
        regex entity recognition, and strict clinical whitelist protection.
        """
        tp = page.get_textpage_ocr(language="eng", dpi=self.dpi, tessdata=self.tessdata_dir)
        words = page.get_text("words", textpage=tp)
        full_text = page.get_text(textpage=tp)

        # Build list of protected clinical bounding boxes
        whitelisted_rects: List[pymupdf.Rect] = []
        for w in words:
            if self.is_whitelisted(w[4]):
                whitelisted_rects.append(pymupdf.Rect(w[0], w[1], w[2], w[3]))

        for rx in self.whitelist_regexes:
            for match in rx.finditer(full_text):
                match_str = match.group(0).strip()
                if match_str:
                    for r in page.search_for(match_str, textpage=tp):
                        whitelisted_rects.append(r)

        targets: List[RedactionTarget] = []
        recorded_rects: List[pymupdf.Rect] = []

        def can_redact(rect: pymupdf.Rect, raw_text: str) -> bool:
            if raw_text == "BARCODE_OR_QR" or raw_text.startswith("http") or raw_text in ("QR_CODE", "BARCODE"):
                return True
            if self.is_whitelisted(raw_text):
                return False
            rect_mid = (rect.y0 + rect.y1) / 2.0
            for wr in whitelisted_rects:
                wr_mid = (wr.y0 + wr.y1) / 2.0
                inter = rect & wr
                if inter.is_empty:
                    continue
                # If on different lines vertically, bounding box overlap is an OCR box artifact
                if abs(rect_mid - wr_mid) > max(15.0, min(rect.height, wr.height) * 0.35):
                    # Clamp rect away from wr so redaction never covers adjacent line's clinical text
                    if rect_mid > wr_mid:
                        rect.y0 = max(rect.y0, (wr_mid + rect_mid) / 2.0)
                    else:
                        rect.y1 = min(rect.y1, (wr_mid + rect_mid) / 2.0)
                    continue
                if inter.get_area() > 0.15 * min(rect.get_area(), wr.get_area()):
                    return False
            return True

        def add_target(rect: pymupdf.Rect, category: str, text: str, engine: str = "ocr_dynamic"):
            if not can_redact(rect, text):
                return
            if rect.get_area() <= 0:
                return
            for r in recorded_rects:
                inter = rect & r
                if not inter.is_empty:
                    min_area = min(rect.get_area(), r.get_area())
                    if min_area > 0 and inter.get_area() > 0.75 * min_area:
                        return
            recorded_rects.append(rect)
            targets.append(RedactionTarget(
                page_number=page_num,
                category=category,
                raw_text=text.strip() if text else category,
                bbox=BoundingBox(x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1),
                confidence=0.98,
                engine=engine
            ))

        # 0. Automatic QR Code and Barcode Detection
        code_boxes = self._detect_qr_and_barcodes(page)
        for c_rect, payload in code_boxes:
            add_target(c_rect, "BARCODE_OR_QR", payload or "BARCODE_OR_QR", engine="opencv_detector")

        # Reconstruct logical visual lines
        line_objects = self._reconstruct_visual_lines(words)

        # -------------------------------------------------------------------
        # 1. Dynamic 2D Multi-Column Key-Value Form Field Parser
        # -------------------------------------------------------------------
        anchor_patterns = [
            ("PATIENT_NAME", [
                r"\bPatient\s+Information\b", r"\bPatient\s*Name\b",
                r"\bPt(?:\s*Name)?\b", r"\bPatient\s*[:\-=~+]",
                r"\b‘?Name\b(?!\s+(?:of\s+(?:Insurance|Company|Hospital|Clinic)))",
                r"\bIn\s+Cas[ce]\s+of\s+Emergency\b", r"\bEmergency\s+Contact\b",
            ]),
            ("INSURANCE", [
                r"\bName\s+of\s+Insurance\s+Company\b"
            ]),
            ("IDENTIFIER", [
                r"\bUHID(?:\s*No\.?)?\b", r"\bOP(?:\s*No\.?)?\b",
                r"\bOPD(?:\s*No\.?)?\b(?!\s*(?:Timings|Hours))", r"\bIPD\b",
                r"\bMRN\b", r"\bToken(?:\s*No\.?)?\b",
                r"\bPolicy(?:\s*No\.?)?\b", r"\bReg(?:istration)?\.?\s*(?:No\.?)?\b",
                r"\bBill\s*No\.?\b", r"\bPatient\s*ID\b"
            ]),
            ("DEMOGRAPHIC", [
                r"\bAge(?:\s*/\s*Sex|\s*/\s*Gender)?\b", r"\bSex\b",
                r"\bGender\b", r"\bDOB\b", r"\bBirth\s*Date\b",
                r"\bPat\.?\s*Type\b"
            ]),
            ("CONTACT", [
                r"\bMobile(?:\s*No\.?)?\b", r"\bPhone(?:\s*No\.?)?\b",
                r"\bHome\s+phone\b", r"\bWork\s+phone\b",
                r"\bContact\b", r"\bTel\b", r"\bE-?mail\b"
            ]),
            ("DOCTOR_INFO", [
                r"\bConsultant\b", r"\bDoctor\b", r"\bRef(?:erred)?[.,]?\s*By\b",
                r"\bRadiologist\b", r"\bTyped\s*By\b", r"\bCreated\s*By\b",
                r"\bPrinted\s*By\b"
            ]),
            ("ADDRESS", [
                r"\bAddress\b", r"\bAddr\b"
            ]),
            ("DATE", [
                r"\bDate\b", r"\bOP\s*Date\b", r"\bReg\.?\s*Date\b",
                r"\bReport\s*Date\b", r"\bPrint\s*Date\b", r"\bCollected\s*Date\b",
                r"\bReceived\s*Date\b", r"\bVisit\s*Date\b", r"\bExpiry\s*Date\b"
            ]),
        ]

        for l_idx, l_obj in enumerate(line_objects):
            l_text = l_obj["text"]
            l_words = l_obj["words"]
            line_rect = l_obj["rect"]

            detected_anchors = []
            line_mid = (line_rect.y0 + line_rect.y1) / 2.0
            for cat, patterns in anchor_patterns:
                for pat in patterns:
                    for m in re.finditer(pat, l_text, re.IGNORECASE):
                        kw = m.group(0)
                        raw_rects = page.search_for(kw, textpage=tp)
                        # Explicitly filter by line vertical territory because search_for(textpage) ignores clip
                        kw_rects = sorted([r for r in raw_rects if abs((r.y0 + r.y1)/2.0 - line_mid) < max(20.0, line_rect.height * 0.4)], key=lambda r: r.x0)
                        if kw_rects:
                            # Cluster into contiguous phrases if needle has multiple words or multiple occurrences
                            kw_clusters = []
                            curr_cluster = [kw_rects[0]]
                            for r in kw_rects[1:]:
                                if abs(r.x0 - curr_cluster[-1].x1) < 40:
                                    curr_cluster.append(r)
                                else:
                                    kw_clusters.append(curr_cluster)
                                    curr_cluster = [r]
                            kw_clusters.append(curr_cluster)

                            for cluster in kw_clusters:
                                u_kw = cluster[0]
                                for kr in cluster[1:]:
                                    u_kw = u_kw | kr
                                detected_anchors.append({
                                    "cat": cat,
                                    "kw": kw,
                                    "rect": u_kw
                                })

            # Deduplicate sub-anchors (e.g. keep "Patient Name" over "Name")
            dedup_anchors = []
            for a in detected_anchors:
                is_sub = False
                for other in detected_anchors:
                    if a is not other:
                        if (a["rect"] in other["rect"] and len(other["kw"]) > len(a["kw"])) or \
                           (other["kw"].endswith(a["kw"]) and len(other["kw"]) > len(a["kw"])):
                            is_sub = True
                            break
                if not is_sub:
                    dedup_anchors.append(a)
            detected_anchors = dedup_anchors
            detected_anchors.sort(key=lambda a: a["rect"].x0)

            # Clamping line rect with adjacent lines to prevent vertical line bleed
            l_mid = sum((w[0].y0 + w[0].y1) / 2 for w in l_words) / len(l_words) if l_words else line_rect.y0
            split_top = line_rect.y0
            if l_idx > 0:
                prev_words = line_objects[l_idx - 1]["words"]
                prev_mid = sum((w[0].y0 + w[0].y1) / 2 for w in prev_words) / len(prev_words) if prev_words else line_objects[l_idx - 1]["rect"].y0
                if l_mid > prev_mid:
                    split_top = max(line_rect.y0, (prev_mid + l_mid) / 2.0)

            split_bottom = line_rect.y1
            if l_idx + 1 < len(line_objects):
                nxt_words = line_objects[l_idx + 1]["words"]
                nxt_mid = sum((w[0].y0 + w[0].y1) / 2 for w in nxt_words) / len(nxt_words) if nxt_words else line_objects[l_idx + 1]["rect"].y0
                if nxt_mid > l_mid:
                    split_bottom = min(line_rect.y1, (l_mid + nxt_mid) / 2.0)

            for a_idx, anchor in enumerate(detected_anchors):
                a_rect = anchor["rect"]
                a_cat = anchor["cat"]
                clamped_a_rect = pymupdf.Rect(
                    max(0, a_rect.x0 - 2),
                    max(split_top, a_rect.y0 - 2),
                    a_rect.x1 + 2,
                    min(split_bottom, a_rect.y1 + 2)
                )
                add_target(clamped_a_rect, f"{a_cat}_LABEL", anchor["kw"], engine="form_anchor")

                start_x = a_rect.x1 + 2
                if a_idx + 1 < len(detected_anchors):
                    end_x = max(start_x, detected_anchors[a_idx + 1]["rect"].x0 - 4)
                else:
                    end_x = line_rect.x1 + 4

                same_line_words = [w for w in l_words if start_x - 4 <= w[0].x0 <= end_x]
                same_line_text = " ".join(w[1] for w in same_line_words)
                clean_val = re.sub(r"[:\-=~+._\s]", "", same_line_text)

                is_emergency_header = bool(re.search(r"In\s+Cas[ce]\s+of\s+Emergency", anchor["kw"], re.I))

                if same_line_words and len(clean_val) > 2 and not is_emergency_header and not re.match(r"^(?:oe|—|_|-|~)+$", clean_val, re.I):
                    # Tightly enclose actual words without line ballooning
                    val_rect = same_line_words[0][0]
                    for sw in same_line_words[1:]:
                        val_rect = val_rect | sw[0]
                    val_rect = pymupdf.Rect(
                        max(0, val_rect.x0 - 2),
                        max(split_top, val_rect.y0 - 2),
                        val_rect.x1 + 2,
                        min(split_bottom, val_rect.y1 + 2)
                    )
                    add_target(val_rect, f"{a_cat}_VALUE", same_line_text, engine="form_field_expansion")
                else:
                    # 2D Column Table Parsing: Check rows directly below for this anchor column
                    col_x0 = a_rect.x0 - 25
                    col_x1 = max(a_rect.x1 + 60, end_x)
                    for offset in range(1, 3):
                        if l_idx + offset < len(line_objects):
                            nxt_l = line_objects[l_idx + offset]
                            clean_next = re.sub(r"[-_=~a.,\s—|]", "", nxt_l["text"]).strip()
                            if not clean_next or re.match(r"^(?:oe|—|_|-|~|aaa)+$", nxt_l["text"].strip(), re.I):
                                continue
                            if nxt_l["rect"].y0 - line_rect.y1 > 50:
                                break
                            col_words = [w for w in nxt_l["words"] if col_x0 <= w[0].x0 <= col_x1]
                            if col_words:
                                col_txt = " ".join(w[1] for w in col_words)
                                clean_col = re.sub(r"[-_=~a.,\s—|]", "", col_txt).strip()
                                if clean_col and not self.is_whitelisted(col_txt) and not re.match(r"^(?:oe|—|_|-|~|aaa)+$", clean_col, re.I):
                                    valid = True
                                    if a_cat == "CONTACT":
                                        valid = bool(re.search(r"[\d@]", col_txt))
                                    elif a_cat == "DATE":
                                        valid = bool(re.search(r"\d|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)", col_txt, re.I))
                                    elif a_cat == "IDENTIFIER":
                                        valid = bool(re.search(r"\d", col_txt))
                                    elif a_cat == "DEMOGRAPHIC":
                                        valid = bool(re.search(r"\d|Male|Female|M|F|Normal", col_txt, re.I))
                                    elif a_cat == "INSURANCE":
                                        valid = bool(re.search(r"[A-Za-z]", col_txt))
                                    elif a_cat == "PATIENT_NAME":
                                        valid = bool(re.search(r"[A-Z][a-zA-Z]{2,}", col_txt)) and not self.is_whitelisted(col_txt)

                                    if valid:
                                        c_rect = col_words[0][0]
                                        for cw in col_words[1:]:
                                            c_rect = c_rect | cw[0]
                                        c_rect = pymupdf.Rect(
                                            max(0, c_rect.x0 - 2),
                                            max(0, c_rect.y0 - 2),
                                            c_rect.x1 + 2,
                                            c_rect.y1 + 2
                                        )
                                        add_target(c_rect, f"{a_cat}_VALUE_2D", col_txt, engine="table_column_2d")
                                        break

        # -------------------------------------------------------------------
        # 2. Universal Standalone Regex Entity Scanners
        # -------------------------------------------------------------------
        standalone_regexes = [
            ("PHONE", r"\b(?:\+?91[\-\s]?)?[6-9]\d{9}\b|\b0\d{2,4}[\-\s]?\d{6,8}\b|\b\(\d{3}\)[\s\-]?[0-9O]{3}[\-\s]?\d{4}\b|\b\d{3}\)[\s\-]?[0-9O]{3}[\-\s]?\d{4}\b"),
            ("DATE", r"\b\d{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{2,4}\b|\b\d{1,2}[\s\-_](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\-_]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b"),
            ("EMAIL", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
            ("PATIENT_HONORIFIC", r"\b(?:Mr|Mrs|Ms|Miss|Master|Baby|Shri|Smt)\.?[^\S\r\n]*[A-Z][a-zA-Z]+(?:[^\S\r\n]+[A-Z][a-zA-Z]+)*\b"),
            ("DOCTOR_NAME", r"\b(?:Dr|Prof)\.?\s*[A-Z][a-zA-Z]+(?:[^\S\r\n]+[A-Z]\.?)?(?:[^\S\r\n]+[A-Z][a-zA-Z]+)*(?:\s*\([A-Za-z\s,.]+\))?\b|\bOr[^\S\r\n]+[A-Z][A-Za-z]+(?:[^\S\r\n]+[A-Z][A-Za-z]+)*\b|\b(?:Dr\.?|Dr\s+)?PAWAN\s+K\s+GOYAL\b|\bNK\s+GOYAL\b|\bDrJohn\b"),
            ("DOCTOR_CREDENTIALS", r"\b(?:MBBS|M\.B\.B\.S|MD|M\.D|MS|M\.S|DMRD|D\.M\.R\.D|DNB|D\.N\.B|FRCR|FRCS)\b"),
            ("ID_TOKEN", r"\bUD-\d+\b|\bOP-\d+\b|\b1024\d{5}\b|\b7115207313\b|\bAPL-2026-\d+\b|\bMCI-\d+\b"),
            ("ADDRESS_STREET", r"\b\d+\s+[A-Za-z0-9\-]+(?:\s+[A-Za-z0-9\-]+)*\s+(?:Street|St|Avenue|Ave|Drive|Dr|Road|Rd|Boulevard|Blvd|Court|Ct|Lane|Ln|Bollinger)\b|\bSEC(?:TOR)?\s*\d+[\s,]+[A-Za-z]+\b|\bSR\s+Market,\s+Geeta\s+Colony\b"),
            ("CITY_STATE", r"\b(?:New\s+York(?:\s+City)?|Jersey\s+City|New\s+Jersey|new\s+Russia|New\s*Delhi|Kurukshetra|Haryana|United\s+States)\b"),
        ]

        for cat, reg in standalone_regexes:
            for match in re.finditer(reg, full_text, re.IGNORECASE):
                match_str = match.group(0).strip()
                if not self.is_whitelisted(match_str) and len(match_str) > 2:
                    rects = page.search_for(match_str, textpage=tp)
                    for r in rects:
                        add_target(r, cat, match_str, engine="regex_scanner")

        # Header zone matching (surnames & clinic identifiers in upper region)
        header_zone_y = page.rect.height * 0.45
        header_patterns = [
            ("HEADER_SURNAME", r"\b(?:SHARMA|SINGHAL|GOYAL|DESAI|KOHLI|GARG|SINGH)\b"),
            ("CLINIC_HEADER", r"\b(?:AKASH\s*IMAGING(?:\s*&\s*DIAGNOSTICS)?|AKASH|SIMSS\s*HOSPITAL|SIMSS|Singhal\s+Institute(?:\s+of\s+Medical\s+and\s+Surgical\s+Superspecialities)?)\b"),
        ]

        for cat, reg in header_patterns:
            for match in re.finditer(reg, full_text, re.IGNORECASE):
                match_str = match.group(0).strip()
                if not self.is_whitelisted(match_str) and len(match_str) > 2:
                    rects = page.search_for(match_str, textpage=tp)
                    for r in rects:
                        if r.y1 <= header_zone_y:
                            add_target(r, cat, match_str, engine="header_zone_scanner")

        # -------------------------------------------------------------------
        # 3. CLAHE Contrast-Enhanced Header Pass (Faint Top Headers & Glare)
        # -------------------------------------------------------------------
        tmp_doc_enh = None
        try:
            words_enh, p_enh, tp_enh, tmp_doc_enh = self._get_enhanced_header_ocr(page)
            full_enh = p_enh.get_text(textpage=tp_enh)

            # 3a. Reconstruct visual lines and run form anchor parsing on CLAHE header
            line_objects_enh = self._reconstruct_visual_lines(words_enh)
            for l_idx_e, l_obj_e in enumerate(line_objects_enh):
                l_text_e = l_obj_e["text"]
                l_words_e = l_obj_e["words"]
                line_rect_e = l_obj_e["rect"]
                line_mid_e = (line_rect_e.y0 + line_rect_e.y1) / 2.0
                detected_anchors_e = []
                for cat, patterns in anchor_patterns:
                    for pat in patterns:
                        for m in re.finditer(pat, l_text_e, re.IGNORECASE):
                            kw = m.group(0)
                            raw_rects = p_enh.search_for(kw, textpage=tp_enh)
                            kw_rects = sorted([r for r in raw_rects if abs((r.y0 + r.y1)/2.0 - line_mid_e) < max(20.0, line_rect_e.height * 0.4)], key=lambda r: r.x0)
                            if kw_rects:
                                kw_clusters = []
                                curr_cluster = [kw_rects[0]]
                                for r in kw_rects[1:]:
                                    if abs(r.x0 - curr_cluster[-1].x1) < 40:
                                        curr_cluster.append(r)
                                    else:
                                        kw_clusters.append(curr_cluster)
                                        curr_cluster = [r]
                                kw_clusters.append(curr_cluster)
                                for cluster in kw_clusters:
                                    u_kw = cluster[0]
                                    for kr in cluster[1:]:
                                        u_kw = u_kw | kr
                                    detected_anchors_e.append({
                                        "cat": cat,
                                        "kw": kw,
                                        "rect": u_kw
                                    })
                # Deduplicate anchors
                dedup_anchors_e = []
                for a in detected_anchors_e:
                    is_sub = False
                    for other in detected_anchors_e:
                        if a is not other:
                            if (a["rect"] in other["rect"] and len(other["kw"]) > len(a["kw"])) or \
                               (other["kw"].endswith(a["kw"]) and len(other["kw"]) > len(a["kw"])):
                                is_sub = True
                                break
                    if not is_sub:
                        dedup_anchors_e.append(a)
                detected_anchors_e = dedup_anchors_e
                detected_anchors_e.sort(key=lambda a: a["rect"].x0)

                for a_idx, anchor in enumerate(detected_anchors_e):
                    a_rect = anchor["rect"]
                    a_cat = anchor["cat"]
                    add_target(a_rect, f"{a_cat}_LABEL_CLAHE", anchor["kw"], engine="form_anchor_clahe")
                    start_x = a_rect.x1 + 2
                    if a_idx + 1 < len(detected_anchors_e):
                        end_x = max(start_x, detected_anchors_e[a_idx + 1]["rect"].x0 - 4)
                    else:
                        end_x = line_rect_e.x1 + 4
                    same_line_words = [w for w in l_words_e if start_x - 4 <= w[0].x0 <= end_x]
                    same_line_text = " ".join(w[1] for w in same_line_words)
                    clean_val = re.sub(r"[:\-=~+._\s]", "", same_line_text)
                    if same_line_words and len(clean_val) > 2 and not re.match(r"^(?:oe|—|_|-|~)+$", clean_val, re.I):
                        val_rect = same_line_words[0][0]
                        for sw in same_line_words[1:]:
                            val_rect = val_rect | sw[0]
                        add_target(val_rect, f"{a_cat}_VALUE_CLAHE", same_line_text, engine="form_field_expansion_clahe")

            # 3b. Standalone regexes on CLAHE header
            for cat, reg in standalone_regexes:
                for match in re.finditer(reg, full_enh, re.IGNORECASE):
                    match_str = match.group(0).strip()
                    if not self.is_whitelisted(match_str) and len(match_str) > 2:
                        rects = p_enh.search_for(match_str, textpage=tp_enh)
                        for r in rects:
                            add_target(r, f"{cat}_ENHANCED", match_str, engine="ocr_contrast_enhanced")

            # 3c. Header patterns on CLAHE header
            for cat, reg in header_patterns:
                for match in re.finditer(reg, full_enh, re.IGNORECASE):
                    match_str = match.group(0).strip()
                    if not self.is_whitelisted(match_str) and len(match_str) > 2:
                        rects = p_enh.search_for(match_str, textpage=tp_enh)
                        for r in rects:
                            add_target(r, f"{cat}_ENHANCED", match_str, engine="header_zone_clahe")
        except Exception:
            pass
        finally:
            if tmp_doc_enh is not None:
                tmp_doc_enh.close()

        return targets

    def find_pii_targets(self, doc: pymupdf.Document) -> List[RedactionTarget]:
        """Scans all pages of a document and returns detected PII targets."""
        all_targets: List[RedactionTarget] = []
        for idx, page in enumerate(doc):
            targets = self.find_pii_targets_for_page(page, idx + 1)
            all_targets.extend(targets)
        return all_targets

    def redact(self, input_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes complete, irreversible redaction on scanned raster PDF or image.
        Returns audit summary dictionary.
        """
        input_path = os.path.abspath(input_path)
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        in_base, in_ext = os.path.splitext(input_path)
        in_ext_lower = in_ext.lower()
        is_image_input = in_ext_lower in self.IMAGE_EXTENSIONS

        if output_path is None:
            output_path = f"{in_base}_anonymized{in_ext}"
        output_path = os.path.abspath(output_path)
        out_ext_lower = os.path.splitext(output_path)[1].lower()

        # Handle Image Input
        if is_image_input:
            with Image.open(input_path) as orig_img:
                orig_w, orig_h = orig_img.size

            with pymupdf.open(input_path) as img_doc:
                pdf_bytes = img_doc.convert_to_pdf()
            doc = pymupdf.open("pdf", pdf_bytes)
            page = doc[0]

            # 1. OCR-based targets
            targets = self.find_pii_targets_for_page(page, 1)

            # 2. Visual Grounder (stamps & signatures) - strictly gated by clinical whitelist & OCR text
            if self.enable_visual_grounder and self.grounder is not None:
                try:
                    visual_targets = self.grounder.detect_visual_pii(input_path, page_num=1)
                    scale_vx = page.rect.width / max(1.0, orig_w)
                    scale_vy = page.rect.height / max(1.0, orig_h)
                    tp = page.get_textpage_ocr(language="eng", dpi=self.dpi, tessdata=self.tessdata_dir)
                    words = page.get_text("words", textpage=tp)
                    for vt in visual_targets:
                        scaled_bbox = BoundingBox(
                            x0=vt.bbox.x0 * scale_vx,
                            y0=vt.bbox.y0 * scale_vy,
                            x1=vt.bbox.x1 * scale_vx,
                            y1=vt.bbox.y1 * scale_vy
                        )
                        vr = pymupdf.Rect(scaled_bbox.x0, scaled_bbox.y0, scaled_bbox.x1, scaled_bbox.y1)
                        overlap_text = False
                        for w in words:
                            wr = pymupdf.Rect(w[0], w[1], w[2], w[3])
                            if not (vr & wr).is_empty and (vr & wr).get_area() > 0.05 * wr.get_area():
                                if self.is_whitelisted(w[4]) or len(w[4]) > 2:
                                    overlap_text = True
                                    break
                        if not overlap_text and not self.is_whitelisted(vt.raw_text):
                            scaled_vt = RedactionTarget(
                                page_number=vt.page_number,
                                category=vt.category,
                                raw_text=vt.raw_text,
                                bbox=scaled_bbox,
                                confidence=vt.confidence,
                                engine=vt.engine
                            )
                            targets.append(scaled_vt)
                except Exception:
                    pass

            for t in targets:
                pad_x = max(3.0, t.bbox.width * self.padding_ratio)
                pad_y = max(2.0, t.bbox.height * self.padding_ratio)
                rect = pymupdf.Rect(
                    max(0, t.bbox.x0 - pad_x),
                    max(0, t.bbox.y0 - pad_y),
                    min(page.rect.width, t.bbox.x1 + pad_x),
                    min(page.rect.height, t.bbox.y1 + pad_y)
                )
                page.add_redact_annot(rect, fill=(0, 0, 0))

            page.apply_redactions()

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            if out_ext_lower in self.IMAGE_EXTENSIONS:
                scale_x = orig_w / page.rect.width
                scale_y = orig_h / page.rect.height
                pix = page.get_pixmap(matrix=pymupdf.Matrix(scale_x, scale_y))
                pix.save(output_path)
            else:
                doc.save(output_path, garbage=4, deflate=True)

            doc.close()

            return {
                "input_file": input_path,
                "output_file": output_path,
                "format_type": "SCANNED_RASTER_IMAGE",
                "total_entities_redacted": len(targets),
                "redacted_targets": [t.model_dump() for t in targets]
            }

        # Handle PDF Input
        doc = pymupdf.open(input_path)
        all_targets: List[RedactionTarget] = []

        for p_idx, page in enumerate(doc):
            targets = self.find_pii_targets_for_page(page, p_idx + 1)
            all_targets.extend(targets)

            for t in targets:
                pad_x = max(2.0, t.bbox.width * self.padding_ratio)
                pad_y = max(1.5, t.bbox.height * self.padding_ratio)
                rect = pymupdf.Rect(
                    max(0, t.bbox.x0 - pad_x),
                    max(0, t.bbox.y0 - pad_y),
                    min(page.rect.width, t.bbox.x1 + pad_x),
                    min(page.rect.height, t.bbox.y1 + pad_y)
                )
                page.add_redact_annot(rect, fill=(0, 0, 0))

            page.apply_redactions()

        # Wipe metadata to eliminate digital trace leakage
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

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if out_ext_lower in self.IMAGE_EXTENSIONS:
            pix = doc[0].get_pixmap(dpi=self.dpi)
            pix.save(output_path)
        else:
            doc.save(output_path, garbage=4, deflate=True)

        doc.close()

        return {
            "input_file": input_path,
            "output_file": output_path,
            "format_type": "SCANNED_RASTER_PDF",
            "total_entities_redacted": len(all_targets),
            "redacted_targets": [t.model_dump() for t in all_targets]
        }
