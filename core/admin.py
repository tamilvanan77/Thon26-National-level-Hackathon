from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    User,
    DoctorProfile,
    PatientProfile,
    DoctorPatient,
    PatientDocument,
    AppointmentRequest,
)


class DoctorProfileInline(admin.StackedInline):
    model = DoctorProfile
    can_delete = False
    verbose_name_plural = 'Doctor Profile'
    fk_name = 'user'

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (DoctorProfileInline,)
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Clinical Access", {"fields": ("role",)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Clinical Access", {"fields": ("role",)}),
    )


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "degree", "specialization", "experience", "is_verified", "created_at")
    list_editable = ("is_verified",)
    search_fields = ("user__username", "degree", "specialization")
    list_filter = ("specialization", "is_verified")


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "age", "blood_pressure", "cholesterol", "risk_score", "created_at")
    search_fields = ("user__username", "diagnosis", "medications")
    list_filter = ("created_at",)
    readonly_fields = ("qr_code", "created_at")


@admin.register(DoctorPatient)
class DoctorPatientAdmin(admin.ModelAdmin):
    list_display = ("doctor", "patient")
    search_fields = ("doctor__user__username", "patient__user__username")


@admin.register(PatientDocument)
class PatientDocumentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doc_type", "title", "uploaded_by", "created_at")
    list_filter = ("doc_type", "created_at")
    search_fields = ("patient__user__username", "title")


@admin.register(AppointmentRequest)
class AppointmentRequestAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "preferred_date", "status", "created_at")
    list_filter = ("status", "preferred_date", "created_at")
    search_fields = ("patient__user__username", "doctor__user__username", "reason")
