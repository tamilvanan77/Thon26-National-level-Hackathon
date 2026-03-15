from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import (
    User,
    DoctorProfile,
    PatientProfile,
    PatientDocument,
    AppointmentRequest,
)


class PatientRegisterForm(UserCreationForm):
    full_name = forms.CharField(max_length=200, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter full name"}))
    gender = forms.ChoiceField(
        choices=(('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"})
    )
    blood_group = forms.ChoiceField(
        choices=(
            ('A+', 'A+'), ('A-', 'A-'),
            ('B+', 'B+'), ('B-', 'B-'),
            ('AB+', 'AB+'), ('AB-', 'AB-'),
            ('O+', 'O+'), ('O-', 'O-')
        ),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": "form-control"}))
    age = forms.IntegerField(widget=forms.NumberInput(attrs={"class": "form-control"}))
    blood_pressure = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 120/80"})
    )
    cholesterol = forms.FloatField(widget=forms.NumberInput(attrs={"class": "form-control"}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ("email", "full_name", "gender", "date_of_birth", "blood_group", "age", "blood_pressure", "cholesterol")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "patient"
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()
            PatientProfile.objects.create(
                user=user,
                full_name=self.cleaned_data["full_name"],
                gender=self.cleaned_data["gender"],
                date_of_birth=self.cleaned_data["date_of_birth"],
                blood_group=self.cleaned_data["blood_group"],
                age=self.cleaned_data["age"],
                blood_pressure=self.cleaned_data["blood_pressure"],
                cholesterol=self.cleaned_data["cholesterol"],
                diagnosis="",
                medications="",
            )
        return user


class DoctorRegisterForm(UserCreationForm):
    # The email field for the User model (username is handled by UserCreationForm)
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": "form-control"}))

    # 1️⃣ Personal Information
    full_name = forms.CharField(max_length=200, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter full name"}))
    gender = forms.ChoiceField(
        choices=(('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"})
    )
    age = forms.IntegerField(widget=forms.NumberInput(attrs={"class": "form-control"}))

    # 2️⃣ Professional Information
    license_number = forms.CharField(max_length=50, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Medical License Number"}))
    specialization = forms.ChoiceField(
        choices=(
            ('Cardiologist', 'Cardiologist'),
            ('Neurologist', 'Neurologist'),
            ('Orthopedic', 'Orthopedic'),
            ('Dermatologist', 'Dermatologist'),
            ('General Physician', 'General Physician'),
        ),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    degree = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. MBBS, MD"}))
    experience = forms.IntegerField(widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Years of Experience"}))
    hospital_name = forms.CharField(max_length=200, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Hospital / Clinic Name"}))

    # 3️⃣ Contact Information
    phone_number = forms.CharField(max_length=15, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Phone Number"}))
    address = forms.CharField(widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Address"}))
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "City"}))
    state = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "State"}))
    pincode = forms.CharField(max_length=10, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Pincode"}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + (
            "email", "full_name", "gender", "date_of_birth", "age",
            "license_number", "specialization", "degree", "experience", "hospital_name",
            "phone_number", "address", "city", "state", "pincode"
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "doctor"
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()
            DoctorProfile.objects.create(
                user=user,
                full_name=self.cleaned_data["full_name"],
                gender=self.cleaned_data["gender"],
                date_of_birth=self.cleaned_data["date_of_birth"],
                age=self.cleaned_data["age"],
                license_number=self.cleaned_data["license_number"],
                specialization=self.cleaned_data["specialization"],
                degree=self.cleaned_data["degree"],
                experience=self.cleaned_data["experience"],
                hospital_name=self.cleaned_data["hospital_name"],
                phone_number=self.cleaned_data["phone_number"],
                address=self.cleaned_data["address"],
                city=self.cleaned_data["city"],
                state=self.cleaned_data["state"],
                pincode=self.cleaned_data["pincode"],
            )
        return user


class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        fields = ["age", "blood_pressure", "cholesterol", "diagnosis", "medications"]
        widgets = {
            "age": forms.NumberInput(attrs={"class": "form-control"}),
            "blood_pressure": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 120/80"}),
            "cholesterol": forms.NumberInput(attrs={"class": "form-control"}),
            "diagnosis": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "medications": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class PatientSelfUpdateForm(forms.ModelForm):
    # This form is for patients to update their OWN medical details if allowed
    class Meta:
        model = PatientProfile
        fields = ["age", "blood_pressure", "cholesterol", "diagnosis", "medications"]
        widgets = {
            "age": forms.NumberInput(attrs={"class": "form-control"}),
            "blood_pressure": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 120/80"}),
            "cholesterol": forms.NumberInput(attrs={"class": "form-control"}),
            "diagnosis": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "medications": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class PatientContactUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": "form-control"}))

    class Meta:
        model = PatientProfile
        fields = ["phone_number", "address", "city", "state", "pincode"]
        widgets = {
            "phone_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "Phone Number"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Address"}),
            "city": forms.TextInput(attrs={"class": "form-control", "placeholder": "City"}),
            "state": forms.TextInput(attrs={"class": "form-control", "placeholder": "State"}),
            "pincode": forms.TextInput(attrs={"class": "form-control", "placeholder": "Pincode"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields["email"].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
            user = profile.user
            user.email = self.cleaned_data["email"]
            user.save(update_fields=["email"])
        return profile


class DoctorProfileForm(forms.ModelForm):
    class Meta:
        model = DoctorProfile
        fields = ["degree", "specialization", "experience"]
        widgets = {
            "degree": forms.TextInput(attrs={"class": "form-control"}),
            "specialization": forms.TextInput(attrs={"class": "form-control"}),
            "experience": forms.NumberInput(attrs={"class": "form-control"}),
        }


class PatientDocumentForm(forms.ModelForm):
    class Meta:
        model = PatientDocument
        fields = ["doc_type", "title", "file", "notes"]
        widgets = {
            "doc_type": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "file": forms.FileInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class AppointmentRequestForm(forms.ModelForm):
    class Meta:
        model = AppointmentRequest
        fields = ["doctor", "reason", "preferred_date", "preferred_time"]
        widgets = {
            "doctor": forms.Select(attrs={"class": "form-select"}),
            "reason": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "preferred_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "preferred_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
        }


class AppointmentUpdateForm(forms.ModelForm):
    class Meta:
        model = AppointmentRequest
        fields = ["status", "response_note"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "response_note": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }
