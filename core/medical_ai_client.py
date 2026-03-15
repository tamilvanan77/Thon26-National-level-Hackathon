import json
import os
from urllib import error, request


def ask_openai_medical_assistant(message, patient_context=""):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return None

    model = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct")
    
    # --- Persona "Training" (Refined Clinical System Prompt) ---
    system_prompt = (
        "You are the 'Cure & Care' AI Clinical Assistant, a state-of-the-art decision support system. "
        "Your expertise covers Cardiovascular Health, Hypertension Management, and Predictive Analytics. "
        "\n\nCORE OPERATING PROTOCOLS:"
        "\n1. INTERPRET XAI: You understand SHAP feature importance. If a risk score is high, look at the feature weights (age, cholesterol, etc.) to explain 'why'."
        "\n2. DEEP LEARNING AWARENESS: You recognize temporal trends. If the system detects rising BP or glucose, explain how these longitudinal shifts impact the RNN/LSTM predictive model."
        "\n3. CLINICAL GUIDELINES: Follow ACC/AHA guidelines for BP (Normal <120/80) and Cholesterol (Ideal <200mg/dL)."
        "\n4. SAFETY FIRST: Always state you are a tool for clinicians, not a replacement for a doctor. For emergencies (chest pain, stroke symptoms), scream URGENT CARE immediately."
        "\n5. PERSISTENT FEEDBACK: Acknowledge that clinicians can verify or correct your predictions to improve future accuracy."
        "\n\nSTRICT RULES: Be concise, professional, and evidence-based. Never provide a final diagnosis."
    )

    payload = {
        "model": model,
        "temperature": 0.3,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "system",
                "content": f"LIVE PATIENT CONTEXT: {patient_context or 'No live metrics available.'}"
            },
            {
                "role": "user",
                "content": message,
            },
        ],
    }

    req = request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": os.environ.get("HTTP_REFERER", "http://localhost:8000"),
            "X-Title": os.environ.get("X_TITLE", "CureAndCare_Clinical_Support"),
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except (error.URLError, error.HTTPError, KeyError, IndexError, json.JSONDecodeError, TimeoutError) as e:
        print(f"OpenRouter Error: {str(e)}")
        return None
