from django import forms
from django.contrib.auth.forms import AuthenticationForm

from accounts.models import User
from accounts.models import DoctorProfile, PatientProfile, validate_not_future_date, validate_logical_age


class LoginForm(AuthenticationForm):

    username = forms.CharField(label="Username or Email", max_length=150)


class PatientRegisterForm(forms.ModelForm):

    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    # PatientProfile fields collected on the signup page
    date_of_birth = forms.DateField(
        required=True, 
        validators=[validate_not_future_date, validate_logical_age],
        widget=forms.DateInput(attrs={"type": "date"})
    )
    gender = forms.ChoiceField(
        required=True,
        choices=[
            ("", "Select Option"),
            ("Female", "Female"),
            ("Male", "Male"),
        ],
    )
    address = forms.CharField(required=True, widget=forms.TextInput)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "phone", "profile_picture"]
        widgets = {
            "profile_picture": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            raise forms.ValidationError("Passwords do not match.")

        username = cleaned_data.get("username")
        email = cleaned_data.get("email")

        if username and User.objects.filter(username=username).exists():
            self.add_error("username", "This username is already taken.")

        if email and User.objects.filter(email=email).exists():
            self.add_error("email", "This email is already used.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

    def save_profile(self, user):

        profile, created = PatientProfile.objects.get_or_create(
            user=user,
            defaults={
                "date_of_birth": self.cleaned_data.get("date_of_birth"),
                "gender": self.cleaned_data["gender"],
                "address": self.cleaned_data["address"],
            },
        )
        if not created:
            profile.date_of_birth = self.cleaned_data.get("date_of_birth")
            profile.gender = self.cleaned_data["gender"]
            profile.address = self.cleaned_data["address"]
            profile.save()


class PatientProfileForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        required=True, 
        validators=[validate_not_future_date, validate_logical_age],
        widget=forms.DateInput(attrs={"type": "date"})
    )
    gender = forms.ChoiceField(required=True, choices=[
        ('Male', 'Male'), ('Female', 'Female')
    ])
    address = forms.CharField(required=True, widget=forms.Textarea)
    emergency_contact_name = forms.CharField(required=False, max_length=120)
    emergency_contact_phone = forms.CharField(required=False, max_length=20)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "phone", "profile_picture"]
        widgets = {
            "profile_picture": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self.instance, 'patient_profile'):
            profile = self.instance.patient_profile
            self.initial['date_of_birth'] = profile.date_of_birth
            self.initial['gender'] = profile.gender
            self.initial['address'] = profile.address
            self.initial['emergency_contact_name'] = profile.emergency_contact_name
            self.initial['emergency_contact_phone'] = profile.emergency_contact_phone

    def save(self, commit=True):
        user = super().save(commit=commit)
        from accounts.models import PatientProfile

        profile, _ = PatientProfile.objects.get_or_create(user=user)
        profile.date_of_birth = self.cleaned_data.get('date_of_birth')
        profile.gender = self.cleaned_data['gender']
        profile.address = self.cleaned_data['address']
        profile.emergency_contact_name = self.cleaned_data.get('emergency_contact_name')
        profile.emergency_contact_phone = self.cleaned_data.get('emergency_contact_phone')
        if commit:
            profile.save()
        return user


class DoctorProfileForm(forms.ModelForm):
    specialization = forms.CharField(required=True, max_length=120)
    license_number = forms.CharField(required=True, max_length=120)
    consultation_fee = forms.DecimalField(max_digits=8, decimal_places=2, min_value=0, required=True)
    consultation_duration_minutes = forms.IntegerField(min_value=5, max_value=240, required=True)
    buffer_before_minutes = forms.IntegerField(min_value=0, max_value=60, required=True)
    buffer_after_minutes = forms.IntegerField(min_value=0, max_value=60, required=True)
    bio = forms.CharField(required=False, widget=forms.Textarea)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "phone", "profile_picture"]
        widgets = {
            "profile_picture": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self.instance, 'doctor_profile'):
            profile = self.instance.doctor_profile
            self.initial['specialization'] = profile.specialization
            self.initial['license_number'] = profile.license_number
            self.initial['consultation_fee'] = profile.consultation_fee
            self.initial['consultation_duration_minutes'] = profile.consultation_duration_minutes
            self.initial['buffer_before_minutes'] = profile.buffer_before_minutes
            self.initial['buffer_after_minutes'] = profile.buffer_after_minutes
            self.initial['bio'] = profile.bio

    def clean_license_number(self):
        license_number = self.cleaned_data.get('license_number')
        if not license_number:
            return license_number

        existing_profiles = DoctorProfile.objects.filter(license_number=license_number)
        if hasattr(self.instance, 'doctor_profile'):
            existing_profiles = existing_profiles.exclude(pk=self.instance.doctor_profile.pk)

        if existing_profiles.exists():
            raise forms.ValidationError("This license number is already used.")
        return license_number

    def save(self, commit=True):
        user = super().save(commit=commit)
        if hasattr(user, 'doctor_profile'):
            profile = user.doctor_profile
            profile.specialization = self.cleaned_data.get('specialization')
            profile.license_number = self.cleaned_data.get('license_number')
            profile.consultation_fee = self.cleaned_data.get('consultation_fee')
            profile.consultation_duration_minutes = self.cleaned_data.get('consultation_duration_minutes')
            profile.buffer_before_minutes = self.cleaned_data.get('buffer_before_minutes')
            profile.buffer_after_minutes = self.cleaned_data.get('buffer_after_minutes')
            profile.bio = self.cleaned_data.get('bio')
            if commit:
                profile.save()
        return user


class ReceptionistProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "phone", "profile_picture"]
        widgets = {
            "profile_picture": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }


class AdminProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "phone", "profile_picture"]
        widgets = {
            "profile_picture": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }
