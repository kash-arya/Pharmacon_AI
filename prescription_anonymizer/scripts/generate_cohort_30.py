"""
30-Document Diverse Medical Prescription Cohort Generator.

Generates a rigorous, diverse benchmark cohort of 30 medical documents:
- Category A (1-8): Clean Digital Vector EMR Prescriptions (Apollo, Max, NHS, Epic format)
- Category B (9-14): Dense Multi-Column Tabular Grids (Testing Tabular Bleed / Adjacent Cell Over-masking)
- Category C (15-20): Real Scanned & Inpatient Admission/Discharge Summaries
- Category D (21-25): Rubber Stamp & Doctor Signature Authorized Prescriptions
- Category E (26-30): Optical Stress Tests (Tilted, low-contrast, noisy camera artifacts)

Each case comes with exact ground-truth PII strings and ground-truth clinical entities
to enable rigorous mathematical evaluation of PII Recall and Tabular Bleed Rate.
"""

from typing import List, Dict, Any, Tuple
import os
import json
import pymupdf
import cv2
import numpy as np


COHORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cohort_30")
os.makedirs(COHORT_DIR, exist_ok=True)


def create_vector_prescription(
    path: str,
    hospital: str,
    doctor: str,
    reg_no: str,
    phone: str,
    email: str,
    patient: str,
    age_sex: str,
    uhid: str,
    date: str,
    diagnosis: str,
    medicines: List[Tuple[str, str]],
    is_tabular: bool = False
):
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)

    # Header
    page.insert_text((50, 50), hospital.upper(), fontsize=13, fontname="helv", color=(0.1, 0.1, 0.5))
    page.insert_text((50, 70), f"{doctor}, Reg No: {reg_no}", fontsize=9, fontname="helv")
    page.insert_text((50, 85), f"Phone: {phone} | Email: {email}", fontsize=8, fontname="helv")

    if is_tabular:
        # Multi-column grid: [ Name | Age/Sex | UHID ] on Row 1, [ Date | Diagnosis | Phone ] on Row 2
        y0 = 110
        # Outer table border
        page.draw_rect(pymupdf.Rect(45, y0, 550, y0 + 55), color=(0.7, 0.7, 0.7), width=1)
        # Vertical dividers
        page.draw_line(pymupdf.Point(210, y0), pymupdf.Point(210, y0 + 55), color=(0.7, 0.7, 0.7), width=1)
        page.draw_line(pymupdf.Point(380, y0), pymupdf.Point(380, y0 + 55), color=(0.7, 0.7, 0.7), width=1)
        page.draw_line(pymupdf.Point(45, y0 + 27), pymupdf.Point(550, y0 + 27), color=(0.7, 0.7, 0.7), width=1)

        # Row 1 cells
        page.insert_text((50, y0 + 18), f"Name: {patient}", fontsize=9, fontname="helv")
        page.insert_text((215, y0 + 18), f"Age/Sex: {age_sex}", fontsize=9, fontname="helv")
        page.insert_text((385, y0 + 18), f"UHID: {uhid}", fontsize=9, fontname="helv")

        # Row 2 cells (Notice Diagnosis is in adjacent cell!)
        page.insert_text((50, y0 + 45), f"Date: {date}", fontsize=9, fontname="helv")
        page.insert_text((215, y0 + 45), f"Diagnosis: {diagnosis}", fontsize=9, fontname="helv")
        page.insert_text((385, y0 + 45), f"Phone: {phone}", fontsize=9, fontname="helv")
        med_y0 = y0 + 90
    else:
        # Boxed header
        page.draw_rect(pymupdf.Rect(45, 105, 550, 165), color=(0.8, 0.8, 0.8), width=1)
        page.insert_text((55, 125), f"Patient Name: {patient}", fontsize=10, fontname="helv")
        page.insert_text((250, 125), f"Age/Sex: {age_sex}", fontsize=10, fontname="helv")
        page.insert_text((420, 125), f"Date: {date}", fontsize=10, fontname="helv")
        page.insert_text((55, 145), f"UHID: {uhid}", fontsize=10, fontname="helv")
        page.insert_text((250, 145), f"Phone: {phone}", fontsize=10, fontname="helv")
        page.insert_text((50, 195), f"Clinical Diagnosis: {diagnosis}", fontsize=10, fontname="helv")
        med_y0 = 225

    page.insert_text((50, med_y0), "Rx (Prescribed Medicines):", fontsize=11, fontname="helv", color=(0, 0, 0))
    for i, (drug, instr) in enumerate(medicines):
        page.insert_text((65, med_y0 + 25 + (i * 26)), f"{i+1}. {drug} - {instr}", fontsize=9, fontname="helv")

    doc.save(path)
    doc.close()


def generate_all_30_documents() -> List[Dict[str, Any]]:
    """Builds and returns the full 30-case dataset metadata catalog."""
    catalog = []

    # Common medicines pool for realistic prescriptions
    med_pool = [
        ("Tab. Metformin 500 mg", "1 tablet BD with meals for 30 days"),
        ("Tab. Atorvastatin 20 mg", "1 tablet HS at bedtime for 30 days"),
        ("Tab. Pantoprazole 40 mg", "1 tablet OD empty stomach before breakfast for 14 days"),
        ("Tab. Amoxicillin 500 mg", "1 capsule TDS after meals for 5 days"),
        ("Tab. Cetirizine 10 mg", "1 tablet HS for 5 days as needed for allergy"),
        ("Syp. Paracetamol 250 mg/5 mL", "5 mL TDS for 3 days SOS for fever"),
        ("Inhaler Budesonide 200 mcg", "2 puffs BD; rinse mouth after use"),
        ("Tab. Clopidogrel 75 mg", "1 tablet OD after lunch for 30 days")
    ]

    hospitals = [
        "Apollo Multispeciality Hospitals", "Fortis Healthcare Network", "Max Super Speciality Hospital",
        "AIIMS New Delhi - Outpatient Clinic", "Manipal Hospital Bangalore", "Medanta The Medicity",
        "Narayana Institute of Cardiac Sciences", "Tata Memorial Centre Oncology"
    ]

    patients = [
        ("Ramesh Kumar Verma", "54 Y / Male", "UHID-APL-90412", "+91 98101 23450", "Type-2 Diabetes"),
        ("Sunita Devi Sharma", "48 Y / Female", "UHID-FOR-11823", "+91 98202 34561", "Hypertension Stage 2"),
        ("Mohammed Farooq", "36 Y / Male", "UHID-MAX-45910", "+91 98303 45672", "Acute Bronchitis"),
        ("Pooja Chandrasekhar", "29 Y / Female", "UHID-AIM-77312", "+91 98404 56783", "Allergic Rhinitis"),
        ("Gurpreet Singh Anand", "62 Y / Male", "UHID-MAN-66291", "+91 98505 67894", "Coronary Artery Disease"),
        ("Ananya Sengupta", "22 Y / Female", "UHID-MED-33108", "+91 98606 78905", "Gastroesophageal Reflux"),
        ("Vikramaditya Rathore", "41 Y / Male", "UHID-NAR-88204", "+91 98707 89016", "Hyperlipidemia"),
        ("Deepika Sundaram", "33 Y / Female", "UHID-TAT-99411", "+91 98808 90127", "Post-op Followup")
    ]

    doctors = [
        ("Dr. Arvind Swaminathan, MD", "MCI-44102", "dr.arvind@apollo.com"),
        ("Dr. Priya Venkatesh, MBBS, DNB", "DMC-88231", "priya.v@fortis.org"),
        ("Dr. Sanjay K. Banerjee, MD, DM", "KMC-99410", "sanjay.b@maxhealthcare.com"),
        ("Dr. Neha Kapoor, MD", "MCI-12094", "neha.kapoor@aiims.edu")
    ]

    # --- CATEGORY A: Clean Digital Vector Prescriptions (Docs 1-8) ---
    for i in range(8):
        doc_id = f"case_{i+1:02d}_vector_clean"
        p_name, age_sex, uhid, phone, diag = patients[i]
        doc_name, reg_no, email = doctors[i % len(doctors)]
        hosp = hospitals[i]
        date = f"{10+i}/10/2026"
        meds = med_pool[i % len(med_pool): (i % len(med_pool)) + 3]
        filename = f"{doc_id}.pdf"
        file_path = os.path.join(COHORT_DIR, filename)

        create_vector_prescription(
            file_path, hosp, doc_name, reg_no, phone, email,
            p_name, age_sex, uhid, date, diag, meds, is_tabular=False
        )

        catalog.append({
            "id": doc_id,
            "filename": filename,
            "category": "VECTOR_CLEAN",
            "format": "VECTOR_DIGITAL",
            "path": file_path,
            "ground_truth_pii": [p_name, uhid, phone, email, doc_name, reg_no, date],
            "ground_truth_clinical": [m[0] for m in meds] + [diag],
            "is_tabular": False
        })

    # --- CATEGORY B: Multi-Column Tabular Grid Prescriptions (Docs 9-16) ---
    # Specifically tests Tabular Bleed where Name is in the cell adjacent to Diagnosis
    for i in range(8):
        doc_id = f"case_{i+9:02d}_tabular_grid"
        p_name, age_sex, uhid, phone, diag = patients[i]
        doc_name, reg_no, email = doctors[(i+1) % len(doctors)]
        hosp = hospitals[(i+2) % len(hospitals)]
        date = f"{12+i}/10/2026"
        meds = med_pool[i % len(med_pool): (i % len(med_pool)) + 3]
        filename = f"{doc_id}.pdf"
        file_path = os.path.join(COHORT_DIR, filename)

        create_vector_prescription(
            file_path, hosp, doc_name, reg_no, phone, email,
            p_name, age_sex, uhid, date, diag, meds, is_tabular=True
        )

        catalog.append({
            "id": doc_id,
            "filename": filename,
            "category": "TABULAR_GRID",
            "format": "VECTOR_DIGITAL",
            "path": file_path,
            "ground_truth_pii": [p_name, uhid, phone, email, doc_name, reg_no, date],
            "ground_truth_clinical": [m[0] for m in meds] + [diag],
            "is_tabular": True
        })

    # --- CATEGORY C: Scanned Real Outpatient Slips (Docs 17-22) ---
    real_sample_sources = [
        ("sample_prescription_1.pdf", ["Dr John Smith", "Maria Sharapova", "9 tennis court", "5/11/2022", "(000)-111-2222"], ["Prednisone", "Lialda"]),
        ("sample_prescription_2.pdf", ["Dr John Smith", "Virat Kohli", "2 cricket blvd", "2/05/2022", "(000)-111-2222"], ["Omeprazole"]),
        ("sample_patient_details_1.pdf", ["Kathy Crawford", "May 6 1972", "9264 Ash Dr", "(737) 988-0851"], ["Varicella", "Migraine"])
    ]
    for idx, (src_name, pii_list, clin_list) in enumerate(real_sample_sources):
        src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "samples", src_name)
        if os.path.exists(src_path):
            doc_id = f"case_{idx+17:02d}_scanned_real"
            dest_name = f"{doc_id}.pdf"
            dest_path = os.path.join(COHORT_DIR, dest_name)
            # Copy file
            with open(src_path, "rb") as sf, open(dest_path, "wb") as df:
                df.write(sf.read())

            catalog.append({
                "id": doc_id,
                "filename": dest_name,
                "category": "SCANNED_REAL",
                "format": "SCANNED_RASTER",
                "path": dest_path,
                "ground_truth_pii": pii_list,
                "ground_truth_clinical": clin_list,
                "is_tabular": False
            })

    # Add image versions of scanned prescriptions
    img_src = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "samples", "extracted_images", "sample_prescription_1_p1.png")
    if os.path.exists(img_src):
        doc_id = "case_20_scanned_img_png"
        dest_name = f"{doc_id}.png"
        dest_path = os.path.join(COHORT_DIR, dest_name)
        with open(img_src, "rb") as sf, open(dest_path, "wb") as df:
            df.write(sf.read())
        catalog.append({
            "id": doc_id,
            "filename": dest_name,
            "category": "SCANNED_IMAGE",
            "format": "SCANNED_RASTER",
            "path": dest_path,
            "ground_truth_pii": ["Dr John Smith", "Maria Sharapova", "9 tennis court", "5/11/2022"],
            "ground_truth_clinical": ["Prednisone", "Lialda"],
            "is_tabular": False
        })

    # --- CATEGORY D: Clinic Rubber Stamp & Signature Prescriptions (Docs 21-25) ---
    # Render PDF pages to images and artificially stamp colored ink seals & signatures
    for idx in range(5):
        doc_id = f"case_{idx+21:02d}_stamp_signature"
        # Render a clean vector PDF to image
        base_pdf = os.path.join(COHORT_DIR, f"case_{idx+1:02d}_vector_clean.pdf")
        doc = pymupdf.open(base_pdf)
        pix = doc[0].get_pixmap(dpi=150)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR if pix.n == 4 else cv2.COLOR_RGB2BGR)

        # 1. Draw circular blue clinic rubber stamp at (w-200, 180)
        center = (img_bgr.shape[1] - 140, 120)
        cv2.circle(img_bgr, center, 45, (160, 40, 30), 3) # Blue-purple BGR
        cv2.putText(img_bgr, "VERIFIED", (center[0]-35, center[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 40, 30), 1)
        cv2.putText(img_bgr, "CLINIC SEAL", (center[0]-40, center[1]+15), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (160, 40, 30), 1)

        # 2. Draw cursive doctor signature flourish at bottom-right (w-220, h-120)
        sig_x, sig_y = img_bgr.shape[1] - 220, img_bgr.shape[0] - 120
        pts = np.array([[sig_x, sig_y], [sig_x+40, sig_y-25], [sig_x+80, sig_y+15],
                        [sig_x+120, sig_y-30], [sig_x+180, sig_y+5]], np.int32)
        cv2.polylines(img_bgr, [pts], isClosed=False, color=(140, 30, 20), thickness=2)
        cv2.putText(img_bgr, "Dr. Signed", (sig_x+20, sig_y+25), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 0.6, (140, 30, 20), 1)

        dest_name = f"{doc_id}.png"
        dest_path = os.path.join(COHORT_DIR, dest_name)
        cv2.imwrite(dest_path, img_bgr)
        doc.close()

        catalog.append({
            "id": doc_id,
            "filename": dest_name,
            "category": "STAMP_SIGNATURE",
            "format": "SCANNED_RASTER",
            "path": dest_path,
            "ground_truth_pii": [patients[idx][0], patients[idx][2], patients[idx][3], "Dr. Signed", "CLINIC SEAL"],
            "ground_truth_clinical": [patients[idx][4]],
            "is_tabular": False
        })

    # --- CATEGORY E: Optical Stress Tests (Docs 26-30: Rotated, Low Contrast, Noisy) ---
    distortions = ["skew_rotated", "low_contrast", "gaussian_noise", "phone_shadow", "faded_thermal"]
    for idx, dist in enumerate(distortions):
        doc_id = f"case_{idx+26:02d}_{dist}"
        base_img_path = os.path.join(COHORT_DIR, f"case_{idx+21:02d}_stamp_signature.png")
        img = cv2.imread(base_img_path)
        h, w, _ = img.shape

        if dist == "skew_rotated":
            # Rotate image by 4.5 degrees
            M = cv2.getRotationMatrix2D((w//2, h//2), 4.5, 1.0)
            img = cv2.warpAffine(img, M, (w, h), borderValue=(255, 255, 255))
        elif dist == "low_contrast":
            # Simulate low-contrast thermal/carbon copy
            img = cv2.convertScaleAbs(img, alpha=0.55, beta=90)
        elif dist == "gaussian_noise":
            noise = np.random.normal(0, 15, img.shape).astype(np.uint8)
            img = cv2.add(img, noise)
        elif dist == "phone_shadow":
            # Gradient shadow across page
            shadow = np.tile(np.linspace(1.0, 0.50, h)[:, None, None], (1, w, 3))
            img = (img * shadow).astype(np.uint8)
        elif dist == "faded_thermal":
            img = cv2.GaussianBlur(img, (3, 3), 0)
            img = cv2.convertScaleAbs(img, alpha=0.70, beta=60)

        dest_name = f"{doc_id}.png"
        dest_path = os.path.join(COHORT_DIR, dest_name)
        cv2.imwrite(dest_path, img)

        catalog.append({
            "id": doc_id,
            "filename": dest_name,
            "category": "OPTICAL_STRESS",
            "format": "SCANNED_RASTER",
            "path": dest_path,
            "ground_truth_pii": [patients[idx][0], patients[idx][2], patients[idx][3]],
            "ground_truth_clinical": [patients[idx][4]],
            "distortion": dist,
            "is_tabular": False
        })

    # Save metadata catalog
    catalog_path = os.path.join(COHORT_DIR, "cohort_catalog.json")
    with open(catalog_path, "w") as f:
        json.dump(catalog, f, indent=2)

    return catalog


if __name__ == "__main__":
    cat = generate_all_30_documents()
    print(f"Generated {len(cat)} diverse prescription documents into {COHORT_DIR}")
    for c in cat:
        print(f"  [{c['category']:<15}] {c['filename']:<32} (format: {c['format']})")
