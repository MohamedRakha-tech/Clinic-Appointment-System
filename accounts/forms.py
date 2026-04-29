from django import forms
from django.contrib.auth.forms import AuthenticationForm

from accounts.models import User


class LoginForm(AuthenticationForm):
    """Login form using Django AuthenticationForm (session auth)."""

    username = forms.CharField(label="Username or Email", max_length=150)


class PatientRegisterForm(forms.ModelForm):
    """Public registration form (patient only)."""

    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    # PatientProfile fields collected on the signup page
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    gender = forms.CharField(required=False, max_length=20)
    address = forms.CharField(required=False, widget=forms.TextInput)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "phone"]

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
        """Write the profile-specific fields to the PatientProfile row."""
        from accounts.models import PatientProfile

        profile, _ = PatientProfile.objects.get_or_create(user=user)
        profile.date_of_birth = self.cleaned_data.get("date_of_birth")
        profile.gender = self.cleaned_data.get("gender") or ""
        profile.address = self.cleaned_data.get("address") or ""
        profile.save()
