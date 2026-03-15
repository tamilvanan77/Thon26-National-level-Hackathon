from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils.timezone import now
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import never_cache

from .forms import (
    PatientRegisterForm,
    DoctorRegisterForm,
    PatientProfileForm,
    PatientSelfUpdateForm,
    PatientContactUpdateForm,
    DoctorProfileForm,
    PatientDocumentForm,
    AppointmentRequestForm,
    AppointmentUpdateForm,
)
from .models import (
    DoctorProfile,
    PatientProfile,
    DoctorPatient,
    PatientDocument,
    AppointmentRequest,
    AIDiagnosis,
)
from .ai_engine import analyze_patient, analyze_clinical_data, analyze_visual_diagnosis
from .chatbot import medical_chatbot
from .document_ai import process_uploaded_document


@never_cache
def register_view(request):
    """
    Handles registration for patients only. Doctors are registered by Admin.
    """
    if request.method == "POST":
        form = PatientRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Registration successful. Please login.")
            return redirect("login")
        messages.error(request, "Please correct the errors below.")
    else:
        form = PatientRegisterForm()

    return render(request, "register.html", {"form": form, "role": "patient"})


@never_cache
@ensure_csrf_cookie
def login_view(request):
    if request.method == "POST":
        role = request.POST.get("role", "").strip().lower()
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Backfill legacy accounts where role is blank/invalid.
            if user.role not in {"doctor", "patient"}:
                if DoctorProfile.objects.filter(user=user).exists():
                    user.role = "doctor"
                    user.save(update_fields=["role"])
                elif PatientProfile.objects.filter(user=user).exists():
                    user.role = "patient"
                    user.save(update_fields=["role"])

            if role not in {"doctor", "patient"}:
                messages.error(request, "Please choose Doctor or Patient.")
                return render(request, "login.html")

            if user.role != role:
                shown_role = user.role.title() if user.role in {"doctor", "patient"} else "Unknown"
                messages.error(request, f"This account is registered as {shown_role}.")
                return render(request, "login.html")

            login(request, user)
            if user.role == "doctor":
                return redirect("doctor_profile")
            return redirect("dashboard")

        messages.error(request, "Invalid username or password.")

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard(request):
    if request.user.role == "doctor":
        return redirect("doctor_profile")

    try:
        patient = PatientProfile.objects.get(user=request.user)
    except PatientProfile.DoesNotExist:
        # If superuser (admin) logs in, redirect to admin panel
        if request.user.is_superuser:
            return redirect('/admin/')
        
        # Regular user without profile -> Force logout and redirect to register
        messages.warning(request, "Patient profile not found. Please register again.")
        logout(request)
        return redirect("register")

    analysis = analyze_patient(patient)

    patient.risk_score = analysis["risk_score"]
    patient.save(update_fields=["risk_score"])

    return render(request, "dashboard.html", {
        "analysis": analysis,
        "patient": patient
    })


@login_required
def patient_profile(request, id):
    if request.user.role == "patient":
        own_profile = get_object_or_404(PatientProfile, user=request.user)
        if own_profile.id != id:
            messages.error(request, "You can only access your own profile.")
            return redirect("my_profile")
        messages.info(request, "Use My Profile page to view your reports and appointment status.")
        return redirect("my_profile")

    if request.user.role != "doctor":
        messages.error(request, "Only doctors can access patient charts.")
        return redirect("dashboard")

    doctor_profile = get_object_or_404(DoctorProfile, user=request.user)
    
    if not doctor_profile.is_verified:
        messages.warning(request, "Access to patient charts is restricted until your account is verified.")
        return redirect("doctor_profile")

    patient = get_object_or_404(PatientProfile, id=id)

    if not DoctorPatient.objects.filter(doctor=doctor_profile, patient=patient).exists():
        messages.error(request, "This patient is not assigned to your care list.")
        return redirect("dashboard")

    analysis = analyze_patient(patient)
    patient.risk_score = analysis["risk_score"]
    patient.save(update_fields=["risk_score"])

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_profile":
            form = PatientProfileForm(request.POST, instance=patient)
            document_form = PatientDocumentForm()
            if form.is_valid():
                form.save()
                messages.success(request, "Patient details updated.")
                return redirect("patient_profile", id=id)
            messages.error(request, "Please correct patient record form errors.")
        elif action == "upload_document":
            form = PatientProfileForm(instance=patient)
            document_form = PatientDocumentForm(request.POST, request.FILES)
            if document_form.is_valid():
                document = document_form.save(commit=False)
                document.patient = patient
                document.uploaded_by = request.user
                document.save()
                try:
                    processed = process_uploaded_document(document)
                    document.extracted_text = processed["extracted_text"]
                    document.parsed_data = processed["parsed_data"]
                    document.verification_status = processed["verification_status"]
                    document.save(update_fields=["extracted_text", "parsed_data", "verification_status"])
                except Exception:
                    document.verification_status = "error"
                    document.save(update_fields=["verification_status"])
                messages.success(request, "Document uploaded.")
                return redirect("patient_profile", id=id)
            messages.error(request, "Please correct document upload form errors.")
        else:
            form = PatientProfileForm(instance=patient)
            document_form = PatientDocumentForm()
    else:
        form = PatientProfileForm(instance=patient)
        document_form = PatientDocumentForm()

    documents = patient.documents.all().order_by("-created_at")
    appointments = patient.appointments.select_related("doctor__user").order_by("-created_at")

    return render(request, "patient_profile.html", {
        "patient": patient,
        "analysis": analysis,
        "form": form,
        "document_form": document_form,
        "documents": documents,
        "appointments": appointments,
    })


@login_required
def my_profile(request):
    if request.user.role != "patient":
        messages.error(request, "Only patients can access this page.")
        return redirect("dashboard")

    try:
        patient = PatientProfile.objects.get(user=request.user)
    except PatientProfile.DoesNotExist:
        messages.warning(request, "Patient profile not found. Please register again.")
        logout(request)
        return redirect("register")

    doctors = DoctorProfile.objects.select_related("user").all().order_by("user__username")
    appointment_form = AppointmentRequestForm()
    appointment_form.fields["doctor"].queryset = doctors
    
    contact_form = PatientContactUpdateForm(instance=patient)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_contact":
            contact_form = PatientContactUpdateForm(request.POST, instance=patient)
            if contact_form.is_valid():
                contact_form.save()
                messages.success(request, "Contact information updated.")
                return redirect("my_profile")
            messages.error(request, "Please correct contact form errors.")

        elif action in {"update_profile", "upload_document"}:
            messages.error(request, "Patients have view-only access for medical records. Only doctors can update clinical data.")

        elif action == "request_appointment":
            appointment_form = AppointmentRequestForm(request.POST)
            appointment_form.fields["doctor"].queryset = doctors
            if appointment_form.is_valid():
                appointment = appointment_form.save(commit=False)
                appointment.patient = patient
                appointment.save()
                messages.success(request, "Appointment request sent.")
                return redirect("my_profile")
            messages.error(request, "Please correct appointment form errors.")

        else:
            messages.error(request, "Unknown form submission.")

    analysis = analyze_patient(patient)
    patient.risk_score = analysis["risk_score"]
    patient.save(update_fields=["risk_score"])

    documents = patient.documents.select_related("uploaded_by").order_by("-created_at")
    appointments = patient.appointments.select_related("doctor__user").order_by("-created_at")

    return render(request, "my_profile.html", {
        "patient": patient,
        "analysis": analysis,
        "documents": documents,
        "appointments": appointments,
        "appointment_form": appointment_form,
        "contact_form": contact_form,
    })


@login_required
def doctor_profile(request):
    if request.user.role != "doctor":
        messages.error(request, "Only doctors can access this page.")
        return redirect("dashboard")

    profile = get_object_or_404(DoctorProfile, user=request.user)

    if request.method == "POST":
        form = DoctorProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Doctor profile updated.")
            return redirect("doctor_profile")
    else:
        form = DoctorProfileForm(instance=profile)

    patients = (
        PatientProfile.objects.select_related("user")
        .filter(doctorpatient__doctor=profile)
        .order_by("user__username")
    )
    appointments = (
        AppointmentRequest.objects.filter(doctor=profile)
        .select_related("patient__user")
        .order_by("-created_at")
    )

    today = now().date()
    stats = {
        "total_patients": patients.count(),
        "today_appointments": appointments.filter(preferred_date=today).count(),
        "pending_requests": appointments.filter(status="pending").count(),
    }

    return render(
        request,
        "doctor_profile.html",
        {
            "form": form,
            "profile": profile,
            "patients": patients,
            "appointments": appointments,
            "stats": stats,
            "today": today,
        },
    )


@login_required
def appointment_update(request, id):
    if request.user.role != "doctor":
        messages.error(request, "Only doctors can update appointment requests.")
        return redirect("dashboard")

    doctor_profile = get_object_or_404(DoctorProfile, user=request.user)
    appointment = get_object_or_404(AppointmentRequest, id=id, doctor=doctor_profile)

    if request.method != "POST":
        return redirect("dashboard")

    form = AppointmentUpdateForm(request.POST, instance=appointment)
    if form.is_valid():
        updated = form.save()

        if updated.status == "approved":
            DoctorPatient.objects.get_or_create(doctor=doctor_profile, patient=updated.patient)

        messages.success(request, "Appointment updated.")
    else:
        messages.error(request, "Unable to update appointment.")

    return redirect("dashboard")


@login_required
def report_view(request, id):
    patient = get_object_or_404(PatientProfile, id=id)

    if request.user.role == "patient" and patient.user != request.user:
        return redirect("dashboard")

    if request.user.role == "doctor":
        doctor_profile = get_object_or_404(DoctorProfile, user=request.user)
        
        if not doctor_profile.is_verified:
            messages.warning(request, "Access to clinical reports is restricted until your account is verified.")
            return redirect("doctor_profile")

        if not DoctorPatient.objects.filter(doctor=doctor_profile, patient=patient).exists():
            messages.error(request, "You cannot view reports for unassigned patients.")
            return redirect("dashboard")

    analysis = analyze_patient(patient)
    documents = patient.documents.select_related("uploaded_by").order_by("-created_at")

    return render(request, "report.html", {
        "patient": patient,
        "analysis": analysis,
        "documents": documents,
        "today": now().date()
    })


@login_required
def chatbot_page(request):
    return render(request, "chatbot.html")


@login_required
def chatbot_api(request):
    message = request.GET.get("message", "")
    patient = None

    if hasattr(request.user, "role") and request.user.role == "patient":
        try:
            patient = PatientProfile.objects.get(user=request.user)
        except PatientProfile.DoesNotExist:
            patient = None

    reply = medical_chatbot(message, patient)
    return JsonResponse({"reply": reply})


@login_required
def risk_preview_api(request):
    age = request.GET.get("age")
    blood_pressure = request.GET.get("blood_pressure")
    cholesterol = request.GET.get("cholesterol")
    diagnosis = request.GET.get("diagnosis", "")
    medications = request.GET.get("medications", "")
    prescription_text = request.GET.get("prescription_text", "")

    analysis = analyze_clinical_data(
        age=age,
        blood_pressure=blood_pressure,
        cholesterol=cholesterol,
        diagnosis=diagnosis,
        medications=medications,
        prescription_text=prescription_text,
    )

    return JsonResponse(
        {
            "risk_score": analysis["risk_score"],
            "level": analysis["level"],
            "alerts": analysis["alerts"],
        }
    )


@login_required
def drug_check_view(request):
    result = None
    level = None

    if request.method == "POST":
        doctor_profile = get_object_or_404(DoctorProfile, user=request.user)
        if not doctor_profile.is_verified:
            messages.error(request, "This clinical tool is only available for verified doctors.")
            return redirect("doctor_profile")

        drug1 = request.POST.get("drug1", "").lower()
        drug2 = request.POST.get("drug2", "").lower()

        if ("aspirin" in drug1 and "warfarin" in drug2) or \
           ("warfarin" in drug1 and "aspirin" in drug2):
            result = "Aspirin and Warfarin together may increase bleeding risk."
            level = "High"

        elif ("atorvastatin" in drug1 and "clarithromycin" in drug2) or \
             ("clarithromycin" in drug1 and "atorvastatin" in drug2):
            result = "This combination may increase muscle damage risk."
            level = "Moderate"
        else:
            result = "No major interaction found."
            level = "Low"

    return render(request, "drug_check.html", {
        "result": result,
        "level": level
    })


@login_required
def ocr_upload_view(request):
    messages.info(
        request,
        "Direct upload from patient portal is disabled. Doctors upload prescriptions/lab reports from patient chart.",
    )
    return redirect("my_profile")


def custom_404(request, exception):
    return render(request, "404.html", status=404)
@login_required
def verify_prediction(request, id):
    """
    Handles doctor feedback for AI predictions.
    """
    if request.user.role != 'doctor':
        return JsonResponse({"status": "error", "message": "Only doctors can verify predictions."}, status=403)

    doctor_profile = get_object_or_404(DoctorProfile, user=request.user)
    if not doctor_profile.is_verified:
        return JsonResponse({"status": "error", "message": "Your account is not verified."}, status=403)

    patient = get_object_or_404(PatientProfile, id=id)
    if not DoctorPatient.objects.filter(doctor=doctor_profile, patient=patient).exists():
        return JsonResponse({"status": "error", "message": "Patient not assigned to you."}, status=403)

    if request.method == "POST":
        import json
        data = json.loads(request.body)
        
        patient.ai_prediction_verified = data.get("verified", False)
        patient.ai_prediction_notes = data.get("notes", "")
        patient.save(update_fields=["ai_prediction_verified", "ai_prediction_notes"])
        
        return JsonResponse({
            "status": "success", 
            "message": "Clinical feedback saved successfully.",
            "is_verified": patient.ai_prediction_verified
        })

    return JsonResponse({"status": "error", "message": "Invalid request."}, status=400)
@login_required
def visual_diagnosis(request):
    """
    View for uploading clinical images for AI analysis.
    """
    if request.method == "POST" and request.FILES.get("image"):
        image = request.FILES["image"]
        patient = PatientProfile.objects.filter(user=request.user).first()
        diagnosis = AIDiagnosis.objects.create(
            user=request.user, 
            patient=patient, 
            image=image
        )
        
        # Run AI analysis
        result = analyze_visual_diagnosis(diagnosis.image.path)
        
        diagnosis.extracted_text = result.get("extracted_text")
        diagnosis.disease_prediction = result.get("disease")
        diagnosis.solution = result.get("solution")
        diagnosis.recommended_specialization = result.get("specialization")
        diagnosis.save()
        
        return redirect("visual_diagnosis_result", pk=diagnosis.pk)
        
    return render(request, "visual_diagnosis.html")


@login_required
def visual_diagnosis_result(request, pk):
    """
    Display the AI analysis results and recommended doctors.
    """
    diagnosis = get_object_or_404(AIDiagnosis, pk=pk, user=request.user)
    
    # Simple recommendation logic based on specialization keywords
    spec = diagnosis.recommended_specialization
    doctors = DoctorProfile.objects.filter(is_verified=True)
    
    # Try to find doctors matching the specialization
    recommended_doctors = []
    if spec:
        # Search for surgeons, cardiologists, etc. in specialization field
        recommended_doctors = doctors.filter(specialization__icontains=spec)
    
    # Fallback to general physicians if no specialized matches found
    if not recommended_doctors.exists():
        recommended_doctors = doctors.filter(specialization__icontains="general")[:3]
    else:
        recommended_doctors = recommended_doctors[:3]

    return render(request, "visual_diagnosis_result.html", {
        "diagnosis": diagnosis,
        "recommended_doctors": recommended_doctors
    })
