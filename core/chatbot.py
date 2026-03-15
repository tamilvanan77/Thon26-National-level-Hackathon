from .ai_engine import analyze_patient
from .medical_ai_client import ask_openai_medical_assistant


def medical_chatbot(message, patient=None):

    message = message.lower()

    # -------- Emergency Detection --------
    emergency_keywords = ["chest pain", "heart attack", "severe pain", "breathing problem"]
    for word in emergency_keywords:
        if word in message:
            return ("This may be a medical emergency. "
                    "Please seek immediate medical attention or visit the nearest hospital.")

    # -------- External AI Provider (optional) --------
    patient_context = "No patient profile provided."
    if patient:
        live = analyze_patient(patient, include_external=False)
        patient_context = (
            f"Age: {patient.age}, BP: {patient.blood_pressure}, Cholesterol: {patient.cholesterol}, "
            f"Diagnosis: {patient.diagnosis or 'N/A'}, Medications: {patient.medications or 'N/A'}, "
            f"Current computed risk score: {live['risk_score']}% ({live['level']})."
        )
    ai_reply = ask_openai_medical_assistant(message, patient_context)
    if ai_reply:
        return ai_reply

    # -------- Personalized Risk Info --------
    if "my risk" in message and patient:
        live = analyze_patient(patient, include_external=False)
        return (f"Your current calculated heart risk is approximately "
                f"{live['risk_score']}% ({live['level']}). "
                "Please follow your prescribed treatment plan.")

    # -------- Cholesterol --------
    if "cholesterol" in message:
        if patient and patient.cholesterol:
            return (f"Your cholesterol level is {patient.cholesterol}. "
                    "Ideal total cholesterol should be below 200 mg/dL. "
                    "Consider reducing fried food and exercising regularly.")
        return ("High cholesterol increases heart disease risk. "
                "Healthy diet and exercise help reduce it.")

    # -------- Blood Pressure --------
    if "blood pressure" in message or "bp" in message:
        if patient and patient.blood_pressure:
            return (f"Your BP reading is {patient.blood_pressure}. "
                    "Normal BP is around 120/80 mmHg. "
                    "Reduce salt intake and manage stress.")
        return "Normal blood pressure is around 120/80 mmHg."

    # -------- Diet Advice --------
    if "diet" in message or "food" in message:
        return ("A heart-healthy diet includes fruits, vegetables, "
                "whole grains, lean protein, and low-fat dairy. "
                "Avoid excess sugar, salt, and oily food.")

    # -------- Exercise --------
    if "exercise" in message:
        return ("Regular physical activity such as 30 minutes of walking daily "
                "can significantly reduce cardiovascular risk.")

    # -------- Symptoms Gathering --------
    if "symptom" in message or "feeling" in message:
        return ("Please describe your symptoms clearly. "
                "For example: chest pain, dizziness, headache, fatigue.")

    # -------- Medication Inquiry --------
    if "medicine" in message or "drug" in message:
        return ("Please consult your doctor before changing any medication. "
                "If you uploaded a prescription, the system checks for interactions.")

    # -------- Age Factor --------
    if "age" in message:
        if patient and patient.age:
            return (f"You are {patient.age} years old. "
                    "Heart risk generally increases after age 50. "
                    "Regular screening is recommended.")
        return "Age is an important factor in heart disease risk."

    # -------- Greeting --------
    if "hello" in message or "hi" in message:
        return "Hello! I am your AI Health Assistant. How can I help you today?"

    # -------- Default --------
    return ("I am here to assist with heart health, blood pressure, cholesterol, "
            "diet, exercise, and medication queries. "
            "For detailed diagnosis, please consult your doctor.")
