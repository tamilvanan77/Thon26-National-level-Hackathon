import json
import os
import re
from urllib import error, request

from .ocr_engine import extract_text_from_image


LAB_PATTERNS = {
    "total_cholesterol": r"(?:total\s*cholesterol|cholesterol)\s*[:\-]?\s*(\d+(?:\.\d+)?)",
    "ldl": r"(?:ldl|low\s*density\s*lipoprotein)\s*[:\-]?\s*(\d+(?:\.\d+)?)",
    "hdl": r"(?:hdl|high\s*density\s*lipoprotein)\s*[:\-]?\s*(\d+(?:\.\d+)?)",
    "triglycerides": r"(?:triglycerides?)\s*[:\-]?\s*(\d+(?:\.\d+)?)",
    "glucose": r"(?:glucose|fbs|fasting\s*blood\s*sugar)\s*[:\-]?\s*(\d+(?:\.\d+)?)",
    "hba1c": r"(?:hba1c|a1c)\s*[:\-]?\s*(\d+(?:\.\d+)?)",
}

DOSE_PATTERN = r"(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu)"
FREQ_KEYWORDS = (
    "once daily",
    "twice daily",
    "thrice daily",
    "daily",
    "bid",
    "tid",
    "qhs",
    "od",
    "bd",
    "after food",
    "before food",
)

ALLOWED_LAB_KEYS = set(LAB_PATTERNS.keys())
ALLOWED_DOC_TYPES = {"prescription", "lab_report"}


def extract_text_from_document(file_path):
    ext = os.path.splitext(file_path.lower())[1]
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
        return extract_text_from_image(file_path).strip()
    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
            return file.read().strip()
    return ""


def _parse_lab_values(text):
    values = {}
    lowered = text.lower()
    for key, pattern in LAB_PATTERNS.items():
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            values[key] = float(match.group(1))
        except (TypeError, ValueError):
            continue
    return values


def _parse_medications(text):
    medications = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or len(line) < 3:
            continue
        line_lower = line.lower()

        dose = ""
        dose_match = re.search(DOSE_PATTERN, line_lower)
        if dose_match:
            dose = f"{dose_match.group(1)} {dose_match.group(2)}"

        frequency = ""
        for keyword in FREQ_KEYWORDS:
            if keyword in line_lower:
                frequency = keyword
                break

        name_match = re.match(r"([a-zA-Z][a-zA-Z0-9\-\s]{2,40})", line)
        if not name_match:
            continue
        name = name_match.group(1).strip(" -:")

        if any(token in line_lower for token in ("tab", "cap", "syrup", "mg", "ml", "od", "bd", "bid", "tid")):
            medications.append(
                {
                    "name": name,
                    "dosage": dose,
                    "frequency": frequency,
                    "source_line": line[:120],
                }
            )

    unique = []
    seen = set()
    for med in medications:
        key = med["name"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(med)
    return unique


def _rule_based_parse(text, doc_type):
    payload = {
        "doc_type": doc_type if doc_type in ALLOWED_DOC_TYPES else "lab_report",
        "medications": _parse_medications(text),
        "lab_values": _parse_lab_values(text),
        "clinical_notes": [],
    }

    if payload["medications"]:
        payload["clinical_notes"].append("Medication names, dosage, and frequency were parsed from document text.")
    if payload["lab_values"]:
        payload["clinical_notes"].append("Lab values were detected and digitized from report text.")
    if not payload["medications"] and not payload["lab_values"]:
        payload["clinical_notes"].append("Text extracted, but no structured medication/lab entities were identified.")

    return payload


def _extract_first_json(text):
    if not text:
        return None
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    match = re.search(r"\{[\s\S]*\}", stripped)
    return match.group(0) if match else None


def _sanitize_string(value, max_len=300):
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_len]


def _sanitize_medications(items):
    if not isinstance(items, list):
        return []

    cleaned = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        name = _sanitize_string(item.get("name"), max_len=120)
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        cleaned.append(
            {
                "name": name,
                "dosage": _sanitize_string(item.get("dosage"), max_len=50),
                "frequency": _sanitize_string(item.get("frequency"), max_len=60),
                "source_line": _sanitize_string(item.get("source_line"), max_len=120),
            }
        )
    return cleaned


def _sanitize_lab_values(values):
    if not isinstance(values, dict):
        return {}
    cleaned = {}
    for key, value in values.items():
        if key not in ALLOWED_LAB_KEYS:
            continue
        try:
            cleaned[key] = float(value)
        except (TypeError, ValueError):
            continue
    return cleaned


def _sanitize_notes(notes):
    if not isinstance(notes, list):
        return []
    output = []
    for note in notes:
        clean = _sanitize_string(note, max_len=220)
        if clean:
            output.append(clean)
    return output[:8]


def _normalize_payload(raw, doc_type):
    safe_doc_type = doc_type if doc_type in ALLOWED_DOC_TYPES else "lab_report"
    if not isinstance(raw, dict):
        return {
            "doc_type": safe_doc_type,
            "medications": [],
            "lab_values": {},
            "clinical_notes": [],
        }

    normalized = {
        "doc_type": safe_doc_type,
        "medications": _sanitize_medications(raw.get("medications")),
        "lab_values": _sanitize_lab_values(raw.get("lab_values")),
        "clinical_notes": _sanitize_notes(raw.get("clinical_notes")),
    }

    if not normalized["clinical_notes"]:
        normalized["clinical_notes"].append("AI parser completed structured extraction.")
    return normalized


def _merge_payloads(primary, secondary):
    merged = {
        "doc_type": primary.get("doc_type") or secondary.get("doc_type") or "lab_report",
        "medications": [],
        "lab_values": {},
        "clinical_notes": [],
    }

    med_map = {}
    for payload in (primary, secondary):
        for med in payload.get("medications", []):
            if not isinstance(med, dict):
                continue
            name = _sanitize_string(med.get("name"), max_len=120)
            if not name:
                continue
            key = name.lower()
            if key not in med_map:
                med_map[key] = {
                    "name": name,
                    "dosage": _sanitize_string(med.get("dosage"), max_len=50),
                    "frequency": _sanitize_string(med.get("frequency"), max_len=60),
                    "source_line": _sanitize_string(med.get("source_line"), max_len=120),
                }
    merged["medications"] = list(med_map.values())

    for payload in (secondary, primary):
        for key, value in payload.get("lab_values", {}).items():
            if key in ALLOWED_LAB_KEYS:
                merged["lab_values"][key] = value

    notes = []
    for payload in (primary, secondary):
        notes.extend(_sanitize_notes(payload.get("clinical_notes")))
    merged["clinical_notes"] = list(dict.fromkeys(notes))[:10]

    return merged


def _analyze_with_openai(text, doc_type):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or os.environ.get("DOC_AI_USE_LLM", "1") != "1":
        return None

    model = os.environ.get("OPENAI_DOC_AI_MODEL", os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini"))
    clipped_text = text[:12000]

    prompt = (
        "Extract structured medical entities from this OCR text. "
        "Return only JSON with keys: medications, lab_values, clinical_notes. "
        "medications is an array of objects with keys: name, dosage, frequency, source_line. "
        "lab_values must only include these keys when present: total_cholesterol, ldl, hdl, triglycerides, glucose, hba1c. "
        "clinical_notes should be concise extraction notes, not diagnosis."
    )

    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a medical document structuring engine. "
                    "Provide extraction only. Never provide diagnosis or treatment decisions."
                ),
            },
            {"role": "system", "content": f"Document type: {doc_type}"},
            {"role": "user", "content": f"{prompt}\n\nOCR_TEXT:\n{clipped_text}"},
        ],
    }

    req = request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        parsed_text = _extract_first_json(content) or ""
        raw = json.loads(parsed_text) if parsed_text else None
    except (error.URLError, error.HTTPError, KeyError, IndexError, TimeoutError, json.JSONDecodeError):
        return None

    return _normalize_payload(raw, doc_type)


def parse_medical_document(text, doc_type):
    payload = {
        "doc_type": doc_type if doc_type in ALLOWED_DOC_TYPES else "lab_report",
        "medications": [],
        "lab_values": {},
        "clinical_notes": [],
    }

    if not text:
        payload["clinical_notes"].append("No machine-readable text extracted from the document.")
        return payload

    rule_payload = _rule_based_parse(text, doc_type)
    ai_payload = _analyze_with_openai(text, doc_type)

    if ai_payload:
        merged = _merge_payloads(ai_payload, rule_payload)
        merged["clinical_notes"].append("Document entities validated with AI-assisted parsing and rule fallback.")
        merged["clinical_notes"] = list(dict.fromkeys(_sanitize_notes(merged["clinical_notes"])))
        return merged

    rule_payload["clinical_notes"].append("AI parser unavailable; using deterministic local extraction.")
    rule_payload["clinical_notes"] = list(dict.fromkeys(_sanitize_notes(rule_payload["clinical_notes"])))
    return rule_payload


def process_uploaded_document(document):
    extracted_text = extract_text_from_document(document.file.path)
    parsed_data = parse_medical_document(extracted_text, document.doc_type)

    if extracted_text:
        verification_status = "parsed"
    else:
        verification_status = "pending"

    return {
        "extracted_text": extracted_text,
        "parsed_data": parsed_data,
        "verification_status": verification_status,
    }
