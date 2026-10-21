"""
Multi-National Healthcare Benchmark Cohort Generator.

Generates 5 layout-accurate statutory PDF benchmark specimens covering:
1. US (HIPAA California Security Rx Pad: DEA, NPI, DAW, SSN, street address)
2. UK (NHS Primary Care FP10: NHS Number, GMC Number, Surgery Address, Counter-signature)
3. Australia (PBS / Medicare Form: Medicare No, PBS Prescriber No, AHPRA No)
4. EU / Germany (Muster 16 Rosa Rezept: Versicherten-Nr, BSNR, LANR, Krankenkasse, Wohnanschrift)
5. India (DPDP Act Hospital OPD: ABHA ID, UHID, OPD No, NMC/MCI Registration)

Each document is synthesized with authentic regulatory statutory IDs and paired with ground-truth
PII and clinical pharmacology metadata catalogs for automated evaluation.
"""

import os
import json
from typing import List, Dict, Any, Tuple
import pymupdf

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "multinational_cohort")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_us_prescription(pdf_path: str) -> Dict[str, Any]:
    doc = pymupdf.open()
    page = doc.new_page(width=450, height=600)  # Standard US 5.5 x 7.5 prescription pad size

    # Header / Clinic
    page.draw_rect(pymupdf.Rect(20, 20, 430, 80), color=(0.2, 0.4, 0.6), fill=(0.95, 0.97, 1.0))
    page.insert_text((30, 40), "CEDARS-SINAI MEDICAL GROUP", fontsize=12, fontname="helv", color=(0.1, 0.2, 0.5))
    page.insert_text((30, 55), "Dr. Elizabeth Blackwell, M.D. - Internal Medicine", fontsize=9, fontname="helv")
    page.insert_text((30, 68), "8700 Beverly Blvd, Suite 210, Los Angeles, CA 90048 | Tel: (310) 423-5000", fontsize=8, fontname="helv")

    # Patient info box
    page.draw_rect(pymupdf.Rect(20, 90, 430, 160), color=(0.7, 0.7, 0.7))
    page.insert_text((30, 108), "PATIENT NAME: Jonathan Q. Public", fontsize=9, fontname="helv")
    page.insert_text((270, 108), "DOB: 04/12/1981", fontsize=9, fontname="helv")
    page.insert_text((30, 125), "ADDRESS: 742 Evergreen Terrace, Springfield, OR 97477", fontsize=8.5, fontname="helv")
    page.insert_text((30, 142), "DATE: 10/18/2026", fontsize=9, fontname="helv")
    page.insert_text((270, 142), "PHONE: (555) 839-2001", fontsize=8.5, fontname="helv")

    # Rx Body
    page.insert_text((30, 190), "Rx", fontsize=22, fontname="times-bold", color=(0.1, 0.2, 0.5))
    page.draw_line(pymupdf.Point(20, 200), pymupdf.Point(430, 200), color=(0.2, 0.4, 0.6), width=1)

    medications = [
        ("Lipitor (Atorvastatin) 20 mg tablet", "Sig: Take 1 tablet by mouth daily at bedtime. Dispense: #30"),
        ("Metformin HCl 500 mg oral tablet", "Sig: Take 1 tablet twice daily with meals. Dispense: #60"),
        ("Lisinopril 10 mg oral tablet", "Sig: Take 1 tablet daily in the morning for hypertension. Dispense: #30")
    ]

    y = 230
    for title, sig in medications:
        page.insert_text((40, y), title, fontsize=10, fontname="helv")
        page.insert_text((55, y + 15), sig, fontsize=8.5, fontname="helv")
        y += 45

    # DAW box
    page.draw_rect(pymupdf.Rect(30, 400, 150, 430), color=(0.6, 0.6, 0.6))
    page.insert_text((35, 418), "Dispense as Written (DAW: 1)", fontsize=8, fontname="helv")

    # Prescriber statutory identifiers & signature
    page.draw_line(pymupdf.Point(200, 430), pymupdf.Point(420, 430), color=(0.4, 0.4, 0.4), width=1)
    page.insert_text((210, 425), "Elizabeth Blackwell", fontsize=11, fontname="times-italic")
    page.insert_text((210, 442), "PRESCRIBER SIGNATURE", fontsize=7.5, fontname="helv")

    page.draw_rect(pymupdf.Rect(20, 460, 430, 520), color=(0.8, 0.8, 0.8), fill=(0.98, 0.98, 0.98))
    page.insert_text((30, 480), "DEA REG NO: AB1234567", fontsize=9, fontname="helv")
    page.insert_text((220, 480), "NPI: 1234567890", fontsize=9, fontname="helv")
    page.insert_text((30, 500), "CALIFORNIA LICENSE: C145892", fontsize=8.5, fontname="helv")
    page.insert_text((220, 500), "REFILLS: 3 (Three)", fontsize=8.5, fontname="helv")

    # Security pad footer notice
    page.insert_text((80, 550), "CALIFORNIA SECURITY PRESCRIPTION - VOID IF ALTERED", fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))

    doc.save(pdf_path)
    doc.close()

    return {
        "filename": os.path.basename(pdf_path),
        "jurisdiction": "US",
        "description": "US California Security Rx Pad (DEA, NPI, DAW, HIPAA Demographics)",
        "ground_truth_pii": [
            "Jonathan Q. Public",
            "04/12/1981",
            "742 Evergreen Terrace, Springfield, OR 97477",
            "(555) 839-2001",
            "Elizabeth Blackwell",
            "AB1234567",
            "1234567890",
            "C145892"
        ],
        "ground_truth_clinical": [
            "Lipitor",
            "Atorvastatin",
            "20 mg",
            "Metformin HCl",
            "500 mg",
            "Lisinopril",
            "10 mg",
            "Dispense as Written"
        ]
    }


def generate_uk_prescription(pdf_path: str) -> Dict[str, Any]:
    doc = pymupdf.open()
    page = doc.new_page(width=420, height=595)  # UK FP10 A5 aspect ratio

    # Header / NHS Watermark bar
    page.draw_rect(pymupdf.Rect(15, 15, 405, 55), color=(0.0, 0.4, 0.2), fill=(0.94, 0.98, 0.94))
    page.insert_text((25, 35), "NHS PRIMARY CARE FP10 PRESCRIPTION", fontsize=11, fontname="helv", color=(0.0, 0.4, 0.2))
    page.insert_text((25, 48), "National Health Service - England", fontsize=8, fontname="helv")

    # Patient & NHS Number Box
    page.draw_rect(pymupdf.Rect(15, 65, 405, 140), color=(0.6, 0.6, 0.6))
    page.insert_text((25, 82), "Patient Surname: PENDELTON", fontsize=8.5, fontname="helv")
    page.insert_text((200, 82), "Forename(s): Arthur", fontsize=8.5, fontname="helv")
    page.insert_text((25, 98), "Address: 12 Baker Street, London, NW1 6XE", fontsize=8.5, fontname="helv")
    page.insert_text((25, 114), "DOB: 14/05/1975", fontsize=8.5, fontname="helv")
    page.insert_text((150, 114), "Age: 51", fontsize=8.5, fontname="helv")
    page.insert_text((220, 114), "NHS NUMBER: 485 777 3456", fontsize=9, fontname="helv", color=(0.0, 0.2, 0.5))
    page.insert_text((25, 130), "Prescriber: Dr. Alastair Finch, GMC 6123456", fontsize=8.5, fontname="helv")

    # Rx Body
    page.draw_rect(pymupdf.Rect(15, 150, 405, 340), color=(0.8, 0.8, 0.8))
    page.insert_text((25, 170), "Prescription Items:", fontsize=9.5, fontname="helv", color=(0.1, 0.1, 0.1))

    items = [
        ("Amoxicillin 500mg capsules", "Take one capsule three times daily for 7 days (21 caps)"),
        ("Salbutamol 100micrograms/dose inhaler CFC-free", "Inhale 1 or 2 puffs when required for wheezing (1 inhaler)"),
        ("Paracetamol 500mg tablets", "Two tablets up to four times daily when needed for pain (32 tabs)")
    ]

    y = 195
    for drug, dose in items:
        page.insert_text((30, y), drug, fontsize=9.5, fontname="helv")
        page.insert_text((45, y + 14), dose, fontsize=8, fontname="helv")
        y += 40

    # Signature and Surgery stamps
    page.draw_line(pymupdf.Point(25, 390), pymupdf.Point(190, 390), color=(0.4, 0.4, 0.4))
    page.insert_text((35, 385), "Alastair Finch", fontsize=10, fontname="times-italic")
    page.insert_text((25, 402), "Doctor Signature & Stamp", fontsize=7.5, fontname="helv")

    page.draw_line(pymupdf.Point(220, 390), pymupdf.Point(395, 390), color=(0.4, 0.4, 0.4))
    page.insert_text((230, 385), "Registered Pharmacist", fontsize=9, fontname="times-italic")
    page.insert_text((220, 402), "Pharmacist Signature & Counter-sign", fontsize=7.5, fontname="helv")

    # Surgery Stamp Box
    page.draw_rect(pymupdf.Rect(15, 420, 405, 475), color=(0.7, 0.7, 0.7), fill=(0.98, 0.98, 0.98))
    page.insert_text((25, 438), "Surgery Address & Practice Stamp:", fontsize=8, fontname="helv")
    page.insert_text((25, 452), "St. Thomas Medical Practice, Lambeth Palace Rd, London SE1 7EH", fontsize=8, fontname="helv")
    page.insert_text((25, 465), "Tel: 020 7188 7188 | Practice Code: Y02845", fontsize=8, fontname="helv")

    # Footer
    page.insert_text((110, 520), "FOR NHS DISPENSING ONLY - FORM FP10-D", fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))

    doc.save(pdf_path)
    doc.close()

    return {
        "filename": os.path.basename(pdf_path),
        "jurisdiction": "UK",
        "description": "UK Primary Care FP10 (NHS Number, GMC Number, Surgery Address, Counter-sign)",
        "ground_truth_pii": [
            "PENDELTON",
            "Arthur",
            "12 Baker Street, London, NW1 6XE",
            "14/05/1975",
            "485 777 3456",
            "Alastair Finch",
            "6123456",
            "020 7188 7188"
        ],
        "ground_truth_clinical": [
            "Amoxicillin",
            "500mg",
            "Salbutamol",
            "100micrograms",
            "Paracetamol",
            "500mg"
        ]
    }


def generate_au_prescription(pdf_path: str) -> Dict[str, Any]:
    doc = pymupdf.open()
    page = doc.new_page(width=450, height=620)

    # Header / PBS bar
    page.draw_rect(pymupdf.Rect(20, 20, 430, 75), color=(0.1, 0.3, 0.1), fill=(0.95, 0.98, 0.95))
    page.insert_text((30, 42), "PHARMACEUTICAL BENEFITS SCHEME (PBS)", fontsize=11, fontname="helv", color=(0.1, 0.4, 0.2))
    page.insert_text((30, 58), "AUSTRALIAN GOVERNMENT DEPARTMENT OF HEALTH", fontsize=8, fontname="helv")

    # Patient & Medicare Details
    page.draw_rect(pymupdf.Rect(20, 85, 430, 160), color=(0.7, 0.7, 0.7))
    page.insert_text((30, 105), "PATIENT NAME: Lachlan Murdoch-Smith", fontsize=9, fontname="helv")
    page.insert_text((260, 105), "MEDICARE NO: 2345 67890 1", fontsize=9, fontname="helv", color=(0.1, 0.3, 0.1))
    page.insert_text((30, 122), "ADDRESS: 45 George Street, Sydney NSW 2000", fontsize=8.5, fontname="helv")
    page.insert_text((30, 139), "DATE: 20/10/2026", fontsize=9, fontname="helv")
    page.insert_text((180, 139), "ENTITLEMENT: General Beneficiary", fontsize=8.5, fontname="helv")
    page.insert_text((30, 154), "PHONE: (02) 9876 5432", fontsize=8, fontname="helv")

    # Rx Details
    page.draw_rect(pymupdf.Rect(20, 170, 430, 360), color=(0.8, 0.8, 0.8))
    page.insert_text((30, 192), "PBS PRESCRIPTION:", fontsize=10, fontname="helv", color=(0.1, 0.2, 0.1))

    drugs = [
        ("Atorvastatin 40 mg tablet", "One tablet daily in the evening. Quantity: 30 (1 repeat)"),
        ("Esomeprazole 20 mg tablet", "One tablet each morning before food. Quantity: 28 (5 repeats)"),
        ("Metoprolol Tartrate 50 mg tablet", "Half tablet twice daily with meals. Quantity: 100")
    ]

    y = 220
    for drug_name, dosage in drugs:
        page.insert_text((40, y), drug_name, fontsize=9.5, fontname="helv")
        page.insert_text((55, y + 15), dosage, fontsize=8.5, fontname="helv")
        y += 45

    # Prescriber info & AHPRA / PBS Prescriber Number
    page.draw_rect(pymupdf.Rect(20, 375, 430, 480), color=(0.7, 0.7, 0.7), fill=(0.98, 0.98, 0.98))
    page.insert_text((30, 395), "PRESCRIBER DETAILS:", fontsize=8.5, fontname="helv")
    page.insert_text((30, 412), "Dr. Bruce Campbell, MBBS FRACP", fontsize=9, fontname="helv")
    page.insert_text((30, 428), "PBS PRESCRIBER NO: 456789A", fontsize=9, fontname="helv", color=(0.1, 0.3, 0.1))
    page.insert_text((220, 428), "AHPRA REG: MED0001234567", fontsize=9, fontname="helv", color=(0.1, 0.3, 0.1))
    page.insert_text((30, 444), "Sydney Premier Clinic, 100 Macquarie St, Sydney NSW", fontsize=8, fontname="helv")

    page.draw_line(pymupdf.Point(230, 470), pymupdf.Point(410, 470), color=(0.4, 0.4, 0.4))
    page.insert_text((250, 465), "Bruce Campbell", fontsize=10, fontname="times-italic")
    page.insert_text((240, 478), "PRESCRIBER SIGNATURE", fontsize=7.5, fontname="helv")

    # PBS Watermark
    page.insert_text((130, 530), "AUSTRALIAN PBS PRESCRIPTION - VALID NATIONWIDE", fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))

    doc.save(pdf_path)
    doc.close()

    return {
        "filename": os.path.basename(pdf_path),
        "jurisdiction": "AU",
        "description": "Australian PBS Script (Medicare Card, PBS Prescriber No, AHPRA ID)",
        "ground_truth_pii": [
            "Lachlan Murdoch-Smith",
            "2345 67890 1",
            "45 George Street, Sydney NSW 2000",
            "(02) 9876 5432",
            "Bruce Campbell",
            "456789A",
            "MED0001234567"
        ],
        "ground_truth_clinical": [
            "Atorvastatin",
            "40 mg",
            "Esomeprazole",
            "20 mg",
            "Metoprolol Tartrate",
            "50 mg"
        ]
    }


def generate_eu_germany_prescription(pdf_path: str) -> Dict[str, Any]:
    doc = pymupdf.open()
    page = doc.new_page(width=500, height=350)  # German Muster 16 Rosa Rezept Landscape standard

    # Pink background bar characteristic of Muster 16 (Rosa Rezept)
    page.draw_rect(pymupdf.Rect(10, 10, 490, 340), color=(0.85, 0.4, 0.5), fill=(0.99, 0.96, 0.97))

    # Top Status Boxes
    page.draw_rect(pymupdf.Rect(20, 20, 260, 50), color=(0.8, 0.4, 0.5))
    page.insert_text((25, 33), "Krankenkasse bzw. Kostentrager:", fontsize=7, fontname="helv")
    page.insert_text((25, 45), "Techniker Krankenkasse (TK)", fontsize=8.5, fontname="helv")

    page.draw_rect(pymupdf.Rect(270, 20, 480, 50), color=(0.8, 0.4, 0.5))
    page.insert_text((275, 33), "Name, Vorname des Versicherten:", fontsize=7, fontname="helv")
    page.insert_text((275, 45), "von Schmidt, Maximilian", fontsize=9, fontname="helv")

    # Insurance Data Bar (Kostentrager-Nr, Versicherten-Nr, Status)
    page.draw_rect(pymupdf.Rect(20, 55, 480, 95), color=(0.8, 0.4, 0.5))
    page.insert_text((25, 67), "Kostentragerkennung", fontsize=6.5, fontname="helv")
    page.insert_text((25, 82), "108018007", fontsize=8.5, fontname="helv")

    page.insert_text((130, 67), "Versicherten-Nr.", fontsize=6.5, fontname="helv")
    page.insert_text((130, 82), "T123456789", fontsize=9, fontname="helv", color=(0.2, 0.2, 0.6))

    page.insert_text((240, 67), "Status", fontsize=6.5, fontname="helv")
    page.insert_text((240, 82), "10001", fontsize=8.5, fontname="helv")

    page.insert_text((300, 67), "Geb.-Jahr", fontsize=6.5, fontname="helv")
    page.insert_text((300, 82), "1968", fontsize=8.5, fontname="helv")

    page.insert_text((360, 67), "Ausstellungsdatum", fontsize=6.5, fontname="helv")
    page.insert_text((360, 82), "12.05.2024", fontsize=8.5, fontname="helv")

    # Patient Address Box
    page.insert_text((25, 110), "Wohnanschrift: Kurfürstendamm 102, 10711 Berlin", fontsize=8, fontname="helv")

    # Rp. Prescriptions Box
    page.draw_rect(pymupdf.Rect(20, 120, 330, 275), color=(0.8, 0.4, 0.5), fill=(1.0, 1.0, 1.0))
    page.insert_text((25, 140), "Rp. (Verordnungen):", fontsize=10, fontname="times-bold", color=(0.6, 0.1, 0.2))

    prescriptions = [
        ("1. Ramipril 5mg 1A Pharma 100 TAB N3", "1 x tgl. morgens 1 Tablette"),
        ("2. Pantoprazol TAD 20mg 56 TAB N2", "1 x tgl. vor dem Fruhstuck 1 Magenschutz"),
        ("3. Ibuprofen AL 400mg 50 Filmtabletten N2", "Bei Bedarf max. 3 x tgl. 1 Tablette")
    ]

    y = 165
    for med, instr in prescriptions:
        page.insert_text((30, y), med, fontsize=8.5, fontname="helv")
        page.insert_text((45, y + 13), instr, fontsize=7.5, fontname="helv")
        y += 35

    # Doctor practice stamp & statutory BSNR / LANR box
    page.draw_rect(pymupdf.Rect(340, 120, 480, 275), color=(0.8, 0.4, 0.5), fill=(1.0, 1.0, 1.0))
    page.insert_text((345, 135), "Vertragsarztstempel / Arztunterschrift:", fontsize=7, fontname="helv")
    page.insert_text((345, 155), "Praxis Dr. med. Klaus Becker", fontsize=8.5, fontname="helv")
    page.insert_text((345, 170), "Facharzt fur Allgemeinmedizin", fontsize=7.5, fontname="helv")
    page.insert_text((345, 185), "BSNR: 723456700", fontsize=8.5, fontname="helv", color=(0.2, 0.2, 0.6))
    page.insert_text((345, 200), "LANR: 987654321", fontsize=8.5, fontname="helv", color=(0.2, 0.2, 0.6))

    page.draw_line(pymupdf.Point(345, 245), pymupdf.Point(470, 245), color=(0.4, 0.4, 0.4))
    page.insert_text((360, 240), "Klaus Becker", fontsize=10, fontname="times-italic")
    page.insert_text((355, 255), "Unterschrift des Arztes", fontsize=7, fontname="helv")

    # Muster 16 label
    page.insert_text((20, 310), "Muster 16 (7.2020) Bundesmantelvertrag-Arzte (BMV-A)", fontsize=7, fontname="helv", color=(0.5, 0.5, 0.5))

    doc.save(pdf_path)
    doc.close()

    return {
        "filename": os.path.basename(pdf_path),
        "jurisdiction": "EU",
        "description": "German Statutory Muster 16 Rosa Rezept (BSNR, LANR, Versicherten-Nr, BMV-A)",
        "ground_truth_pii": [
            "Maximilian",
            "Kurfürstendamm 102, 10711 Berlin",
            "T123456789",
            "723456700",
            "987654321",
            "Klaus Becker"
        ],
        "ground_truth_clinical": [
            "Ramipril",
            "5mg",
            "Pantoprazol",
            "20mg",
            "Ibuprofen",
            "400mg"
        ]
    }


def generate_india_prescription(pdf_path: str) -> Dict[str, Any]:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)

    # Header / Hospital
    page.draw_rect(pymupdf.Rect(35, 30, 560, 95), color=(0.1, 0.2, 0.6), fill=(0.95, 0.97, 1.0))
    page.insert_text((45, 55), "APOLLO MULTISPECIALITY HOSPITALS", fontsize=14, fontname="helv", color=(0.1, 0.2, 0.6))
    page.insert_text((45, 72), "Dr. Ramesh Chandra, MBBS, MD (Cardiology) - Reg No: NMC-45892", fontsize=9, fontname="helv")
    page.insert_text((45, 87), "Sarita Vihar, Delhi Mathura Road, New Delhi 110076 | Phone: +91 98110 54321", fontsize=8, fontname="helv")

    # DPDP / Patient Demographics Box
    page.draw_rect(pymupdf.Rect(35, 105, 560, 185), color=(0.7, 0.7, 0.7))
    page.insert_text((45, 125), "PATIENT NAME: Aarav Sharma", fontsize=9.5, fontname="helv")
    page.insert_text((240, 125), "AGE/SEX: 48 Y / Male", fontsize=9.5, fontname="helv")
    page.insert_text((400, 125), "DATE: 20-Oct-2026", fontsize=9.5, fontname="helv")

    page.insert_text((45, 145), "UHID: AP2024-88912", fontsize=9, fontname="helv", color=(0.1, 0.2, 0.6))
    page.insert_text((240, 145), "OPD NO: OPD-4421", fontsize=9, fontname="helv")
    page.insert_text((400, 145), "ABHA ID: 91-4567-8912-3456", fontsize=9, fontname="helv", color=(0.1, 0.2, 0.6))

    page.insert_text((45, 165), "ADDRESS: Sector 4, Indirapuram, Ghaziabad, UP 201014", fontsize=8.5, fontname="helv")
    page.insert_text((400, 165), "MOBILE: +91 98765 43210", fontsize=8.5, fontname="helv")

    # Diagnosis & Rx
    page.insert_text((45, 215), "Clinical Impression: Primary Hypertension & Type 2 Diabetes Mellitus", fontsize=10, fontname="helv")
    page.insert_text((45, 240), "Rx (Medical Prescription):", fontsize=11, fontname="helv", color=(0.1, 0.2, 0.6))

    meds = [
        ("Tab. Telmisartan 40 mg", "1 tablet OD morning after breakfast for 30 days"),
        ("Tab. Glimepiride 1 mg", "1 tablet OD before breakfast for 30 days"),
        ("Tab. Metformin SR 500 mg", "1 tablet BD after lunch and dinner for 30 days"),
        ("Tab. Rosuvastatin 10 mg", "1 tablet HS at bedtime for 30 days")
    ]

    y = 270
    for med, instr in meds:
        page.insert_text((55, y), med, fontsize=9.5, fontname="helv")
        page.insert_text((70, y + 16), instr, fontsize=8.5, fontname="helv")
        y += 42

    # Signature and hospital seal
    page.draw_line(pymupdf.Point(380, 520), pymupdf.Point(540, 520), color=(0.4, 0.4, 0.4))
    page.insert_text((400, 515), "Ramesh Chandra", fontsize=11, fontname="times-italic")
    page.insert_text((400, 535), "Dr. Ramesh Chandra, MD", fontsize=8.5, fontname="helv")
    page.insert_text((400, 548), "Authorized Prescriber Signature", fontsize=7.5, fontname="helv")

    page.insert_text((45, 580), "DPDP ACT 2023 COMPLIANT EMR RECORD - CONFIDENTIAL", fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))

    doc.save(pdf_path)
    doc.close()

    return {
        "filename": os.path.basename(pdf_path),
        "jurisdiction": "IN",
        "description": "Indian DPDP Hospital OPD Slip (ABHA ID, UHID, OPD No, NMC Reg)",
        "ground_truth_pii": [
            "Aarav Sharma",
            "Sector 4, Indirapuram, Ghaziabad, UP 201014",
            "+91 98765 43210",
            "+91 98110 54321",
            "AP2024-88912",
            "OPD-4421",
            "91-4567-8912-3456",
            "Ramesh Chandra",
            "NMC-45892"
        ],
        "ground_truth_clinical": [
            "Telmisartan",
            "40 mg",
            "Glimepiride",
            "1 mg",
            "Metformin SR",
            "500 mg",
            "Rosuvastatin",
            "10 mg"
        ]
    }


def generate_cohort() -> List[Dict[str, Any]]:
    manifest = []
    
    specimens = [
        ("specimen_us_hipaa.pdf", generate_us_prescription),
        ("specimen_uk_nhs.pdf", generate_uk_prescription),
        ("specimen_au_pbs.pdf", generate_au_prescription),
        ("specimen_eu_germany.pdf", generate_eu_germany_prescription),
        ("specimen_in_dpdp.pdf", generate_india_prescription)
    ]

    for name, gen_fn in specimens:
        path = os.path.join(OUTPUT_DIR, name)
        metadata = gen_fn(path)
        metadata["full_path"] = path
        manifest.append(metadata)
        print(f"Generated: {name} ({metadata['jurisdiction']}) -> {path}")

    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nCohort generation complete. Manifest saved to: {manifest_path}")
    return manifest


if __name__ == "__main__":
    generate_cohort()
