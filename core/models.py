from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.files.base import ContentFile

from io import BytesIO
import qrcode


# ======================================
# 🔥 CUSTOM USER MODEL
# ======================================

class User(AbstractUser):

    ROLE_CHOICES = (
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='patient'
    )

    def __str__(self):
        return f"{self.username} ({self.role})"


# ======================================
# 🔥 DOCTOR PROFILE
# ======================================

class DoctorProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    # 1️⃣ Personal Information
    full_name = models.CharField(max_length=200, default="")
    gender = models.CharField(
        max_length=10,
        choices=(('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')),
        default='Male'
    )
    date_of_birth = models.DateField(null=True, blank=True)
    age = models.IntegerField(default=30)

    # 2️⃣ Professional Information
    license_number = models.CharField(max_length=50, blank=True, null=True)
    degree = models.CharField(max_length=100)  # e.g. "MBBS, MD"
    specialization = models.CharField(max_length=100)
    experience = models.IntegerField()  # years
    hospital_name = models.CharField(max_length=200, blank=True, null=True)

    # 3️⃣ Contact Information
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dr. {self.user.username}"


# ======================================
# 🔥 PATIENT PROFILE
# ======================================

class PatientProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    full_name = models.CharField(max_length=200, default="")
    gender = models.CharField(
        max_length=10,
        choices=(('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')),
        default='Male'
    )
    date_of_birth = models.DateField(null=True, blank=True)
    blood_group = models.CharField(
        max_length=5,
        choices=(
            ('A+', 'A+'), ('A-', 'A-'),
            ('B+', 'B+'), ('B-', 'B-'),
            ('AB+', 'AB+'), ('AB-', 'AB-'),
            ('O+', 'O+'), ('O-', 'O-')
        ),
        default='O+'
    )

    age = models.IntegerField()
    blood_pressure = models.CharField(max_length=20, default="120/80")
    cholesterol = models.FloatField(default=0.0)

    # 🔥 Contact Information
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)

    diagnosis = models.TextField(blank=True, null=True, default="")
    medications = models.TextField(blank=True, null=True, default="")

    # 🔥 AI Fields
    risk_score = models.FloatField(blank=True, null=True)
    ai_prediction_verified = models.BooleanField(default=False)
    ai_prediction_notes = models.TextField(blank=True, null=True)

    # 🔥 OCR Fields
    prescription_image = models.ImageField(
        upload_to='prescriptions/',
        null=True,
        blank=True
    )

    prescription_text = models.TextField(
        null=True,
        blank=True
    )

    # 🔥 QR Code
    qr_code = models.ImageField(
        upload_to='qr_codes/',
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def _build_qr_payload(self):
        return (
            f"Care&Cure Patient\n"
            f"ID: {self.pk}\n"
            f"Username: {self.user.username}\n"
            f"Age: {self.age}\n"
            f"Blood Pressure: {self.blood_pressure}\n"
            f"Cholesterol: {self.cholesterol}\n"
            f"Risk Score: {self.risk_score if self.risk_score is not None else '-'}"
        )

    def _generate_qr_code_file(self):
        qr_image = qrcode.make(self._build_qr_payload())
        buffer = BytesIO()
        qr_image.save(buffer, format="PNG")
        return ContentFile(buffer.getvalue(), name=f"patient_{self.pk}_qr.png")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.pk:
            return

        old_name = self.qr_code.name if self.qr_code else None
        self.qr_code.save(f"patient_{self.pk}_qr.png", self._generate_qr_code_file(), save=False)

        if old_name and old_name != self.qr_code.name:
            self.qr_code.storage.delete(old_name)

        super().save(update_fields=["qr_code"])

    def __str__(self):
        return f"{self.user.username} - Patient"


# ======================================
# 🔥 DOCTOR-PATIENT RELATIONSHIP
# ======================================

class DoctorPatient(models.Model):
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("doctor", "patient")

    def __str__(self):
        return f"{self.doctor.user.username} -> {self.patient.user.username}"


class PatientDocument(models.Model):
    DOC_TYPE_CHOICES = (
        ("prescription", "Prescription"),
        ("lab_report", "Lab Report"),
    )

    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="documents")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="patient_documents/")
    notes = models.TextField(blank=True, null=True)
    extracted_text = models.TextField(blank=True, null=True)
    parsed_data = models.JSONField(blank=True, null=True)
    verification_status = models.CharField(
        max_length=20,
        choices=(
            ("pending", "Pending"),
            ("parsed", "Parsed"),
            ("error", "Error"),
        ),
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.user.username} - {self.title}"


class AppointmentRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="appointments")
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="appointments")
    reason = models.TextField()
    preferred_date = models.DateField(blank=True, null=True)
    preferred_time = models.TimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    response_note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.user.username} -> Dr. {self.doctor.user.username} ({self.status})"


class AIDiagnosis(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="ai_diagnoses", null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="visual_diagnoses", null=True, blank=True)
    image = models.ImageField(upload_to="ai_diagnoses/")
    extracted_text = models.TextField(blank=True, null=True)
    disease_prediction = models.CharField(max_length=200, blank=True, null=True)
    solution = models.TextField(blank=True, null=True)
    recommended_specialization = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user_display = self.user.username if self.user else "Anonymous"
        return f"AI Diagnosis for {user_display} - {self.disease_prediction or 'Processing'}"
