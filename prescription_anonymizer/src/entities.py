"""
Core Entity Definitions and PII Anchor Lexicons for Medical Prescriptions.
"""

from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Normalized or pixel bounding box (x0, y0, x1, y1)."""
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)

    def expand(self, dx_ratio: float = 0.15, dy_ratio: float = 0.15) -> "BoundingBox":
        """Expand bounding box by given ratios for safety margin."""
        w = self.width
        h = self.height
        return BoundingBox(
            x0=max(0.0, self.x0 - w * dx_ratio),
            y0=max(0.0, self.y0 - h * dy_ratio),
            x1=self.x1 + w * dx_ratio,
            y1=self.y1 + h * dy_ratio,
        )


class RedactionTarget(BaseModel):
    """Identified PII entity with spatial coordinates on a specific page."""
    page_number: int
    category: str = Field(description="e.g. PATIENT_NAME, PHONE, UHID, DOCTOR_NAME, ADDRESS")
    raw_text: Optional[str] = None
    bbox: BoundingBox
    confidence: float = 1.0
    engine: str = Field(default="vector_rule", description="Detector engine: vector_rule, ocr_anchor, vlm")


# ---------------------------------------------------------------------------
# Multi-lingual & Standard Demographic Anchor Patterns
# ---------------------------------------------------------------------------

# Normalized Label Anchors for Form Key-Value Matching
KEY_VALUE_ANCHORS = {
    "PATIENT_NAME": [
        r"\bPatient\s+Information\b",
        r"\bPatient\s*Name\b",
        r"\bPt(?:\s*Name)?\b",
        r"\bPatient\s*[:\-=~+]",
        r"\b‘?Name\b(?!\s+(?:of\s+(?:Insurance|Company|Hospital|Clinic)))",
        r"\bIn\s+Cas[ce]\s+of\s+Emergency\b",
        r"\bEmergency\s+Contact\b",
    ],
    "IDENTIFIER": [
        r"\bUHID(?:\s*No\.?)?\b",
        r"\bOP(?:\s*No\.?)?\b",
        r"\bOPD(?:\s*No\.?)?\b(?!\s*(?:Timings|Hours))",
        r"\bIPD(?:\s*No\.?)?\b",
        r"\bIP(?:\s*No\.?)?\b",
        r"\bMRN\b",
        r"\bPatient\s*ID\b",
        r"\bReg(?:istration)?\.?\s*(?:No\.?)?\b",
        r"\bToken(?:\s*No\.?)?\b",
        r"\bPolicy\s*(?:No\.?|Number)?\b",
        r"\bBill\s*No\.?\b",
    ],
    "DEMOGRAPHIC": [
        r"\bAge(?:\s*/\s*Sex|\s*/\s*Gender)?\b",
        r"\bSex\b",
        r"\bGender\b",
        r"\bDOB\b",
        r"\bDate\s+of\s+Birth\b",
        r"\bPat\.?\s*Type\b",
    ],
    "CONTACT": [
        r"\bMobile(?:\s*No\.?)?\b",
        r"\bPhone(?:\s*No\.?)?\b",
        r"\bContact(?:\s*No\.?)?\b",
        r"\bHome\s+phone\b",
        r"\bWork\s+phone\b",
        r"\bTel(?:\s*No\.?)?\b",
        r"\bE-?mail\b",
    ],
    "DOCTOR_INFO": [
        r"\bConsultant\b",
        r"\bDoctor(?:\s+Name)?\b",
        r"\bRef(?:erred)?[.,]?\s*By\b",
        r"\bRadiologist\b",
        r"\bPhysician\b",
        r"\bSurgeon\b",
        r"\bTyped\s*By\b",
        r"\bCreated\s*By\b",
        r"\bPrinted\s*By\b",
    ],
    "ADDRESS": [
        r"\bAddress\b",
        r"\bAddr\b",
        r"\bCity\b",
        r"\bState\b",
        r"\bPin(?:\s*code)?\b",
    ],
    "DATE": [
        r"\bDate\b",
        r"\bOP\s*Date\b",
        r"\bReg\.?\s*Date\b",
        r"\bReport\s*Date(?:\s*/\s*Time)?\b",
        r"\bPrint\s*Date(?:\s*/\s*Time)?\b",
        r"\bCollected\s*Date(?:\s*/\s*Time)?\b",
        r"\bReceived\s*Date(?:\s*/\s*Time)?\b",
        r"\bVisit\s*Date\b",
        r"\bExpiry\s*Date\b",
        r"\bBirth\s*Date\b",
    ],
}

PATIENT_NAME_ANCHORS = [
    r"\bPatient\s+Name\s*[:\-=~+]",
    r"\bPt(?:\s+Name)?\s*[:\-=~+]",
    r"\b‘?Name\s*[:\-=~+]",
    r"\bPatient\s*[:\-=~+]",
    r"\b(?:Mr|Mrs|Ms|Miss|Master|Baby|Shri|Smt)\.?\s*[A-Za-z]+(?:\s+[A-Za-z]+)*",
]

DEMOGRAPHIC_ANCHORS = [
    r"\bAge(?:\s*/\s*Sex|\s*/\s*Gender)?\s*[:\-=~+]?\s*[\d\s]+(?:\s*(?:Y|Yrs|Years))?(?:\s*/\s*(?:Male|Female|M|F))?",
    r"\bSex\s*[:\-=~+]?\s*(?:Male|Female|M|F)\b",
    r"\bGender\s*[:\-=~+]?\s*(?:Male|Female|M|F)\b",
    r"\bDOB\s*[:\-=~+]?\s*[0-9\-/]+",
    r"\bDate(?:\s+of\s+Birth)?\s*[:\-=~+]?\s*[0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{2,4}",
    r"\b\d{1,3}\s*(?:Y|Yrs|Years)\s*/\s*(?:Male|Female|M|F)\b",
]

IDENTIFIER_ANCHORS = [
    r"\bUHID(?:\s*No\.?)?\s*[:\-=~+]?\s*[A-Za-z0-9\-/]+",
    r"\bOP(?:\s*No\.?)?\s*[:\-=~+]?\s*[A-Za-z0-9\-/]+",
    r"\bOPD\s*(?:No\.?)?\s*[:\-=~+]?\s*[A-Za-z0-9\-/]+(?!\s*(?:Timings|Hours))",
    r"\bIPD\s*(?:No\.?)?\s*[:\-=~+]?\s*[A-Za-z0-9\-/]+",
    r"\bMRN\s*[:\-=~+]?\s*[A-Za-z0-9\-/]+",
    r"\b(?:Reg\.?\s*No\.?|Registration\s*(?:No\.?)?)\s*[:\-=~+]?\s*[A-Za-z0-9\-/]+",
    r"\bPatient\s*ID\s*[:\-=~+]?\s*[A-Za-z0-9\-/]+",
    r"\bToken(?:\s*No\.?)?\s*[:\-=~+]?\s*[A-Za-z0-9\-.\s]+",
    r"\bPolicy\s*(?:No\.?|Number)?\s*[:\-=~+]?\s*[A-Za-z0-9\-/]+",
]

CONTACT_ANCHORS = [
    r"\b(?:Phone|Mobile|Contact|Tel)(?:\s*No\.?)?\s*[:\-=~+]?\s*\+?[0-9\s\-()]{7,16}",
    r"\b(?:\+?91[\-\s]?)?[6-9]\d{9}\b",
    r"\b0\d{2,4}[\-\s]?\d{6,8}\b",
    r"\b\(\d{3}\)[\s\-]?\d{3}[\-\s]?\d{4}\b",
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
]

DOCTOR_ANCHORS = [
    r"\b(?:Dr|Or|Prof)\.?\s+[A-Za-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Za-z]+)*(?:\s*\([A-Za-z\s,.]+\))?",
    r"\bConsultant\s*[:\-=~+]?\s*(?:Dr|Or)?\.?\s*[A-Za-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Za-z]+)*",
    r"\bRef(?:erred)?[.,]?\s*By\s*[:\-=~+]?\s*[A-Za-z0-9\s.]+",
    r"\bTyped\s*By\s*[:\-=~+]?\s*[A-Za-z0-9\s.]+",
    r"\bCreated\s*By\s*[:\-=~+]?\s*[A-Za-z0-9\s.]+",
    r"\bPrinted\s*By\s*[:\-=~+]?\s*[A-Za-z0-9\s.]+",
    r"\b(?:MBBS|M\.B\.B\.S|MD|M\.D|MS|M\.S|DMRD|D\.M\.R\.D|DNB|D\.N\.B|FRCR|FRCS)\b",
]

HEADER_SURNAMES = [
    "SHARMA", "SINGHAL", "GOYAL", "DESAI", "KOHLI", "GARG", "SINGH", "CRAWFORD", "SHARAPOVA"
]

CLINIC_HEADERS = [
    r"\bAKASH\s*IMAGING(?:\s*&\s*DIAGNOSTICS)?\b",
    r"\bAKASH\b",
    r"\bSIMSS\s*HOSPITAL\b",
    r"\bSIMSS\b",
    r"\bSinghal\s+Institute(?:\s+of\s+Medical\s+and\s+Surgical\s+Superspecialities)?\b",
]

ADDRESS_ANCHORS = [
    r"\b(?:Address|Addr)\s*[:\-=~+]?\s*.*",
    r"\b(?:SEC|Sector)\s*\d+[\s,]+[A-Za-z]+",
    r"\b\d+\s+[A-Za-z0-9\-]+(?:\s+[A-Za-z0-9\-]+)*\s+(?:Street|St|Avenue|Ave|Drive|Dr|Road|Rd|Boulevard|Blvd|Court|Ct|Lane|Ln|Bollinger|Colony|Market)\b",
    r"\b(?:New\s+York(?:\s+City)?|Jersey\s+City|New\s+Jersey|new\s+Russia|New\s*Delhi|Kurukshetra|Haryana|United\s+States)\b",
]

DATE_ANCHORS = [
    r"\b\d{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{2,4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:AM|PM))?)?",
    r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\-_]\d{2,4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:AM|PM))?)?",
    r"\b\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*-\d{2,4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:AM|PM))?)?",
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b",
]

CLINICAL_WHITELIST_PATTERNS = [
    # Pharmacology: active ingredients, dosage forms, routes, frequencies
    r"\b(?:Prednisone|Lialda|Omeprazole|Telmisartan|Amlodipine|Paracetamol|Triptans|Ibuprofen|Metformin|Amoxicillin|Azithromycin|Pantoprazole|Cefixime)\b",
    r"\b(?:mg|mcg|ml|gm|gram|tablet|tablets|capsule|capsules|syrup|suspension|drops|injection|ointment|gel|cream|patch)\b",
    r"\b(?:Refill|Refil|daily|once\s+daily|twice\s+daily|thrice\s+daily|SOS|stat|PRN|meals|breakfast|bedtime|hs|tid|bid|od|qid|three\s+months|for\s+three\s+months|tablets\s+daily)\b",
    r"\b(?:Rx|Prescription|Advice|Treatment|ADVICE\s*/\s*TREATMENT|Directions|Instructions|INVESTIGATIONS|General\s+Local/\s*Systemic\s+Examination)\b",
    # Clinical Departments & Hospital Specialties
    r"\b(?:Department|GENERAL\s+SURGERY|General\s+Surgery|Surgery|Internal\s+Medicine|Orthopedics|Radiology|Pediatrics|Cardiology)\b",
    # Clinical Diagnoses, Vitals & Findings
    r"\b(?:Chief\s+Complaints|DIAGNOSIS|Diagnosis|VITALS|Vitals|BP|Temp|sO2|SpO2|Pulse|Heart\s+Rate|Respiratory\s+Rate|Weight|Height|BMI)\b",
    r"\b(?:Hypertension|Essential\s+Hypertension|Blood\s+Pressure|Blood\s+Group|Diabetes|Fever|Cough|Pain|Headache|Migraine|Allergy|Allergies)\b",
    r"\b(?:Varicella|Chicken\s+Pox|Measles|IMMUNE|Hepatitis|Peanuts|Medical\s+Problems|General\s+Medical\s+History|Medical\s+History|medication\s+taken)\b",
    r"\b(?:Do\s+you\s+have\s+medical\s+insurance\?|Medical\s+Insurance\s+Details|Normal|mm\s+of\s+Hg|°F|%)\b",
    r"\b(?:Lifestyle\s+Modification|Dietary\s+Advice|disease\s+process|plan\s+of\s+care)\b",
    # Diagnostic Imaging / Ultrasound Anatomy & Findings
    r"\b(?:ULTRASOUND|WHOLE\s*ABDOMEN|HOLE\s*ABDOMEN|Ultrasound|Abdomen|USG|color\s+doppler|Samsung\s+RS80|transducer|cine\s+scans|elastography)\b",
    r"\b(?:Liver|Gall\s*bladder|CBD|Pancreas|Kidney|Right\s+kidney|Left\s+kidney|Prostate|Spleen|Urinary\s+bladder|Aorta|IVC|peritoneal\s+cavity|Appendix)\b",
    r"\b(?:echotexture|echogenecity|dilatation|calculus|calculi|hydronephrosis|focal\s+lesion|space-occupying\s+lesion|free\s+fluid|calyx|Calyx)\b",
    r"\b(?:normal\s+in\s+size|normal\s+in\s+course|distended|wall\s+thickness|upper\s+limit\s+normal|differentiation\s+is\s+maintained)\b",
    r"\b(?:lymph\s+node|enlarged|mass|portal\s+vein|peritoneal|parenchyma|cortico-medullary|corticomedullary|renal\s+non\s+obstructive\s+calculi)\b",
]


