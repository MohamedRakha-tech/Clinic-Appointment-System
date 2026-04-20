from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


# ─────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────

class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    username    = models.CharField(max_length=150, unique=True)
    email       = models.EmailField(max_length=255, unique=True)
    first_name  = models.CharField(max_length=150, blank=True, null=True)
    last_name   = models.CharField(max_length=150, blank=True, null=True)
    phone       = models.CharField(max_length=20, blank=True, null=True)
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD  = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.username


# ─────────────────────────────────────────────
# PROFILE TABLES
# ─────────────────────────────────────────────

class PatientProfile(models.Model):
    user                    = models.OneToOneField(User, on_delete=models.CASCADE, related_name="patient_profile")
    date_of_birth           = models.DateField(blank=True, null=True)
    gender                  = models.CharField(max_length=10, blank=True, null=True)
    address                 = models.TextField(blank=True, null=True)
    emergency_contact_name  = models.CharField(max_length=120, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    created_at              = models.DateTimeField(auto_now_add=True)
    updated_at              = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patient_profiles"

    def __str__(self):
        return f"Patient: {self.user.username}"


class DoctorProfile(models.Model):
    user                          = models.OneToOneField(User, on_delete=models.CASCADE, related_name="doctor_profile")
    specialization                = models.CharField(max_length=120)
    license_number                = models.CharField(max_length=120, unique=True)
    consultation_duration_minutes = models.IntegerField(default=15)
    buffer_before_minutes         = models.IntegerField(default=5)
    buffer_after_minutes          = models.IntegerField(default=5)
    bio                           = models.TextField(blank=True, null=True)
    created_at                    = models.DateTimeField(auto_now_add=True)
    updated_at                    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "doctor_profiles"

    def __str__(self):
        return f"Dr. {self.user.username} ({self.specialization})"


class ReceptionistProfile(models.Model):
    user          = models.OneToOneField(User, on_delete=models.CASCADE, related_name="receptionist_profile")
    employee_code = models.CharField(max_length=50, unique=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "receptionist_profiles"

    def __str__(self):
        return f"Receptionist: {self.user.username}"


class AdminProfile(models.Model):
    user          = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_profile")
    employee_code = models.CharField(max_length=50, unique=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "admin_profiles"

    def __str__(self):
        return f"Admin: {self.user.username}"