from django.test import TestCase

from .ai_engine import analyze_clinical_data
from .document_ai import parse_medical_document


class ClinicalAnalysisTests(TestCase):
    def test_high_risk_with_interaction(self):
        result = analyze_clinical_data(
            age=64,
            blood_pressure="168/98",
            cholesterol=268,
            medications="aspirin, warfarin",
        )
        self.assertGreaterEqual(result["risk_score"], 60)
        self.assertEqual(result["level"], "High Risk")
        self.assertTrue(any("interaction" in item.lower() for item in result["alerts"]))

    def test_low_risk_profile(self):
        result = analyze_clinical_data(
            age=24,
            blood_pressure="118/76",
            cholesterol=168,
            medications="",
        )
        self.assertLess(result["risk_score"], 30)
        self.assertEqual(result["level"], "Low Risk")


class DocumentParserTests(TestCase):
    def test_parse_lab_and_medication_entities(self):
        text = """
        Tab Atorvastatin 10 mg once daily
        Cholesterol: 245
        LDL: 168
        HbA1c: 6.7
        """
        payload = parse_medical_document(text, "lab_report")
        self.assertIn("total_cholesterol", payload["lab_values"])
        self.assertIn("ldl", payload["lab_values"])
        self.assertIn("hba1c", payload["lab_values"])
        self.assertGreaterEqual(len(payload["medications"]), 1)
